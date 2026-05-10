"""AI analiz servisi — Claude API entegrasyonu, bağlam paketleme ve güvenlik."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.ai_analysis import AIAnalysis
from app.models.log_entry import LogEntry
from app.models.metric import Metric
from app.models.service_status import ServiceStatus
from app.schemas.ai_analysis import AiAnalysisResult

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 4000
AI_COOLDOWN_SECONDS = 300

SYSTEM_PROMPT = """Sen Usalp platformunun Linux sistem analiz uzmanısın.
Sana sunulan log satırları, servis durumları ve sistem metrikleri üzerinden
kök neden analizi yapıyorsun.

ÇIKTI KURALLARI:
- Yalnızca ve yalnızca geçerli JSON döndür. Başka hiçbir metin ekleme.
- JSON şeması şu alanlardan oluşur:
  {
    "severity": "low|medium|high|critical",
    "category": "network_error|disk_issue|permission_issue|config_error|dependency_failure|resource_exhaustion",
    "summary": "string (Türkçe, 1-2 cümle)",
    "likely_causes": ["string", ...],
    "suggested_commands": [{"command": "string", "description": "string"}, ...],
    "confidence": float (0.0-1.0)
  }

ANALİZ PRENSİPLERİ:
- "Sorun kesinlikle şudur" deme. "Olası nedenler şunlardır" formatında yaz.
- Her suggested_command gerçek, çalışır bir Linux komutu olmalı.
- summary Türkçe yaz, teknik terimler İngilizce kalabilir (nginx, systemd vb.)
- confidence: kanıt ne kadar güçlüyse o kadar yüksek (0.9+ = çok net sinyal)
- Kategoriyi log ve metrik sinyallerinden çıkar:
    * "Connection refused", "ECONNRESET", "timeout" → network_error
    * "No space left", "I/O error", disk >%95 → disk_issue
    * "Permission denied", "EACCES", "403" → permission_issue
    * "Syntax error", "invalid config", "parse error" → config_error
    * "dependency failed", "can't connect" → dependency_failure
    * "OOM", "CPU throttled", "too many connections" → resource_exhaustion
"""

SENSITIVE_PATTERNS: list[tuple[str, str]] = [
    (r"password\s*=\s*\S+", "password=[REDACTED]"),
    (r"token\s*=\s*\S+", "token=[REDACTED]"),
    (r"key\s*=\s*\S+", "key=[REDACTED]"),
    (r"secret\s*=\s*\S+", "secret=[REDACTED]"),
    (r"Bearer\s+\S+", "Bearer [REDACTED]"),
    (r"sk-ant-[a-zA-Z0-9-]+", "[API_KEY_REDACTED]"),
]

_INJECTION_SIGNALS = [
    "ignore previous instructions",
    "system prompt",
    "you are now",
    "forget your",
    "new instructions",
]


# ---------------------------------------------------------------------------
# Güvenlik yardımcıları
# ---------------------------------------------------------------------------


def sanitize_for_ai(text: str) -> str:
    """Log içeriğindeki hassas verileri maskeler."""
    for pattern, replacement in SENSITIVE_PATTERNS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def check_prompt_injection(text: str) -> bool:
    """Loglar içinde prompt injection girişimi var mı kontrol eder."""
    lower = text.lower()
    return any(sig in lower for sig in _INJECTION_SIGNALS)


# ---------------------------------------------------------------------------
# Bağlam paketleme yardımcıları
# ---------------------------------------------------------------------------


def _format_services(
    failed: list[ServiceStatus],
    others: list[ServiceStatus],
) -> str:
    """Servis durumlarını okunabilir formata çevirir; failed olanlar önce."""
    lines: list[str] = []
    for s in failed:
        lines.append(f"[FAILED] {s.service_name}")
    for s in others:
        lines.append(f"[{s.status.upper()}] {s.service_name}")
    return "\n".join(lines) or "Tüm servisler normal"


def _format_logs(entries: list[LogEntry]) -> str:
    """Log satırlarını zaman-seviye-kaynak: mesaj formatında listeler."""
    if not entries:
        return "(yok)"
    return "\n".join(
        f"[{e.logged_at.strftime('%H:%M:%S')}] [{e.level}] {e.source_file}: "
        f"{sanitize_for_ai(e.message)}"
        for e in entries
    )


def build_context_package(
    logs: list[LogEntry],
    services: list[ServiceStatus],
    metrics: Metric,
) -> str:
    """AI'ye gönderilecek bağlam paketini hazırlar.

    Token limitini aşmamak için öncelik sırası uygulanır:
    1. Kritik/error logları (max 60 satır)
    2. Warning logları (max 20 satır)
    3. Servis durumları (failed olanlar önce)
    4. Sistem metrikleri
    """
    safe_logs = [
        log for log in logs if not check_prompt_injection(log.message)
    ]

    priority_logs = [
        entry for entry in safe_logs if entry.level in ("CRITICAL", "ERROR", "FATAL")
    ][:60]
    warning_logs = [entry for entry in safe_logs if entry.level == "WARNING"][:20]

    failed_services = [s for s in services if s.status == "failed"]
    other_services = [s for s in services if s.status != "failed"]

    context = f"""\
## SİSTEM METRİKLERİ
CPU: %{metrics.cpu_percent:.1f}  |  RAM: %{metrics.ram_percent:.1f}  |  Disk: %{metrics.disk_percent:.1f}
Load Average: {metrics.load_avg_1:.2f} / {metrics.load_avg_5:.2f} / {metrics.load_avg_15:.2f}

## SERVİS DURUMLARI
{_format_services(failed_services, other_services)}

## HATA LOGLARI (ÖNCELİKLİ)
{_format_logs(priority_logs)}

## UYARI LOGLARI
{_format_logs(warning_logs)}"""

    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n... (kısaltıldı)"

    return context


# ---------------------------------------------------------------------------
# Veritabanından bağlam verilerini çekme
# ---------------------------------------------------------------------------


async def _fetch_context_data(
    db: AsyncSession,
    server_id: int,
) -> tuple[list[LogEntry], list[ServiceStatus], Metric | None]:
    """Bir sunucuya ait son log, servis ve metrik verilerini DB'den çeker."""
    logs_stmt = (
        select(LogEntry)
        .where(LogEntry.server_id == server_id)
        .order_by(LogEntry.logged_at.desc())
        .limit(100)
    )
    logs_result = await db.execute(logs_stmt)
    logs = list(logs_result.scalars().all())

    services_stmt = (
        select(ServiceStatus)
        .where(ServiceStatus.server_id == server_id)
        .order_by(ServiceStatus.checked_at.desc())
    )
    services_result = await db.execute(services_stmt)
    seen: set[str] = set()
    services: list[ServiceStatus] = []
    for s in services_result.scalars().all():
        if s.service_name not in seen:
            seen.add(s.service_name)
            services.append(s)

    metrics_stmt = (
        select(Metric)
        .where(Metric.server_id == server_id)
        .order_by(Metric.recorded_at.desc())
        .limit(1)
    )
    metrics_result = await db.execute(metrics_stmt)
    latest_metric = metrics_result.scalar_one_or_none()

    return logs, services, latest_metric


# ---------------------------------------------------------------------------
# Cooldown kontrolü
# ---------------------------------------------------------------------------


async def can_trigger_analysis(db: AsyncSession, server_id: int) -> bool:
    """Aynı sunucu için son 5 dakika içinde analiz yapılmış mı kontrol eder."""
    stmt = (
        select(AIAnalysis.created_at)
        .where(AIAnalysis.server_id == server_id)
        .order_by(AIAnalysis.created_at.desc())
        .limit(1)
    )
    last_at = await db.scalar(stmt)
    if not last_at:
        return True
    elapsed = (datetime.now(UTC) - last_at.replace(tzinfo=UTC)).total_seconds()
    return elapsed >= AI_COOLDOWN_SECONDS


# ---------------------------------------------------------------------------
# Claude API çağrısı
# ---------------------------------------------------------------------------


class AiParseError(Exception):
    """Claude yanıtı beklenilen JSON şemasına parse edilemedi."""


async def call_claude(
    context_package: str,
    *,
    max_retries: int = 2,
) -> AiAnalysisResult:
    """Claude API'yi çağırır ve structured output döner.

    JSON parse başarısız olursa ``max_retries`` kez yeniden dener.
    """
    import anthropic

    client = anthropic.AsyncAnthropic(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
    )
    last_error: AiParseError | None = None

    for attempt in range(1, max_retries + 1):
        message = await client.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Aşağıdaki sistem verisini analiz et:\n\n"
                        f"{context_package}"
                    ),
                }
            ],
        )

        raw_text = message.content[0].text
        clean = raw_text.strip().removeprefix("```json").removesuffix("```").strip()

        logger.info(
            "claude_call_complete attempt=%d/%d input_tokens=%d output_tokens=%d",
            attempt,
            max_retries,
            message.usage.input_tokens,
            message.usage.output_tokens,
        )

        try:
            parsed = json.loads(clean)
            return AiAnalysisResult(**parsed)
        except (json.JSONDecodeError, ValueError) as e:
            last_error = AiParseError(
                f"Claude yanıtı parse edilemedi (deneme {attempt}/{max_retries}): {e}"
            )
            logger.warning(
                "claude_parse_retry attempt=%d/%d error=%s",
                attempt,
                max_retries,
                e,
            )

    raise last_error  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Ana tetikleme fonksiyonu
# ---------------------------------------------------------------------------


async def trigger_analysis(
    db: AsyncSession,
    server_id: int,
    alert_id: int | None = None,
) -> AIAnalysis | None:
    """Bir sunucu için AI analizi başlatır ve sonucu DB'ye kaydeder.

    Cooldown kontrolü bu fonksiyon içinde yapılır — hem manuel hem otomatik
    tetiklemelerde tek noktadan uygulanır.
    Hata durumunda exception fırlatmaz — sadece loglar ve None döner.
    (AI hatası sistemin çalışmasını durdurmamalı)
    """
    import anthropic

    if not settings.LLM_API_KEY:
        logger.warning("LLM_API_KEY tanımlı değil, AI analiz atlanıyor")
        return None

    if not await can_trigger_analysis(db, server_id):
        logger.info("ai_cooldown_active server_id=%d", server_id)
        return None

    try:
        logs, services, latest_metric = await _fetch_context_data(db, server_id)
        if not latest_metric:
            logger.warning("ai_skip_no_metrics server_id=%d", server_id)
            return None

        context = build_context_package(logs, services, latest_metric)

        result = await call_claude(context)

        analysis = AIAnalysis(
            server_id=server_id,
            alert_id=alert_id,
            category=result.category,
            severity=result.severity,
            summary=result.summary,
            causes=json.dumps(result.likely_causes, ensure_ascii=False),
            commands=json.dumps(
                [c.model_dump() for c in result.suggested_commands],
                ensure_ascii=False,
            ),
            confidence=result.confidence,
        )
        db.add(analysis)
        await db.flush()
        logger.info(
            "ai_analysis_complete server_id=%d category=%s confidence=%.2f",
            server_id,
            result.category,
            result.confidence,
        )
        return analysis

    except AiParseError as e:
        logger.error("ai_parse_error server_id=%d error=%s", server_id, e)
        return None
    except anthropic.APIError as e:
        logger.error("ai_api_error server_id=%d status=%s", server_id, e.status_code)
        return None
    except Exception:
        logger.exception("ai_unexpected_error server_id=%d", server_id)
        return None
