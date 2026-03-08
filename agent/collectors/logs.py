"""Log dosyası toplayıcı."""

from __future__ import annotations

import subprocess


def collect(sources: list[dict]) -> list[dict]:
    """Konfigürasyonda belirtilen log dosyalarının son satırlarını toplar."""
    entries: list[dict] = []
    for source in sources:
        path = source["path"]
        try:
            output = subprocess.run(
                ["tail", "-n", "50", path],
                capture_output=True,
                text=True,
                timeout=5,
            )
            for line in output.stdout.strip().splitlines():
                entries.append({
                    "source_file": path,
                    "raw_line": line,
                    "level": _detect_level(line),
                })
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return entries


_LEVEL_KEYWORDS = {
    "error": "error",
    "err": "error",
    "critical": "critical",
    "crit": "critical",
    "warning": "warning",
    "warn": "warning",
    "info": "info",
}


def _detect_level(line: str) -> str:
    """Log satırından seviye tespit eder."""
    lower = line.lower()
    for keyword, level in _LEVEL_KEYWORDS.items():
        if keyword in lower:
            return level
    return "info"
