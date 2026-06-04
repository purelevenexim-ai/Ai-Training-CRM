"""
Phase 3 — Timeline Service

Builds a unified customer timeline merging:
- Communication events (emails, WhatsApp)
- Shopify orders
- Journey enrollment events
- CRM notes / manual events
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from app.storage import get_connection

logger = logging.getLogger(__name__)


def get_customer_timeline(email: str, limit: int = 100) -> list[dict]:
    """
    Returns unified timeline events sorted newest-first.
    Each event: {type, ts, title, subtitle, channel, icon, color, metadata}
    """
    email = email.lower().strip()
    events: list[dict] = []

    with get_connection() as conn:
        # Communication events
        rows = conn.execute(
            """
            SELECT event_type, channel, template_name, subject, message_preview, source_type, source_id, created_at
            FROM communication_events
            WHERE customer_email = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (email, limit),
        ).fetchall()
        for r in rows:
            et = r["event_type"]
            icon, color = _event_icon(et)
            events.append({
                "type": "communication",
                "event_type": et,
                "ts": r["created_at"],
                "title": _event_title(et, r["template_name"] or r["subject"]),
                "subtitle": r["message_preview"] or r["subject"] or "",
                "channel": r["channel"],
                "source_type": r["source_type"],
                "source_id": r["source_id"],
                "icon": icon,
                "color": color,
            })

        # Shopify orders
        order_rows = conn.execute(
            """
            SELECT order_name, total_price, financial_status, fulfillment_status,
                   line_items_json, created_at_shopify
            FROM shopify_orders
            WHERE customer_email = ?
            ORDER BY created_at_shopify DESC
            LIMIT ?
            """,
            (email, limit),
        ).fetchall()
        for r in order_rows:
            items = json.loads(r["line_items_json"] or "[]")
            items_str = ", ".join(i.get("title", "") for i in items[:2])
            if len(items) > 2:
                items_str += f" +{len(items)-2} more"
            events.append({
                "type": "order",
                "event_type": "ORDER",
                "ts": r["created_at_shopify"] or "",
                "title": f"Order {r['order_name']} — ₹{r['total_price']:,.0f}",
                "subtitle": items_str,
                "channel": "shopify",
                "financial_status": r["financial_status"],
                "fulfillment_status": r["fulfillment_status"],
                "icon": "🛒",
                "color": "#059669",
            })

        # Journey enrollments
        exec_rows = conn.execute(
            """
            SELECT je.journey_id, je.status, je.triggered_at, je.completed_at, j.name as journey_name
            FROM journey_executions je
            LEFT JOIN journeys j ON j.id = je.journey_id
            WHERE je.customer_email = ?
            ORDER BY je.triggered_at DESC
            LIMIT ?
            """,
            (email, limit),
        ).fetchall()
        for r in exec_rows:
            events.append({
                "type": "journey",
                "event_type": "JOURNEY_ENROLLED",
                "ts": r["triggered_at"] or "",
                "title": f"Enrolled in '{r['journey_name'] or r['journey_id']}'",
                "subtitle": f"Status: {r['status']}",
                "channel": "system",
                "icon": "🗺️",
                "color": "#7c3aed",
            })
            if r["completed_at"]:
                events.append({
                    "type": "journey",
                    "event_type": "JOURNEY_COMPLETED",
                    "ts": r["completed_at"],
                    "title": f"Completed '{r['journey_name'] or r['journey_id']}'",
                    "subtitle": "",
                    "channel": "system",
                    "icon": "✅",
                    "color": "#059669",
                })

    # Sort by ts descending
    events.sort(key=lambda e: e["ts"] or "", reverse=True)
    return events[:limit]


def _event_icon(event_type: str) -> tuple[str, str]:
    return {
        "EMAIL_SENT": ("📤", "#3b82f6"),
        "EMAIL_OPENED": ("📨", "#10b981"),
        "EMAIL_CLICKED": ("🖱️", "#8b5cf6"),
        "EMAIL_BOUNCED": ("❌", "#ef4444"),
        "EMAIL_UNSUBSCRIBED": ("🚫", "#ef4444"),
        "WA_SENT": ("💬", "#25d366"),
        "WA_DELIVERED": ("✅", "#22c55e"),
        "WA_READ": ("👁️", "#10b981"),
        "WA_REPLIED": ("↩️", "#0ea5e9"),
        "WA_FAILED": ("❗", "#ef4444"),
        "UNSUBSCRIBED": ("🚫", "#ef4444"),
    }.get(event_type, ("📌", "#6b7280"))


def _event_title(event_type: str, template_name: str | None) -> str:
    label = {
        "EMAIL_SENT": "Email Sent",
        "EMAIL_OPENED": "Email Opened",
        "EMAIL_CLICKED": "Email Clicked",
        "EMAIL_BOUNCED": "Email Bounced",
        "EMAIL_UNSUBSCRIBED": "Unsubscribed",
        "WA_SENT": "WhatsApp Sent",
        "WA_DELIVERED": "WhatsApp Delivered",
        "WA_READ": "WhatsApp Read",
        "WA_REPLIED": "WhatsApp Reply",
        "WA_FAILED": "WhatsApp Failed",
    }.get(event_type, event_type.replace("_", " ").title())
    if template_name:
        return f"{label}: {template_name}"
    return label


def get_customer_summary(email: str) -> dict:
    """Quick stats for the customer card."""
    email = email.lower().strip()
    with get_connection() as conn:
        c = conn.execute("SELECT * FROM customers WHERE email = ?", (email,)).fetchone()
        emails_sent = conn.execute(
            "SELECT COUNT(*) FROM communication_events WHERE customer_email = ? AND event_type = 'EMAIL_SENT'",
            (email,)
        ).fetchone()[0]
        wa_sent = conn.execute(
            "SELECT COUNT(*) FROM communication_events WHERE customer_email = ? AND event_type = 'WA_SENT'",
            (email,)
        ).fetchone()[0]
        orders = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(total_price),0) FROM shopify_orders WHERE customer_email = ?",
            (email,)
        ).fetchone()
    return {
        "customer": dict(c) if c else None,
        "emails_sent": emails_sent,
        "wa_messages_sent": wa_sent,
        "shopify_orders": orders[0],
        "shopify_total_spent": orders[1],
    }
