"""Ortak API bağımlılıkları."""

from __future__ import annotations

from fastapi import Header, HTTPException

from app.config import settings


async def verify_agent_api_key(x_api_key: str = Header(...)) -> str:
    """Agent API key doğrulaması."""
    if x_api_key != settings.AGENT_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key
