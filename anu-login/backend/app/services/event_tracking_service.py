"""
Phase 3 — Event Tracking Service

Unified communication event log for Email + WhatsApp.
Every send, open, click, bounce, and unsubscribe is written here.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.storage import get_connection

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


EVENT_TYPES = {
    # Email
    "EMAIL_SENT", "EMAIL_OPENED", "EMAIL_CLICKED", "EMAIL_BOUNCED", "EMAIL_UNSUBSCRIBED",
    # WhatsApp
    "WA_SENT", "WA_DELIVERED", "WA_READ", "WA_REPLIED", "WA_FAILED",
    # Generic
    "UNSUBSCRIBED", "RESUBSCRIBED",
}


def log_event(
    customer_email: str,
    event_type: str,
    channel: str = "email",
    source_type: str = "journey",
    source_id: str | None = None,
    template_id: str | None = None,
    template_name: str | None = None,
    subject: str | None = None,
    message_preview: str | None = None,
    customer_id: str | None = None,
    metadata: dict | None = None,
) -> str:
    """Log a communication event. Returns the event id."""
    eid = str(uuid.uuid4())
    now = _now()
    with get_connection() as conn:
        if not customer_id:
            row = conn.execute(
                "SELECT id FROM customers WHERE email = ?", (customer_email.lower().strip(),)
            ).fetchone()
            if row:
                customer_id = row["id"]

        conn.execute(
            """
            INSERT INTO communication_events
                (id, customer_id, customer_email, source_type, source_id,
                 event_type, channel, template_id, template_name,
                 subject, message_preview, metadata_json, created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                eid, customer_id, customer_email.lower().strip(),
                source_type, source_id, event_type, channel,
                template_id, template_name, subject,
                (message_preview or "")[:500],
                json.dumps(metadata or {}),
                now,
            ),
        )
    return eid


def get_customer_events(
    email: str,
    limit: int = 50,
    offset: int = 0,
    channel: str | None = None,
    event_type: str | None = None,
) -> tuple[list[dict], int]:
    email = email.lower().strip()
    clauses = ["customer_email = ?"]
    params: list[Any] = [email]
    if channel:
        clauses.append("channel = ?")
        params.append(channel)
    if event_type:
        clauses.append("event_type = ?")
        params.append(event_type)
    where = " AND ".join(clauses)
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM communication_events WHERE {where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        total = conn.execute(
            f"SELECT COUNT(*) FROM communication_events WHERE {where}", params
        ).fetchone()[0]
    items = []
    for r in rows:
        d = dict(r)
        d["metadata"] = json.loads(d.pop("metadata_json", "{}"))
        items.append(d)
    return items, total


def get_overview_stats(days: int = 30) -> dict:
    from datetime import timedelta
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT event_type, channel, COUNT(*) as cnt
            FROM communication_events
            WHERE created_at >= ?
            GROUP BY event_type, channel
            """,
            (since,),
        ).fetchall()
    stats: dict[str, Any] = {
        "days": days,
        "email": {"sent": 0, "opened": 0, "clicked": 0, "bounced": 0, "unsubscribed": 0},
        "whatsapp": {"sent": 0, "delivered": 0, "read": 0, "replied": 0, "failed": 0},
    }
    for r in rows:
        et, ch, cnt = r["event_type"], r["channel"], r["cnt"]
        if ch == "email":
            if et == "EMAIL_SENT":
                stats["email"]["sent"] += cnt
            elif et == "EMAIL_OPENED":
                stats["email"]["opened"] += cnt
            elif et == "EMAIL_CLICKED":
                stats["email"]["clicked"] += cnt
            elif et == "EMAIL_BOUNCED":
                stats["email"]["bounced"] += cnt
            elif et in ("EMAIL_UNSUBSCRIBED", "UNSUBSCRIBED"):
                stats["email"]["unsubscribed"] += cnt
        elif ch == "whatsapp":
            if et == "WA_SENT":
                stats["whatsapp"]["sent"] += cnt
            elif et == "WA_DELIVERED":
                stats["whatsapp"]["delivered"] += cnt
            elif et == "WA_READ":
                stats["whatsapp"]["read"] += cnt
            elif et == "WA_REPLIED":
                stats["whatsapp"]["replied"] += cnt
            elif et == "WA_FAILED":
                stats["whatsapp"]["failed"] += cnt

    es = stats["email"]
    ws = stats["whatsapp"]
    es["open_rate"] = round(es["opened"] / es["sent"] * 100, 1) if es["sent"] else 0
    es["click_rate"] = round(es["clicked"] / es["sent"] * 100, 1) if es["sent"] else 0
    ws["delivery_rate"] = round(ws["delivered"] / ws["sent"] * 100, 1) if ws["sent"] else 0
    ws["read_rate"] = round(ws["read"] / ws["sent"] * 100, 1) if ws["sent"] else 0
    return stats


def get_source_stats(source_type: str, source_id: str) -> dict:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT event_type, COUNT(*) as cnt
            FROM communication_events
            WHERE source_type = ? AND source_id = ?
            GROUP BY event_type
            """,
            (source_type, source_id),
        ).fetchall()
    counts = {r["event_type"]: r["cnt"] for r in rows}
    sent = counts.get("EMAIL_SENT", 0) + counts.get("WA_SENT", 0)
    opened = counts.get("EMAIL_OPENED", 0)
    clicked = counts.get("EMAIL_CLICKED", 0)
    read = counts.get("WA_READ", 0)
    return {
        "source_type": source_type,
        "source_id": source_id,
        "total_sent": sent,
        "email_sent": counts.get("EMAIL_SENT", 0),
        "email_opened": opened,
        "email_clicked": clicked,
        "email_open_rate": round(opened / counts.get("EMAIL_SENT", 1) * 100, 1) if counts.get("EMAIL_SENT") else 0,
        "email_click_rate": round(clicked / counts.get("EMAIL_SENT", 1) * 100, 1) if counts.get("EMAIL_SENT") else 0,
        "wa_sent": counts.get("WA_SENT", 0),
        "wa_delivered": counts.get("WA_DELIVERED", 0),
        "wa_read": read,
        "wa_read_rate": round(read / counts.get("WA_SENT", 1) * 100, 1) if counts.get("WA_SENT") else 0,
        "unsubscribed": counts.get("UNSUBSCRIBED", 0) + counts.get("EMAIL_UNSUBSCRIBED", 0),
    }
