"""Güvenlik yardımcıları — API key doğrulama, secret maskeleme."""

from __future__ import annotations

import re

_MASK_PATTERN = re.compile(
    r"(password|token|key|secret|api_key)\s*[=:]\s*\S+",
    re.IGNORECASE,
)


def mask_secrets(text: str) -> str:
    """Log satırlarında hassas bilgileri maskeler."""
    return _MASK_PATTERN.sub(r"\1=***MASKED***", text)
