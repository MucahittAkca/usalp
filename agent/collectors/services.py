"""systemd servis durum toplayıcı.

Yapılandırmada tanımlanan her servis için ``systemctl show``
komutuyla ``ActiveState``, ``SubState`` ve ``ActiveEnterTimestamp``
değerlerini okur.  Servis listesi YAML config'den gelir.
"""

from __future__ import annotations

import subprocess
import time
from datetime import datetime, timezone

import structlog

from agent.models import ServiceStatus

log = structlog.get_logger()

_SHOW_PROPERTIES = "ActiveState,SubState,ActiveEnterTimestamp"
_TIMEOUT = 5


def _parse_timestamp(raw: str) -> int | None:
    """``ActiveEnterTimestamp`` değerini saniye farkına çevirir.

    Boş veya parse edilemeyen değerlerde ``None`` döndürür.
    """
    if not raw or raw == "n/a":
        return None

    try:
        dt = datetime.strptime(raw, "%a %Y-%m-%d %H:%M:%S %Z")
        dt = dt.replace(tzinfo=timezone.utc)
        return int(time.time() - dt.timestamp())
    except (ValueError, OSError):
        return None


def _query_service(name: str) -> ServiceStatus:
    """Tek bir servisin durumunu ``systemctl show`` ile sorgular."""
    try:
        result = subprocess.run(
            ["systemctl", "show", name, f"--property={_SHOW_PROPERTIES}"],
            capture_output=True,
            text=True,
            timeout=_TIMEOUT,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        log.warning("systemctl_failed", service=name, error=str(exc))
        return ServiceStatus(
            name=name, status="unknown", sub_state="unknown", since_seconds=None
        )

    props: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" in line:
            key, _, value = line.partition("=")
            props[key.strip()] = value.strip()

    return ServiceStatus(
        name=name,
        status=props.get("ActiveState", "unknown"),
        sub_state=props.get("SubState", "unknown"),
        since_seconds=_parse_timestamp(props.get("ActiveEnterTimestamp", "")),
    )


def collect(service_names: list[str]) -> list[ServiceStatus]:
    """Verilen servis listesinin durumlarını toplar."""
    return [_query_service(name) for name in service_names]
