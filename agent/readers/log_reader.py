"""Log dosyası tail okuyucu ve hata-pattern filtresi.

Yapılandırmada tanımlanan her log dosyasının son N satırını okur,
belirlenen minimum seviyeye uyan satırları ``LogEntry`` modeline
dönüştürür.  Tek bir toplama döngüsünde en fazla ``MAX_ENTRIES``
satır döndürülür.
"""

from __future__ import annotations

import re
from collections import deque
from datetime import UTC, datetime
from pathlib import Path

import structlog

from agent.config import LogFileConfig
from agent.models import LogEntry

log = structlog.get_logger()

MAX_ENTRIES = 200

ERROR_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p)
    for p in [
        r"\bERROR\b",
        r"\bCRITICAL\b",
        r"\bFATAL\b",
        r"\bException\b",
        r"\bTraceback\b",
        r"\bPanic\b",
        r"\[error\]",
        r"\[crit\]",
        r"SQLSTATE",
        r"OOM",
    ]
]

_LEVEL_PATTERN = re.compile(
    r"\b(CRITICAL|FATAL|ERROR|WARNING|WARN|INFO|DEBUG)\b"
    r"|\[(crit|error|warn|warning|info|debug)\]",
    re.IGNORECASE,
)

_TIMESTAMP_FORMATS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%b %d %H:%M:%S",
    "%d/%b/%Y:%H:%M:%S %z",
]

_TIMESTAMP_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}"
    r"|[A-Z][a-z]{2}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2}"
    r"|\d{2}/[A-Z][a-z]{2}/\d{4}:\d{2}:\d{2}:\d{2}\s+[+-]\d{4}"
)

_LEVEL_PRIORITY = {
    "DEBUG": 0,
    "INFO": 1,
    "WARNING": 2,
    "WARN": 2,
    "ERROR": 3,
    "CRITICAL": 4,
    "FATAL": 4,
}


def _tail(filepath: Path, n: int) -> list[str]:
    """Dosyanın son *n* satırını verimli biçimde okur."""
    try:
        with filepath.open("r", encoding="utf-8", errors="strict") as fh:
            return list(deque(fh, maxlen=n))
    except FileNotFoundError:
        log.warning("log_file_not_found", path=str(filepath))
    except PermissionError:
        log.warning("log_file_permission_denied", path=str(filepath))
    except UnicodeDecodeError:
        log.warning("log_file_binary_skipped", path=str(filepath))
    return []


def _extract_level(line: str) -> str:
    """Satırdan log seviyesini çıkarır, bulamazsa ``'UNKNOWN'`` döner."""
    match = _LEVEL_PATTERN.search(line)
    if not match:
        return "UNKNOWN"
    raw = (match.group(1) or match.group(2)).upper()
    if raw == "WARN":
        return "WARNING"
    if raw == "CRIT":
        return "CRITICAL"
    return raw


def _parse_timestamp(line: str) -> datetime:
    """Satırdaki zaman damgasını parse eder, başarısızsa ``now(UTC)`` döner."""
    ts_match = _TIMESTAMP_PATTERN.search(line)
    if not ts_match:
        return datetime.now(tz=UTC)

    raw_ts = ts_match.group(0)
    for fmt in _TIMESTAMP_FORMATS:
        try:
            dt = datetime.strptime(raw_ts, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            if dt.year == 1900:
                dt = dt.replace(year=datetime.now(tz=UTC).year)
            return dt
        except ValueError:
            continue

    return datetime.now(tz=UTC)


def _matches_min_level(level: str, min_level: str) -> bool:
    """Satır seviyesi, minimum eşik seviyesine eşit veya üstünde mi?"""
    return _LEVEL_PRIORITY.get(level, 99) >= _LEVEL_PRIORITY.get(min_level, 0)


def _matches_pattern(line: str) -> bool:
    """Satır hata pattern'larından herhangi birine uyuyor mu?"""
    return any(p.search(line) for p in ERROR_PATTERNS)


def read_logs(configs: list[LogFileConfig]) -> list[LogEntry]:
    """Yapılandırılmış tüm log dosyalarını okur ve filtreli sonucu döndürür."""
    entries: list[LogEntry] = []

    for cfg in configs:
        filepath = Path(cfg.path)
        lines = _tail(filepath, cfg.tail_lines)

        for raw_line in lines:
            raw_line = raw_line.rstrip("\n")
            if not raw_line:
                continue

            level = _extract_level(raw_line)

            if not (_matches_min_level(level, cfg.min_level) or _matches_pattern(raw_line)):
                continue

            entries.append(
                LogEntry(
                    source_file=cfg.path,
                    level=level if level != "UNKNOWN" else cfg.min_level,
                    message=raw_line[:500],
                    raw_line=raw_line[:1000],
                    logged_at=_parse_timestamp(raw_line),
                )
            )

            if len(entries) >= MAX_ENTRIES:
                return entries

    return entries
