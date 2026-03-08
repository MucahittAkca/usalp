"""AI analiz endpoint'leri."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.ai_analysis import AIAnalyzeRequest

router = APIRouter(tags=["ai"])


@router.post("/ai/analyze")
async def trigger_analysis(request: AIAnalyzeRequest) -> dict:
    """Manuel AI analiz tetikler."""
    # TODO(v1): AI analyzer servisini çağır
    return {"data": {}, "meta": {"timestamp": ""}}


@router.get("/ai/analyses/{server_id}")
async def get_analyses(server_id: int) -> dict:
    """Sunucuya ait geçmiş AI analizlerini döndürür."""
    # TODO(v1): DB'den analiz geçmişi
    return {"data": [], "meta": {"total": 0, "page": 1, "per_page": 20}}
