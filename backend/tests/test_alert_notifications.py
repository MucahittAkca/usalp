"""Alert notification servis testleri."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from app.config import settings
from app.core.security import hash_api_key
from app.models.alert import Alert
from app.models.server import Server
from app.services import alert_notifications
from app.services.alert_notifications import AlertNotification


def _notification() -> AlertNotification:
    return AlertNotification(
        alert_id=10,
        server_id=1,
        server_name="web-01",
        hostname="web-01.local",
        ip_address="10.0.0.1",
        alert_type="cpu_threshold",
        dedupe_key="cpu_threshold",
        severity="critical",
        message="CPU kullanımı kritik: %95.0",
        created_at=datetime(2026, 3, 11, 12, 0, tzinfo=UTC),
    )


def _clear_channels(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ALERT_NOTIFICATIONS_ENABLED", True)
    monkeypatch.setattr(settings, "ALERT_EMAIL_HOST", "")
    monkeypatch.setattr(settings, "ALERT_EMAIL_FROM", "")
    monkeypatch.setattr(settings, "ALERT_EMAIL_TO", "")
    monkeypatch.setattr(settings, "ALERT_TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr(settings, "ALERT_TELEGRAM_CHAT_ID", "")
    monkeypatch.setattr(settings, "ALERT_SLACK_WEBHOOK_URL", "")


def test_build_alert_notifications_snapshot() -> None:
    """ORM nesneleri session bağımsız notification snapshot'a çevrilir."""
    server = Server(
        id=1,
        name="web-01",
        hostname="web-01.local",
        ip_address="10.0.0.1",
        api_key=hash_api_key("key-web"),
        status="warning",
    )
    alert = Alert(
        id=10,
        server_id=1,
        type="cpu_threshold",
        dedupe_key="cpu_threshold",
        severity="critical",
        message="CPU kritik",
        created_at=datetime(2026, 3, 11, 12, 0, tzinfo=UTC),
    )

    notifications = alert_notifications.build_alert_notifications([alert], server)

    assert len(notifications) == 1
    assert notifications[0].alert_id == 10
    assert notifications[0].server_name == "web-01"
    assert notifications[0].message == "CPU kritik"


@pytest.mark.asyncio
async def test_notify_alerts_no_channels(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hiçbir kanal konfigüre değilse gönderim yapılmaz."""
    _clear_channels(monkeypatch)

    results = await alert_notifications.notify_alerts([_notification()])

    assert results == []


@pytest.mark.asyncio
async def test_notify_alerts_can_be_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """Global enable flag false ise kanallar dolu olsa bile gönderim yapılmaz."""
    _clear_channels(monkeypatch)
    monkeypatch.setattr(settings, "ALERT_NOTIFICATIONS_ENABLED", False)
    monkeypatch.setattr(settings, "ALERT_SLACK_WEBHOOK_URL", "https://hooks.slack.test/x")

    results = await alert_notifications.notify_alerts([_notification()])

    assert results == []


@pytest.mark.asyncio
async def test_notify_alert_sends_slack_and_telegram(monkeypatch: pytest.MonkeyPatch) -> None:
    """Slack ve Telegram kanalları HTTP JSON post ile gönderilir."""
    _clear_channels(monkeypatch)
    monkeypatch.setattr(settings, "ALERT_SLACK_WEBHOOK_URL", "https://hooks.slack.test/x")
    monkeypatch.setattr(settings, "ALERT_TELEGRAM_BOT_TOKEN", "telegram-token")
    monkeypatch.setattr(settings, "ALERT_TELEGRAM_CHAT_ID", "12345")
    post_json = AsyncMock()
    monkeypatch.setattr(alert_notifications, "_post_json", post_json)

    results = await alert_notifications.notify_alert(_notification())

    assert post_json.await_count == 2
    assert {result.channel for result in results} == {"slack", "telegram"}
    assert all(result.delivered for result in results)
    calls_by_url = {call.args[0]: call.args[1] for call in post_json.await_args_list}
    assert calls_by_url["https://hooks.slack.test/x"]["text"].find("CPU kullanımı kritik") >= 0
    assert (
        calls_by_url["https://api.telegram.org/bottelegram-token/sendMessage"]["chat_id"]
        == "12345"
    )


@pytest.mark.asyncio
async def test_notify_alert_sends_email(monkeypatch: pytest.MonkeyPatch) -> None:
    """SMTP kanalı etkinse e-posta gönderimi background thread'e devredilir."""
    _clear_channels(monkeypatch)
    monkeypatch.setattr(settings, "ALERT_EMAIL_HOST", "smtp.example.test")
    monkeypatch.setattr(settings, "ALERT_EMAIL_FROM", "alerts@example.test")
    monkeypatch.setattr(settings, "ALERT_EMAIL_TO", "ops@example.test,dev@example.test")
    sent: list[AlertNotification] = []

    def fake_send_email(notification: AlertNotification) -> None:
        sent.append(notification)

    monkeypatch.setattr(alert_notifications, "_send_email_sync", fake_send_email)

    results = await alert_notifications.notify_alert(_notification())

    assert sent == [_notification()]
    assert len(results) == 1
    assert results[0].channel == "email"
    assert results[0].delivered is True


@pytest.mark.asyncio
async def test_notify_alert_channel_failure_is_returned(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Kanal hatası exception olarak yukarı taşınmaz; sonuçta işaretlenir."""
    _clear_channels(monkeypatch)
    monkeypatch.setattr(settings, "ALERT_SLACK_WEBHOOK_URL", "https://hooks.slack.test/x")
    post_json = AsyncMock(side_effect=RuntimeError("webhook down"))
    monkeypatch.setattr(alert_notifications, "_post_json", post_json)

    results = await alert_notifications.notify_alert(_notification())

    assert len(results) == 1
    assert results[0].channel == "slack"
    assert results[0].delivered is False
    assert results[0].error == "webhook down"
