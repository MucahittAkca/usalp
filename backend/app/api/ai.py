"""AI analiz endpoint'leri — manuel tetikleme ve geçmiş sorgulama."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.database import get_db
from app.models.ai_analysis import AIAnalysis
from app.models.server import Server
from app.schemas.ai_analysis import AIAnalysisOut, AIAnalyzeRequest
from app.services import ai_analyzer

router = APIRouter(tags=["ai"])


@router.post("/ai/analyze")
async def trigger_analysis(
    request: AIAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> dict:
    """Manuel AI analiz tetikler."""
    server = await db.get(Server, request.server_id)
    if not server:
        raise NotFoundError("Server", request.server_id)

    context = request.context or f"Sunucu: {server.name} ({server.hostname})"

    analysis = await ai_analyzer.trigger_analysis(
        db, server.id, context,
    )

    if not analysis:
        return {
            "data": None,
            "meta": {
                "timestamp": datetime.now(UTC).isoformat(),
                "message": "AI analiz çalıştırılamadı (API key eksik veya hata)",
            },
        }

    return {
        "data": AIAnalysisOut.model_validate(analysis).model_dump(),
        "meta": {"timestamp": datetime.now(UTC).isoformat()},
    }


@router.get("/ai/analyses/{server_id}")
async def get_analyses(
    server_id: int,
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _user: str = Depends(get_current_user),
) -> dict:
    """Sunucuya ait geçmiş AI analizlerini döndürür."""
    server = await db.get(Server, server_id)
    if not server:
        raise NotFoundError("Server", server_id)

    total = (
        await db.scalar(
            select(func.count(AIAnalysis.id)).where(AIAnalysis.server_id == server_id)
        )
        or 0
    )

    stmt = (
        select(AIAnalysis)
        .where(AIAnalysis.server_id == server_id)
        .order_by(AIAnalysis.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    result = await db.execute(stmt)
    analyses = result.scalars().all()

    return {
        "data": [AIAnalysisOut.model_validate(a).model_dump() for a in analyses],
        "meta": {"total": total, "page": page, "per_page": per_page},
    }
