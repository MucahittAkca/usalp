"""Kimlik doğrulama şemaları."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class TokenRequest(BaseModel):
    """Dashboard login isteği."""

    model_config = ConfigDict(extra="forbid")

    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT token yanıtı."""

    access_token: str
    token_type: str = "bearer"
