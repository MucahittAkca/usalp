"""Backend API'ye metrik gönderici.

``MetricPayload``'ı JSON olarak serialize edip ``POST /api/v1/metrics``
endpoint'ine gönderir.  5xx ve ağ hatalarında tenacity ile 3 kez retry
yapar; 4xx hatalarında retry **yapmaz**.
"""

from __future__ import annotations

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import AgentConfig
from models import MetricPayload

log = structlog.get_logger()

_CONNECT_TIMEOUT = 5.0
_READ_TIMEOUT = 10.0


class ClientError(Exception):
    """4xx yanıtlarında fırlatılır; retry yapılmaz."""


def _should_retry(exc: BaseException) -> bool:
    """Retry sadece sunucu/ağ hataları için yapılır."""
    return not isinstance(exc, ClientError)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TransportError)),
    before_sleep=lambda rs: log.warning(
        "send_retry",
        attempt=rs.attempt_number,
        wait=rs.idle_for,
    ),
)
def send_metrics(payload: MetricPayload, config: AgentConfig) -> bool:
    """Metrikleri Backend API'ye gönderir. Başarısızlıkta 3 kez retry yapar."""
    url = f"{config.backend_url.rstrip('/')}/api/v1/metrics"

    response = httpx.post(
        url,
        content=payload.model_dump_json(),
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        timeout=httpx.Timeout(
            _READ_TIMEOUT,
            connect=_CONNECT_TIMEOUT,
            read=_READ_TIMEOUT,
            write=_READ_TIMEOUT,
            pool=_CONNECT_TIMEOUT,
        ),
    )

    if 400 <= response.status_code < 500:
        log.error(
            "send_client_error",
            status_code=response.status_code,
            body=response.text[:500],
        )
        raise ClientError(f"HTTP {response.status_code}")

    response.raise_for_status()

    log.info("metrics_sent", status_code=response.status_code)
    return True
