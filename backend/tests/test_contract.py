"""Backend'in ürettiği enum değerleri frontend sözleşmesiyle uyumlu mu?"""

from __future__ import annotations

import json
from pathlib import Path

from app.services.alert_engine import ALERT_TYPES


def _contract() -> dict[str, list[str]]:
    contract_path = Path(__file__).resolve().parents[2] / "contracts" / "api-contract.json"
    return json.loads(contract_path.read_text(encoding="utf-8"))


def test_backend_alert_types_exist_in_contract() -> None:
    contract = _contract()
    assert set(ALERT_TYPES) <= set(contract["alert_types"])


def test_server_status_contract_contains_backend_values() -> None:
    contract = _contract()
    assert {"online", "offline", "warning"} <= set(contract["server_statuses"])
