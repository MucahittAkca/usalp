"""Custom exception handler'lar."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class NotFoundError(Exception):
    """Kayıt bulunamadığında fırlatılır."""

    def __init__(self, resource: str, resource_id: int | str) -> None:
        self.resource = resource
        self.resource_id = resource_id
        super().__init__(f"{resource} #{resource_id} bulunamadı")


class DuplicateAlertError(Exception):
    """Aynı tipte aktif alert varken tekrar oluşturulmaya çalışıldığında."""


def register_exception_handlers(app: FastAPI) -> None:
    """Uygulamaya global exception handler'ları kaydeder."""

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "error": {
                    "code": "NOT_FOUND",
                    "message": str(exc),
                    "details": {"resource": exc.resource, "id": exc.resource_id},
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("İşlenmeyen hata: %s", exc)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Beklenmeyen bir hata oluştu",
                }
            },
        )
