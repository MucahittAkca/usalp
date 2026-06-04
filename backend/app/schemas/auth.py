"""Kimlik doğrulama şemaları."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class TokenRequest(BaseModel):
    """Dashboard login isteği."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=300)


class TokenResponse(BaseModel):
    """JWT token yanıtı."""

    access_token: str
    token_type: str = "bearer"
