"""
Alert sender for PureLeven — notifies owner via WhatsApp (Meta API).

Used for:
  - Bulk inquiry received (critical, immediate)
  - Customer complaint (high, immediate)
  - Delivery failure spike (medium)
  - Daily health digest (low)
  - WABA quality risk (critical)

Uses owner's own WhatsApp number as destination.
Falls back to logging only if Meta API not configured.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

try:
    import httpx
except Exception:  # pragma: no cover - optional in local/dev shells
    httpx = None

from app.config import settings
from app.runtime_db import ensure_runtime_tables, get_db_connection

logger = logging.getLogger(__name__)

SEVERITY_EMOJI = {
    "critical": "🚨",
    "high": "⚠️",
    "medium": "📊",
    "info": "ℹ️",
}


def send_owner_alert(message: str, severity: str = "info", alert_type: str = "general") -> bool:
    """
    Send a WhatsApp text message to the owner's phone number.

    Uses Meta Cloud API directly (same credentials as campaign messages).
    Returns True if delivered, False otherwise.
    """
    _log_alert_to_db(alert_type, severity, message)

    if not settings.meta_phone_number_id or not settings.meta_access_token:
        logger.warning("Meta API not configured — alert not sent: %s", message[:100])
        return False

    if httpx is None:
        logger.warning("httpx is not installed — alert not sent: %s", message[:100])
        return False

    owner_phone = settings.meta_owner_phone
    if not owner_phone:
        logger.warning("META_OWNER_PHONE not set — alert not sent")
        return False

    emoji = SEVERITY_EMOJI.get(severity, "ℹ️")
    body = f"{emoji} *PureLeven Alert*\n\n{message}"

    payload = {
        "messaging_product": "whatsapp",
        "to": owner_phone,
        "type": "text",
        "text": {"body": body, "preview_url": False},
    }

    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(
                f"https://graph.facebook.com/v20.0/{settings.meta_phone_number_id}/messages",
                headers={
                    "Authorization": f"Bearer {settings.meta_access_token}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            if resp.status_code == 200:
                logger.info("Owner alert sent successfully: %s", alert_type)
                return True
            else:
                logger.error("Owner alert Meta API error %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.error("Owner alert send failed: %s", exc)

    return False


def alert_bulk_inquiry(customer_phone: str, reply_text: str) -> None:
    """Immediate alert when customer asks about bulk/wholesale."""
    msg = (
        f"*Bulk Inquiry Received* 🔥\n\n"
        f"Phone: {customer_phone}\n"
        f"Message: {reply_text[:300]}\n\n"
        f"Check WhatsApp now — this is a B2B lead."
    )
    send_owner_alert(msg, severity="critical", alert_type="bulk_inquiry")


def alert_complaint(customer_phone: str, reply_text: str) -> None:
    """Alert when customer sends a complaint."""
    msg = (
        f"*Customer Complaint* ⚠️\n\n"
        f"Phone: {customer_phone}\n"
        f"Message: {reply_text[:300]}\n\n"
        f"Campaigns paused for this customer."
    )
    send_owner_alert(msg, severity="high", alert_type="complaint")


def alert_purchase_intent(customer_phone: str, reply_text: str) -> None:
    """Alert when customer expresses strong purchase intent."""
    msg = (
        f"*Purchase Intent Detected* 🛒\n\n"
        f"Phone: {customer_phone}\n"
        f"Message: {reply_text[:200]}"
    )
    send_owner_alert(msg, severity="high", alert_type="purchase_intent")


def send_daily_health_report(stats: dict[str, Any]) -> None:
    """Send daily health digest to owner."""
    failure_rate = stats.get("failure_rate", "0%")
    msg = (
        f"*Daily WhatsApp Health Report* 📊\n\n"
        f"Messages sent (24h): {stats.get('messages_sent_24h', 0)}\n"
        f"Failed: {stats.get('messages_failed', 0)} ({failure_rate})\n"
        f"New customers: {stats.get('new_customers', 0)}\n"
        f"Unsubscribes: {stats.get('unsubscribes_24h', 0)}\n"
        f"Active 24h sessions: {stats.get('active_sessions', 0)}\n"
        f"Session conversions: {stats.get('session_conversions', 0)}\n"
    )
    if stats.get("warnings"):
        msg += "\n*Warnings:*\n"
        for w in stats["warnings"][:5]:
            msg += f"  • {w}\n"

    send_owner_alert(msg, severity="info", alert_type="daily_health")


def _log_alert_to_db(alert_type: str, severity: str, message: str) -> None:
    """Persist alert to monitoring_alerts table for audit."""
    try:
        ensure_runtime_tables()
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO monitoring_alerts (id, alert_type, severity, message, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), alert_type, severity, message[:2000],
                 datetime.now(timezone.utc).isoformat()),
            )
    except Exception as exc:
        logger.warning("Failed to log alert to DB: %s", exc)
