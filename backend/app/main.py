"""Usalp Backend — FastAPI uygulama giriş noktası."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import ai, alerts, auth, metrics, servers
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.database import engine, get_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN001
    """Startup: DB bağlantısını test et, Shutdown: pool'u kapat."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database bağlantısı başarılı")
    yield
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
    allow_origins=settings.CORS_ORIGINS,
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


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Docker healthcheck ve monitoring için."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
