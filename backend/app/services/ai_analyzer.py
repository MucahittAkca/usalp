"""AI analiz servisi — Claude API entegrasyonu, bağlam paketleme ve güvenlik."""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime

import httpx
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
    "evidence_lines": ["string", ...],
    "suggested_commands": [
      {
        "command": "string",
        "description": "string",
        "risk_level": "low|medium|high"
      },
      ...
    ],
    "confidence": float (0.0-1.0)
  }

ANALİZ PRENSİPLERİ:
- "Sorun kesinlikle şudur" deme. "Olası nedenler şunlardır" formatında yaz.
- Her suggested_command gerçek, çalışır bir Linux komutu olmalı.
- Her evidence_lines girdisi sana verilen bağlamdaki metrik, servis veya log satırından kısa ve birebir destek almalı; uydurma kanıt ekleme.
- risk_level:
    * "low": sadece okuma/inceleme komutları (journalctl, systemctl status, df, free, top, nginx -t)
    * "medium": servis reload/restart, config doğrulama sonrası sınırlı değişiklik, log rotate gibi etkisi sınırlı operasyonlar
    * "high": veri silme, paket kaldırma/kurma, firewall değiştirme, disk formatlama, chmod/chown geniş kapsamlı değişiklik, kill -9
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


class AiProviderError(Exception):
    """LLM sağlayıcısı istek veya yanıt seviyesinde hata döndürdü."""


class AiAnalysisUnavailableError(Exception):
    """Analizin neden üretilemediğini endpoint'e güvenli şekilde taşır."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _content_block_text(block: object) -> str | None:
    """Anthropic/OpenRouter content block içinden text alanını güvenli çıkarır."""
    if isinstance(block, dict):
        block_type = block.get("type")
        text = block.get("text")
        if block_type == "text" and isinstance(text, str):
            return text
        return None

    block_type = getattr(block, "type", None)
    text = getattr(block, "text", None)
    if block_type == "text" and isinstance(text, str):
        return text

    return None


def _extract_message_text(content: object) -> str:
    """Yanıttaki text bloklarını birleştirir; thinking/tool bloklarını atlar."""
    if isinstance(content, str):
        text = content.strip()
        if text:
            return text
        raise AiParseError("Claude yanıtında text content yok.")

    if not isinstance(content, list):
        raise AiParseError("Claude yanıt content formatı desteklenmiyor.")

    text_parts = [
        text
        for block in content
        if (text := _content_block_text(block)) is not None
    ]
    raw_text = "\n".join(text_parts).strip()
    if not raw_text:
        raise AiParseError("Claude yanıtında text bloğu yok.")
    return raw_text


def _extract_json_text(raw_text: str) -> str:
    """Model yanıtındaki JSON objesini markdown/reasoning sarmalından ayıklar."""
    text = raw_text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text).strip()

    if text.startswith("{") and text.endswith("}"):
        return text

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        return text[start:end + 1]

    return text


def _is_openrouter_config() -> bool:
    """OpenRouter base URL/model ayarı OpenAI-compatible chat endpoint'i kullanır."""
    base_url = settings.LLM_BASE_URL.lower()
    return "openrouter.ai" in base_url or settings.LLM_MODEL.startswith("deepseek/")


def _openrouter_chat_url() -> str:
    """LLM_BASE_URL değerinden OpenRouter chat completions URL'sini üretir."""
    base_url = settings.LLM_BASE_URL.rstrip("/")
    if base_url.endswith("/chat/completions"):
        return base_url
    if base_url.endswith("/api/v1"):
        return f"{base_url}/chat/completions"
    if base_url.endswith("/api"):
        return f"{base_url}/v1/chat/completions"
    if "openrouter.ai" in base_url:
        return f"{base_url}/api/v1/chat/completions"
    return f"{base_url}/chat/completions"


def _parse_ai_result(raw_text: str) -> AiAnalysisResult:
    """Ham model çıktısını beklenen analiz şemasına parse eder."""
    clean = _extract_json_text(raw_text)
    parsed = json.loads(clean)
    return AiAnalysisResult(**parsed)


async def _call_openrouter_chat(
    context_package: str,
    *,
    max_retries: int,
) -> AiAnalysisResult:
    """OpenRouter OpenAI-compatible chat completions endpoint'ini çağırır."""
    last_error: AiParseError | None = None

    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(45.0, connect=10.0)) as client:
                response = await client.post(
                    _openrouter_chat_url(),
                    headers={
                        "Authorization": f"Bearer {settings.LLM_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.LLM_MODEL,
                        "max_tokens": 1024,
                        "temperature": 0.2,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {
                                "role": "user",
                                "content": (
                                    "Aşağıdaki sistem verisini analiz et:\n\n"
                                    f"{context_package}"
                                ),
                            },
                        ],
                    },
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as e:
            body = e.response.text[:500]
            raise AiProviderError(
                f"OpenRouter HTTP {e.response.status_code}: {body}"
            ) from e
        except httpx.TransportError as e:
            raise AiProviderError(f"OpenRouter bağlantı hatası: {e}") from e

        body = response.json()
        choices = body.get("choices") if isinstance(body, dict) else None
        if not choices:
            raise AiProviderError("OpenRouter yanıtında choices alanı yok.")

        message = choices[0].get("message", {}) if isinstance(choices[0], dict) else {}
        raw_text = _extract_message_text(message.get("content", ""))

        usage = body.get("usage", {}) if isinstance(body, dict) else {}
        logger.info(
            "openrouter_call_complete attempt=%d/%d input_tokens=%s output_tokens=%s model=%s",
            attempt,
            max_retries,
            usage.get("prompt_tokens"),
            usage.get("completion_tokens"),
            settings.LLM_MODEL,
        )

        try:
            return _parse_ai_result(raw_text)
        except (json.JSONDecodeError, ValueError) as e:
            last_error = AiParseError(
                f"OpenRouter yanıtı parse edilemedi (deneme {attempt}/{max_retries}): {e}"
            )
            logger.warning(
                "openrouter_parse_retry attempt=%d/%d error=%s",
                attempt,
                max_retries,
                e,
            )

    raise last_error  # type: ignore[misc]


async def call_claude(
    context_package: str,
    *,
    max_retries: int = 2,
) -> AiAnalysisResult:
    """Claude API'yi çağırır ve structured output döner.

    JSON parse başarısız olursa ``max_retries`` kez yeniden dener.
    """
    if _is_openrouter_config():
        return await _call_openrouter_chat(context_package, max_retries=max_retries)

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

        raw_text = _extract_message_text(message.content)

        logger.info(
            "claude_call_complete attempt=%d/%d input_tokens=%d output_tokens=%d",
            attempt,
            max_retries,
            message.usage.input_tokens,
            message.usage.output_tokens,
        )

        try:
            return _parse_ai_result(raw_text)
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
    *,
    raise_on_failure: bool = False,
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
        if raise_on_failure:
            raise AiAnalysisUnavailableError(
                "missing_api_key",
                "LLM_API_KEY tanımlı değil. Production .env dosyasını ve backend restart'ını kontrol edin.",
            )
        return None

    if not await can_trigger_analysis(db, server_id):
        logger.info("ai_cooldown_active server_id=%d", server_id)
        if raise_on_failure:
            raise AiAnalysisUnavailableError(
                "cooldown_active",
                "Bu sunucu için çok yakın zamanda analiz yapıldı. 5 dakika bekleyin.",
            )
        return None

    try:
        logs, services, latest_metric = await _fetch_context_data(db, server_id)
        if not latest_metric:
            logger.warning("ai_skip_no_metrics server_id=%d", server_id)
            if raise_on_failure:
                raise AiAnalysisUnavailableError(
                    "missing_metrics",
                    "Bu sunucu için henüz metrik yok. Agent ilk başarılı metrik gönderimini yaptıktan sonra tekrar deneyin.",
                )
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
            evidence_lines=json.dumps(result.evidence_lines, ensure_ascii=False),
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

    except AiAnalysisUnavailableError:
        raise
    except AiParseError as e:
        logger.error("ai_parse_error server_id=%d error=%s", server_id, e)
        if raise_on_failure:
            raise AiAnalysisUnavailableError(
                "parse_error",
                "AI modeli beklenen JSON formatında yanıt vermedi. LLM_MODEL değerini veya backend loglarını kontrol edin.",
            ) from e
        return None
    except AiProviderError as e:
        logger.error("ai_provider_error server_id=%d error=%s", server_id, e)
        if raise_on_failure:
            raise AiAnalysisUnavailableError(
                "provider_error",
                "AI sağlayıcısı isteği tamamlayamadı. OpenRouter API key, model adı, bakiye/rate limit ve LLM_BASE_URL değerlerini kontrol edin.",
            ) from e
        return None
    except anthropic.APIError as e:
        logger.error(
            "ai_api_error server_id=%d status=%s error=%s",
            server_id,
            e.status_code,
            e,
        )
        if raise_on_failure:
            raise AiAnalysisUnavailableError(
                "provider_error",
                "AI sağlayıcısı isteği tamamlayamadı. API key, model adı, bakiye/rate limit ve LLM_BASE_URL değerlerini kontrol edin.",
            ) from e
        return None
    except Exception as e:
        logger.exception("ai_unexpected_error server_id=%d", server_id)
        if raise_on_failure:
            raise AiAnalysisUnavailableError(
                "unexpected_error",
                "AI analiz beklenmeyen bir backend hatasıyla durdu. Backend loglarını kontrol edin.",
            ) from e
        return None
