"""Usalp Backend — FastAPI uygulama giriş noktası."""

from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import ai, alerts, metrics, servers
from app.config import settings
from app.database import get_db

app = FastAPI(
    title="Usalp API",
    description="AI destekli sunucu izleme ve log analiz platformu",
    version="0.1.0",
    docs_url="/api/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/api/redoc" if settings.ENVIRONMENT == "development" else None,
)

app.include_router(metrics.router, prefix="/api/v1")
app.include_router(servers.router, prefix="/api/v1")
app.include_router(alerts.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict:
    """Docker healthcheck ve monitoring için."""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable")
