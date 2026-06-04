"""
Phase 2 — Campaign Service

Manages one-off broadcast campaigns that target contact lists or all customers.
Supports Email, WhatsApp, and multi-channel campaigns.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.storage import get_connection
from app.services.audience_service import get_list, get_list_members, render_template, get_template
from app.services.email_service import send_email
from app.services.event_tracking_service import log_event

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# ─── CRUD ────────────────────────────────────────────────────────────────────

def create_campaign(
    name: str,
    *,
    description: str = "",
    type: str = "email",
    audience_type: str = "all",
    list_id: str | None = None,
    segment_filter: dict | None = None,
    template_id: str | None = None,
    schedule_type: str = "send_now",
    scheduled_at: str | None = None,
    recurring_pattern: str | None = None,
    created_by: str | None = None,
) -> dict:
    now = _now()
    cid = _new_id()
    initial_status = "scheduled" if (schedule_type == "schedule_at" and scheduled_at) else "draft"
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO campaigns
                (id, name, description, type, audience_type, list_id, segment_filter_json,
                 template_id, schedule_type, scheduled_at, recurring_pattern, status,
                 created_by, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                cid, name, description, type, audience_type, list_id,
                json.dumps(segment_filter or {}),
                template_id, schedule_type, scheduled_at, recurring_pattern,
                initial_status, created_by, now, now,
            ),
        )
    return get_campaign(cid)


def get_campaign(cid: str) -> dict | None:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (cid,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["segment_filter"] = json.loads(d.pop("segment_filter_json", "{}"))
    return d


def list_campaigns(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    with get_connection() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM campaigns WHERE status = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (status, limit, offset),
            ).fetchall()
            total = conn.execute(
                "SELECT COUNT(*) FROM campaigns WHERE status = ?", (status,)
            ).fetchone()[0]
        else:
            rows = conn.execute(
                "SELECT * FROM campaigns ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            total = conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
    items = []
    for r in rows:
        d = dict(r)
        d["segment_filter"] = json.loads(d.pop("segment_filter_json", "{}"))
        items.append(d)
    return items, total


def update_campaign(cid: str, updates: dict) -> dict | None:
    current = get_campaign(cid)
    if not current:
        return None

    allowed = {
        "name", "description", "type", "audience_type", "list_id",
        "template_id", "schedule_type", "scheduled_at", "recurring_pattern",
    }
    clean = {k: v for k, v in updates.items() if k in allowed}
    if "segment_filter" in updates:
        clean["segment_filter_json"] = json.dumps(updates["segment_filter"])

    # Keep schedule state in sync while still in pre-send lifecycle.
    if current.get("status") in ("draft", "scheduled") and (
        "schedule_type" in clean or "scheduled_at" in clean
    ):
        next_schedule_type = clean.get("schedule_type", current.get("schedule_type"))
        next_scheduled_at = clean.get("scheduled_at", current.get("scheduled_at"))
        clean["status"] = "scheduled" if (next_schedule_type == "schedule_at" and next_scheduled_at) else "draft"

    if not clean:
        return current
    clean["updated_at"] = _now()
    sets = ", ".join(f"{k} = ?" for k in clean)
    vals = list(clean.values()) + [cid]
    with get_connection() as conn:
        conn.execute(f"UPDATE campaigns SET {sets} WHERE id = ?", vals)
    return get_campaign(cid)


def delete_campaign(cid: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute("DELETE FROM campaigns WHERE id = ? AND status = 'draft'", (cid,))
    return cur.rowcount > 0


# ─── Audience Resolution ─────────────────────────────────────────────────────

def _resolve_audience(campaign: dict) -> list[dict]:
    """Return list of {email, name, phone, id} dicts for the campaign audience."""
    aud = campaign.get("audience_type", "all")
    with get_connection() as conn:
        if aud == "list" and campaign.get("list_id"):
            rows = conn.execute(
                """
                SELECT c.id, c.email, c.name, c.phone
                FROM contact_list_members clm
                JOIN customers c ON c.id = clm.customer_id
                WHERE clm.list_id = ? AND c.deleted_at IS NULL AND COALESCE(c.pause_campaigns, 0) = 0
                """,
                (campaign["list_id"],),
            ).fetchall()
        else:
            channel = campaign.get("type", "email")
            if channel == "whatsapp":
                rows = conn.execute(
                    "SELECT id, email, name, phone FROM customers WHERE deleted_at IS NULL AND whatsapp_opted_in = 1 AND COALESCE(pause_campaigns, 0) = 0"
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, email, name, phone FROM customers WHERE deleted_at IS NULL AND email_opted_in = 1 AND COALESCE(pause_campaigns, 0) = 0"
                ).fetchall()
    return [dict(r) for r in rows]


# ─── Preview ─────────────────────────────────────────────────────────────────

def preview_campaign(cid: str, sample_size: int = 5) -> list[dict]:
    campaign = get_campaign(cid)
    if not campaign:
        return []
    if not campaign.get("template_id"):
        return []
    template = get_template(campaign["template_id"])
    if not template:
        return []
    audience = _resolve_audience(campaign)[:sample_size]
    previews = []
    for cust in audience:
        variables = {
            "first_name": (cust.get("name") or "").split()[0] if cust.get("name") else "Customer",
            "name": cust.get("name") or "Customer",
            "email": cust.get("email", ""),
        }
        rendered = render_template(template, campaign.get("type", "email"), variables)
        previews.append({
            "email": cust["email"],
            "name": cust.get("name"),
            "subject": rendered.get("email_subject"),
            "preview": (rendered.get("email_html") or "")[:200],
            "whatsapp_body": rendered.get("whatsapp_body"),
        })
    return previews


# ─── Send ─────────────────────────────────────────────────────────────────────

def send_campaign_now(cid: str, dry_run: bool = False) -> dict:
    campaign = get_campaign(cid)
    if not campaign:
        return {"error": "campaign not found"}
    if campaign["status"] not in ("draft", "scheduled"):
        return {"error": f"cannot send campaign in status '{campaign['status']}'"}

    template = get_template(campaign["template_id"]) if campaign.get("template_id") else None
    audience = _resolve_audience(campaign)
    now = _now()

    if dry_run:
        return {
            "dry_run": True,
            "campaign_id": cid,
            "recipients": len(audience),
            "template": template.get("name") if template else None,
        }

    # Mark as sending
    with get_connection() as conn:
        conn.execute(
            "UPDATE campaigns SET status = 'sending', started_at = ?, total_recipients = ?, updated_at = ? WHERE id = ?",
            (now, len(audience), now, cid),
        )

    sent = 0
    errors = 0
    channel = campaign.get("type", "email")

    for cust in audience:
        send_id = _new_id()
        variables = {
            "first_name": (cust.get("name") or "").split()[0] if cust.get("name") else "Customer",
            "name": cust.get("name") or "Customer",
            "email": cust.get("email", ""),
        }
        rendered = render_template(template, channel, variables) if template else {}
        subject = rendered.get("email_subject") or campaign.get("name", "")
        body = rendered.get("email_html") or rendered.get("email_text") or ""
        wa_body = rendered.get("whatsapp_body") or ""

        error_reason = None
        message_id = None
        send_status = "sent"

        try:
            if channel in ("email", "multichannel"):
                result = send_email(
                    to_email=cust["email"],
                    subject=subject,
                    html_body=body,
                    text_body=rendered.get("email_text") or "",
                )
                message_id = result.get("message_id") if isinstance(result, dict) else None
            if channel in ("whatsapp", "multichannel") and cust.get("phone"):
                try:
                    from app import wabis_client
                    wabis_client.send_template_message(
                        cust["phone"],
                        wa_body,
                        shop_domain=cust.get("shop_domain") or "rwxtic-gz.myshopify.com",
                    )
                except Exception as e:
                    logger.warning("WhatsApp send failed for %s: %s", cust["email"], e)
        except Exception as exc:
            error_reason = str(exc)
            send_status = "failed"
            errors += 1
        else:
            sent += 1

        # Record send
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO campaign_sends
                    (id, campaign_id, customer_id, customer_email, channel, template_id,
                     subject_rendered, body_rendered, status, sent_at, error_reason, message_id, created_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    send_id, cid, cust.get("id"), cust["email"], channel,
                    campaign.get("template_id"), subject, body[:2000],
                    send_status, _now() if send_status == "sent" else None,
                    error_reason, message_id, now,
                ),
            )

        # Log communication event
        try:
            log_event(
                customer_email=cust["email"],
                event_type="EMAIL_SENT" if channel in ("email", "multichannel") else "WA_SENT",
                channel="email" if channel == "email" else "whatsapp",
                source_type="campaign",
                source_id=cid,
                template_id=campaign.get("template_id"),
                template_name=template.get("name") if template else None,
                subject=subject,
                message_preview=body[:200] if channel != "whatsapp" else wa_body[:200],
            )
        except Exception as e:
            logger.warning("Event log failed: %s", e)

    # Mark completed
    with get_connection() as conn:
        conn.execute(
            "UPDATE campaigns SET status = 'completed', completed_at = ?, sent_count = ?, error_count = ?, updated_at = ? WHERE id = ?",
            (_now(), sent, errors, _now(), cid),
        )

    return {
        "campaign_id": cid,
        "total_recipients": len(audience),
        "sent": sent,
        "errors": errors,
        "status": "completed",
    }


def get_campaign_stats(cid: str) -> dict:
    campaign = get_campaign(cid)
    if not campaign:
        return {}
    with get_connection() as conn:
        agg = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END) AS sent,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed,
                SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) AS opened,
                SUM(CASE WHEN clicked_at IS NOT NULL THEN 1 ELSE 0 END) AS clicked
            FROM campaign_sends WHERE campaign_id = ?
            """,
            (cid,),
        ).fetchone()
    total = agg["total"] or 0
    s = agg["sent"] or 0
    return {
        "campaign_id": cid,
        "campaign_name": campaign["name"],
        "status": campaign["status"],
        "total_recipients": total,
        "sent": s,
        "failed": agg["failed"] or 0,
        "opened": agg["opened"] or 0,
        "clicked": agg["clicked"] or 0,
        "open_rate": round((agg["opened"] or 0) / s * 100, 1) if s else 0,
        "click_rate": round((agg["clicked"] or 0) / s * 100, 1) if s else 0,
    }


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def process_due_campaigns(limit: int = 25) -> dict[str, Any]:
    """Send campaigns marked scheduled once their scheduled_at is due."""
    now_dt = datetime.now(timezone.utc)
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, scheduled_at
            FROM campaigns
            WHERE status = 'scheduled'
            ORDER BY scheduled_at ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    due_ids: list[str] = []
    for row in rows:
        scheduled_at = _parse_iso_datetime(row["scheduled_at"])
        if scheduled_at and scheduled_at <= now_dt:
            due_ids.append(row["id"])

    processed = 0
    sent = 0
    failed = 0
    errors: list[dict[str, str]] = []

    for campaign_id in due_ids:
        processed += 1
        try:
            result = send_campaign_now(campaign_id, dry_run=False)
            if result.get("error"):
                failed += 1
                errors.append({"campaign_id": campaign_id, "error": str(result["error"])})
            else:
                sent += 1
        except Exception as exc:
            failed += 1
            errors.append({"campaign_id": campaign_id, "error": str(exc)})
            logger.exception("Scheduled send failed for campaign %s", campaign_id)

    return {
        "checked": len(rows),
        "due": len(due_ids),
        "processed": processed,
        "sent": sent,
        "failed": failed,
        "errors": errors,
    }
