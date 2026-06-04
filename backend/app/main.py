"""Usalp Backend — FastAPI uygulama giriş noktası."""

from __future__ import annotations

import asyncio
import io
import logging
import os
import tarfile
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import ai, alerts, auth, metrics, servers
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.database import async_session, engine, get_db
from app.services import retention, server_status
from app.services.demo_seed import seed_demo_data

logger = logging.getLogger(__name__)
AGENT_SOURCE_DIR = Path(os.getenv("AGENT_SOURCE_DIR", "/agent"))
AGENT_RUNTIME_FILES = {"install.sh", "pyproject.toml", "main.py", "config.py", "models.py"}
AGENT_RUNTIME_DIRS = {"collectors", "readers", "sender"}
AGENT_EXCLUDED_PARTS = {
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "tests",
}


async def _maintenance_loop() -> None:
    """Offline işaretleme ve retention temizliğini periyodik çalıştırır."""
    while True:
        try:
            async with async_session() as session:
                await server_status.mark_stale_servers_offline(session)
                await retention.cleanup_old_records(session)
                await session.commit()
        except Exception:
            logger.exception("maintenance_loop_failed")
        await asyncio.sleep(settings.RETENTION_SWEEP_INTERVAL_SECONDS)


async def _seed_demo_data_if_enabled() -> None:
    """Demo modu açıksa örnek veriyi startup sırasında hazırlar."""
    if not settings.DEMO_MODE:
        return

    async with async_session() as session:
        result = await seed_demo_data(session, reset=settings.DEMO_SEED_RESET)
        await session.commit()

    if result.skipped:
        logger.info("Demo seed atlandı: mevcut demo verisi korunuyor")
        return

    logger.info(
        "Demo seed tamamlandı: servers=%d metrics=%d logs=%d services=%d alerts=%d analyses=%d",
        result.servers,
        result.metrics,
        result.logs,
        result.services,
        result.alerts,
        result.analyses,
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup: DB bağlantısını test et, Shutdown: pool'u kapat."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database bağlantısı başarılı")
    await _seed_demo_data_if_enabled()
    maintenance_task = asyncio.create_task(_maintenance_loop())
    yield
    maintenance_task.cancel()
    with suppress(asyncio.CancelledError):
        await maintenance_task
    await engine.dispose()
    logger.info("Database connection pool kapatıldı")


app = FastAPI(
    title="Usalp API",
    description="AI destekli sunucu izleme ve log analiz platformu",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT == "development" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(metrics.router, prefix="/api/v1", tags=["metrics"])
app.include_router(servers.router, prefix="/api/v1", tags=["servers"])
app.include_router(alerts.router, prefix="/api/v1", tags=["alerts"])
app.include_router(ai.router, prefix="/api/v1", tags=["ai"])


@app.middleware("http")
async def enforce_request_limits_and_headers(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Basit payload limiti ve backend güvenlik header'ları."""
    if request.method in {"POST", "PUT", "PATCH"}:
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                request_size = int(content_length)
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})
            if request_size > settings.MAX_REQUEST_BODY_BYTES:
                return JSONResponse(status_code=413, content={"detail": "Request body too large"})

    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
    return response


def _iter_agent_runtime_files() -> list[Path]:
    """Installer tarball'ına yalnızca çalışma zamanı dosyalarını dahil eder."""
    files: list[Path] = []
    for path in AGENT_SOURCE_DIR.rglob("*"):
        if path.is_dir():
            continue
        rel = path.relative_to(AGENT_SOURCE_DIR)
        if any(part in AGENT_EXCLUDED_PARTS for part in rel.parts):
            continue
        if path.suffix in {".pyc", ".pyo"}:
            continue
        if len(rel.parts) == 1 and rel.name in AGENT_RUNTIME_FILES:
            files.append(path)
            continue
        if len(rel.parts) >= 2 and rel.parts[0] in AGENT_RUNTIME_DIRS and path.suffix == ".py":
            files.append(path)
    return sorted(files)


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Docker healthcheck ve monitoring için."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database unavailable") from exc


@app.get("/install.sh", include_in_schema=False)
async def agent_install_script() -> FileResponse:
    """Agent kurulum script'ini dashboard komutları için servis eder."""
    script_path = AGENT_SOURCE_DIR / "install.sh"
    if not script_path.exists():
        raise HTTPException(status_code=404, detail="Agent install script not found")
    return FileResponse(script_path, media_type="text/x-shellscript")


@app.get("/agent.tar.gz", include_in_schema=False)
async def agent_tarball() -> StreamingResponse:
    """Agent dosyalarını kurulum script'inin indireceği tarball olarak servis eder."""
    if not AGENT_SOURCE_DIR.exists():
        raise HTTPException(status_code=404, detail="Agent source directory not found")

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for path in _iter_agent_runtime_files():
            tar.add(path, arcname=Path("usalp-agent") / path.relative_to(AGENT_SOURCE_DIR))
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/gzip",
        headers={"Content-Disposition": "attachment; filename=agent.tar.gz"},
    )
