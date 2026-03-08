"""AI analiz servisi — Claude API entegrasyonu."""

from __future__ import annotations

import json
import logging

from app.config import settings

logger = logging.getLogger(__name__)

AI_ANALYSIS_SCHEMA = {
    "severity": "low | medium | high | critical",
    "category": "network_error | disk_issue | permission_issue | config_error | dependency_failure | resource_exhaustion",
    "summary": "Kısa, Türkçe açıklama (1-2 cümle)",
    "likely_causes": ["Olası neden 1", "Olası neden 2"],
    "suggested_commands": [{"command": "...", "description": "..."}],
    "confidence": 0.0,
}


async def analyze(context: str) -> dict:
    """Verilen bağlam ile Claude API'den analiz talep eder."""
    import anthropic

    if not settings.LLM_API_KEY:
        logger.warning("LLM_API_KEY tanımlı değil, AI analiz atlanıyor")
        return {}

    client = anthropic.AsyncAnthropic(api_key=settings.LLM_API_KEY)

    message = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": (
                    "Sen bir Linux sistem yöneticisi asistanısın. "
                    "Aşağıdaki sunucu verisini analiz et ve JSON formatında yanıt ver.\n\n"
                    f"Beklenen şema: {json.dumps(AI_ANALYSIS_SCHEMA, ensure_ascii=False)}\n\n"
                    f"Veri:\n{context}"
                ),
            }
        ],
    )

    try:
        return json.loads(message.content[0].text)
    except (json.JSONDecodeError, IndexError):
        logger.error("AI yanıtı parse edilemedi: %s", message.content)
        return {}
