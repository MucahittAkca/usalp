"""Alert bildirimleri — e-posta, Telegram ve Slack gönderimi."""

from __future__ import annotations

import asyncio
import logging
import smtplib
from collections.abc import Awaitable
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage

import httpx

from app.config import settings
from app.models.alert import Alert
from app.models.server import Server

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AlertNotification:
    """Background task'a taşınabilecek immutable alert bildirimi."""

    alert_id: int
    server_id: int
    server_name: str
    hostname: str
    ip_address: str
    alert_type: str
    dedupe_key: str
    severity: str
    message: str
    created_at: datetime | None


@dataclass(frozen=True)
class NotificationDelivery:
    """Tek kanal gönderim sonucu."""

    channel: str
    delivered: bool
    error: str | None = None


def build_alert_notifications(alerts: list[Alert], server: Server) -> list[AlertNotification]:
    """Alert ORM nesnelerini DB session'dan bağımsız bildirim verisine dönüştürür."""
    return [
        AlertNotification(
            alert_id=alert.id,
            server_id=server.id,
            server_name=server.name,
            hostname=server.hostname,
            ip_address=server.ip_address,
            alert_type=alert.type,
            dedupe_key=alert.dedupe_key,
            severity=alert.severity,
            message=alert.message,
            created_at=alert.created_at,
        )
        for alert in alerts
    ]


async def notify_alerts(notifications: list[AlertNotification]) -> list[NotificationDelivery]:
    """Birden fazla alert bildirimini gönderir; kanal hatalarını yutar ve loglar."""
    results: list[NotificationDelivery] = []
    if not settings.ALERT_NOTIFICATIONS_ENABLED:
        return results

    for notification in notifications:
        results.extend(await notify_alert(notification))
    return results


async def notify_alert(notification: AlertNotification) -> list[NotificationDelivery]:
    """Tek alert bildirimini etkin kanallara gönderir."""
    tasks: list[Awaitable[NotificationDelivery]] = []

    if _email_enabled():
        tasks.append(_deliver("email", _send_email(notification)))
    if _telegram_enabled():
        tasks.append(_deliver("telegram", _send_telegram(notification)))
    if _slack_enabled():
        tasks.append(_deliver("slack", _send_slack(notification)))

    if not tasks:
        logger.debug("alert_notification_skipped_no_channels alert_id=%d", notification.alert_id)
        return []

    return list(await asyncio.gather(*tasks))


async def _deliver(channel: str, task: Awaitable[None]) -> NotificationDelivery:
    """Kanal hatalarının metrik alımını etkilememesi için güvenli gönderim sarmalayıcı."""
    try:
        await task
        return NotificationDelivery(channel=channel, delivered=True)
    except Exception as exc:
        logger.exception("alert_notification_failed channel=%s", channel)
        return NotificationDelivery(channel=channel, delivered=False, error=str(exc))


def _email_enabled() -> bool:
    return bool(
        settings.ALERT_EMAIL_HOST
        and settings.ALERT_EMAIL_FROM
        and _email_recipients()
    )


def _telegram_enabled() -> bool:
    return bool(settings.ALERT_TELEGRAM_BOT_TOKEN and settings.ALERT_TELEGRAM_CHAT_ID)


def _slack_enabled() -> bool:
    return bool(settings.ALERT_SLACK_WEBHOOK_URL)


def _email_recipients() -> list[str]:
    return [
        recipient.strip()
        for recipient in settings.ALERT_EMAIL_TO.split(",")
        if recipient.strip()
    ]


def _subject(notification: AlertNotification) -> str:
    return (
        f"[Usalp] {notification.severity.upper()} "
        f"{notification.alert_type} on {notification.server_name}"
    )


def _body(notification: AlertNotification) -> str:
    created_at = notification.created_at.isoformat() if notification.created_at else "-"
    return "\n".join(
        [
            "Usalp alert",
            "",
            f"Server: {notification.server_name}",
            f"Hostname: {notification.hostname}",
            f"IP: {notification.ip_address}",
            f"Severity: {notification.severity}",
            f"Type: {notification.alert_type}",
            f"Dedupe key: {notification.dedupe_key}",
            f"Message: {notification.message}",
            f"Alert ID: {notification.alert_id}",
            f"Created at: {created_at}",
        ]
    )


async def _send_slack(notification: AlertNotification) -> None:
    await _post_json(
        settings.ALERT_SLACK_WEBHOOK_URL,
        {"text": _body(notification)},
    )


async def _send_telegram(notification: AlertNotification) -> None:
    token = settings.ALERT_TELEGRAM_BOT_TOKEN
    await _post_json(
        f"https://api.telegram.org/bot{token}/sendMessage",
        {
            "chat_id": settings.ALERT_TELEGRAM_CHAT_ID,
            "text": _body(notification),
            "disable_web_page_preview": True,
        },
    )


async def _post_json(url: str, payload: dict[str, object]) -> None:
    async with httpx.AsyncClient(timeout=settings.ALERT_NOTIFICATION_TIMEOUT_SECONDS) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()


async def _send_email(notification: AlertNotification) -> None:
    await asyncio.to_thread(_send_email_sync, notification)


def _send_email_sync(notification: AlertNotification) -> None:
    message = EmailMessage()
    message["Subject"] = _subject(notification)
    message["From"] = settings.ALERT_EMAIL_FROM
    message["To"] = ", ".join(_email_recipients())
    message.set_content(_body(notification))

    smtp_cls = smtplib.SMTP_SSL if settings.ALERT_EMAIL_USE_SSL else smtplib.SMTP
    with smtp_cls(
        settings.ALERT_EMAIL_HOST,
        settings.ALERT_EMAIL_PORT,
        timeout=settings.ALERT_NOTIFICATION_TIMEOUT_SECONDS,
    ) as smtp:
        if settings.ALERT_EMAIL_STARTTLS and not settings.ALERT_EMAIL_USE_SSL:
            smtp.starttls()
        if settings.ALERT_EMAIL_USERNAME:
            smtp.login(settings.ALERT_EMAIL_USERNAME, settings.ALERT_EMAIL_PASSWORD)
        smtp.send_message(message)
