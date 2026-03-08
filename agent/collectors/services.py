"""Systemd servis durum toplayıcı."""

from __future__ import annotations

import subprocess


def collect(service_names: list[str]) -> list[dict]:
    """Verilen servislerin systemd durumlarını döndürür."""
    results: list[dict] = []
    for name in service_names:
        try:
            output = subprocess.run(
                ["systemctl", "is-active", name],
                capture_output=True,
                text=True,
                timeout=5,
            )
            status = output.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            status = "unknown"

        results.append({"service_name": name, "status": status})

    return results
