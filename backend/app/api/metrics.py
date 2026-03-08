"""Metrik endpoint'leri."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import verify_agent_api_key
from app.schemas.metric import MetricIn

router = APIRouter(tags=["metrics"])


@router.post("/metrics", dependencies=[Depends(verify_agent_api_key)])
async def receive_metrics(payload: MetricIn) -> dict:
    """Agent'tan metrik alır ve veritabanına kaydeder."""
    # TODO(v1): Metrik kaydetme ve alert engine tetikleme
    return {"data": {"received": True}, "meta": {"timestamp": ""}}
