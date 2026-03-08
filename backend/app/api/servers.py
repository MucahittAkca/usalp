"""Sunucu endpoint'leri."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["servers"])


@router.get("/servers")
async def list_servers() -> dict:
    """Kayıtlı sunucuların listesini döndürür."""
    # TODO(v1): DB'den sunucu listesi çek
    return {"data": [], "meta": {"total": 0, "page": 1, "per_page": 20}}


@router.get("/servers/{server_id}")
async def get_server(server_id: int) -> dict:
    """Belirli bir sunucunun detayını döndürür."""
    # TODO(v1): DB'den sunucu detayı çek
    return {"data": {}, "meta": {"timestamp": ""}}


@router.get("/servers/{server_id}/metrics")
async def get_server_metrics(server_id: int) -> dict:
    """Sunucuya ait metrikleri döndürür."""
    # TODO(v1): Filtreli metrik sorgusu
    return {"data": [], "meta": {"total": 0, "page": 1, "per_page": 20}}


@router.get("/servers/{server_id}/services")
async def get_server_services(server_id: int) -> dict:
    """Sunucuya ait servis durumlarını döndürür."""
    # TODO(v1): DB'den servis durumları
    return {"data": [], "meta": {"timestamp": ""}}


@router.get("/servers/{server_id}/logs")
async def get_server_logs(server_id: int) -> dict:
    """Sunucuya ait log kayıtlarını döndürür."""
    # TODO(v1): Filtreli log sorgusu
    return {"data": [], "meta": {"total": 0, "page": 1, "per_page": 20}}
