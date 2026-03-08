"""Usalp Agent — Sunucu metriklerini toplar ve merkezi sisteme gönderir."""

from __future__ import annotations

import argparse
import asyncio
import logging
from pathlib import Path

import yaml

from collectors import cpu, disk, logs, memory, network, services

logger = logging.getLogger("usalp-agent")


def load_config(path: Path) -> dict:
    """YAML konfigürasyon dosyasını yükler."""
    with open(path) as f:
        return yaml.safe_load(f)


async def collect_metrics(config: dict) -> dict:
    """Tüm aktif collector'lardan metrik toplar."""
    metrics_cfg = config["collection"]["metrics"]
    data: dict = {}

    if metrics_cfg.get("cpu"):
        data.update(cpu.collect())
    if metrics_cfg.get("memory"):
        data.update(memory.collect())
    if metrics_cfg.get("disk"):
        data.update(disk.collect())
    if metrics_cfg.get("network"):
        data.update(network.collect())
    if metrics_cfg.get("load_avg"):
        data["load_avg_1"], data["load_avg_5"], data["load_avg_15"] = (
            cpu.collect_load_avg()
        )

    return data


async def run(config: dict) -> None:
    """Ana döngü: belirli aralıklarla metrik toplar ve gönderir."""
    import httpx

    interval = config["collection"]["interval_seconds"]
    backend_url = config["server"]["backend_url"]
    api_key = config["server"]["api_key"]

    async with httpx.AsyncClient(
        base_url=backend_url,
        headers={"X-API-Key": api_key},
        timeout=30.0,
    ) as client:
        while True:
            try:
                payload = await collect_metrics(config)

                if config.get("services", {}).get("enabled"):
                    svc_list = config["services"].get("watch", [])
                    payload["services"] = services.collect(svc_list)

                if config.get("logs", {}).get("enabled"):
                    log_sources = config["logs"].get("sources", [])
                    payload["logs"] = logs.collect(log_sources)

                response = await client.post("/metrics", json=payload)
                response.raise_for_status()
                logger.info("Metrikler gönderildi (%s)", response.status_code)

            except Exception:
                logger.exception("Metrik gönderimi başarısız")

            await asyncio.sleep(interval)


def main() -> None:
    """CLI giriş noktası."""
    parser = argparse.ArgumentParser(description="Usalp Monitoring Agent")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("agent.yaml"),
        help="Konfigürasyon dosyası yolu",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    log_level = config.get("logging", {}).get("level", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("Usalp Agent başlatılıyor...")
    asyncio.run(run(config))


if __name__ == "__main__":
    main()
