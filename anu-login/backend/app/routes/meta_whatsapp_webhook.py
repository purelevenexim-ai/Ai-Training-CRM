from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from app.config import settings
from app.review_journey_engine import record_review_event
from app.storage import get_db_connection

router = APIRouter()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_phone(raw: str | None) -> str:
    if not raw:
        return ""
    return "".join(c for c in raw if c.isdigit())


def _is_review_stage(stage: str | None) -> bool:
    return (stage or "") in {
        "review_pure_day15",
        "review_thanks_day18",
        "crosssell_day18",
        "replenishment_day45",
        "vip_day75",
    }


@router.get("/webhooks/meta/whatsapp", include_in_schema=False)
def verify_webhook(
    hub_mode: str = Query(default="", alias="hub.mode"),
    hub_verify_token: str = Query(default="", alias="hub.verify_token"),
    hub_challenge: str = Query(default="", alias="hub.challenge"),
) -> Any:
    expected = settings.meta_webhook_verify_token
    if expected and hub_mode == "subscribe" and hub_verify_token == expected:
        return int(hub_challenge) if hub_challenge.isdigit() else hub_challenge
    raise HTTPException(status_code=403, detail="Webhook verify token mismatch")


@router.post("/webhooks/meta/whatsapp", include_in_schema=False)
async def receive_webhook(request: Request) -> dict[str, Any]:
    payload = await request.json()
    now = _now_iso()
    status_events = 0

    with get_db_connection() as conn:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                statuses = value.get("statuses", [])
                for status in statuses:
                    status_events += 1
                    message_id = str(status.get("id", ""))
                    recipient = _normalize_phone(status.get("recipient_id"))
                    state = str(status.get("status", "unknown"))

                    errors = status.get("errors", []) or []
                    first_error = errors[0] if errors else {}
                    error_code = str(first_error.get("code", "")) if first_error else ""
                    error_title = str(first_error.get("title", "")) if first_error else ""
                    error_detail = str(first_error.get("message", "")) if first_error else ""

                    # Persist raw status event.
                    conn.execute(
                        """
                        INSERT INTO whatsapp_message_status_events
                          (id, message_id, recipient_phone, status, template_name,
                           error_code, error_title, error_detail, raw_payload_json, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid.uuid4()),
                            message_id,
                            recipient,
                            state,
                            None,
                            error_code or None,
                            error_title or None,
                            error_detail or None,
                            json.dumps(status, ensure_ascii=True),
                            now,
                        ),
                    )

                    # Keep journey_messages status in sync if this message exists.
                    conn.execute(
                        """
                        UPDATE journey_messages
                        SET delivery_status = ?
                        WHERE wabis_message_id = ?
                        """,
                        (state, message_id),
                    )

                    # Review Journey automation: map Meta status signals to events.
                    # Meta sends status="read" when user opens the WhatsApp message.
                    msg_row = conn.execute(
                        """
                        SELECT customer_id, journey_stage
                        FROM journey_messages
                        WHERE wabis_message_id = ?
                        ORDER BY sent_at DESC
                        LIMIT 1
                        """,
                        (message_id,),
                    ).fetchone()
                    if msg_row:
                        customer_id = str(msg_row["customer_id"])
                        journey_stage = str(msg_row["journey_stage"] or "")
                        if _is_review_stage(journey_stage):
                            if state == "read":
                                record_review_event(
                                    conn=conn,
                                    customer_id=customer_id,
                                    event_type="message_opened",
                                    stage=journey_stage,
                                    channel="whatsapp",
                                    metadata={"meta_status": state, "message_id": message_id},
                                )
                            elif state == "delivered":
                                record_review_event(
                                    conn=conn,
                                    customer_id=customer_id,
                                    event_type="message_delivered",
                                    stage=journey_stage,
                                    channel="whatsapp",
                                    metadata={"meta_status": state, "message_id": message_id},
                                )
                            elif state == "failed":
                                record_review_event(
                                    conn=conn,
                                    customer_id=customer_id,
                                    event_type="message_failed",
                                    stage=journey_stage,
                                    channel="whatsapp",
                                    metadata={
                                        "meta_status": state,
                                        "message_id": message_id,
                                        "error_code": error_code,
                                        "error_title": error_title,
                                    },
                                )

                    # Open a 24h AI session when template is delivered
                    if state == "delivered" and recipient:
                        try:
                            from app.routes.ai_dispatch import open_session, OpenSessionRequest
                            _session_req = OpenSessionRequest(
                                customer_phone=recipient,
                                shop_domain="rwxtic-gz.myshopify.com",
                                trigger_template="delivery_webhook",
                            )
                            open_session(_session_req)
                        except Exception as _sess_err:
                            import logging as _log
                            _log.getLogger(__name__).debug("24h session open skipped: %s", _sess_err)

    return {"status": "ok", "status_events": status_events}


@router.get("/tracking/meta-status/by-phone")
def get_status_by_phone(phone: str, limit: int = 100) -> dict[str, Any]:
    normalized = _normalize_phone(phone)
    capped = max(1, min(limit, 500))

    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT message_id, recipient_phone, status, error_code, error_title, error_detail, created_at
            FROM whatsapp_message_status_events
            WHERE recipient_phone = ? OR recipient_phone = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (phone, normalized, capped),
        ).fetchall()

    items = [dict(r) for r in rows]
    by_status: dict[str, int] = {}
    for item in items:
        by_status[item["status"]] = by_status.get(item["status"], 0) + 1

    return {
        "phone": normalized or phone,
        "count": len(items),
        "by_status": by_status,
        "events": items,
    }


@router.get("/tracking/meta-status/by-message/{message_id}")
def get_status_by_message(message_id: str) -> dict[str, Any]:
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT message_id, recipient_phone, status, error_code, error_title, error_detail, created_at
            FROM whatsapp_message_status_events
            WHERE message_id = ?
            ORDER BY created_at DESC
            """,
            (message_id,),
        ).fetchall()

    return {"message_id": message_id, "events": [dict(r) for r in rows]}


@router.post("/webhooks/meta/replay-read-events")
def replay_read_events(token: str = Query(default="")) -> dict[str, Any]:
    """
    Protected endpoint: replay historical Meta "read" status events from whatsapp_message_status_events
    to backfill opened_at timestamps on journey_messages for review journey stages.

    Security: Requires admin_secret as query param or calls will be rejected.
    Use: /api/webhooks/meta/replay-read-events?token=<ANU_LOGIN_ADMIN_SECRET>

    Returns:
      - total_read_events: count of all "read" events in status log
      - processed: count successfully backfilled with opened_at
      - skipped: count without matching journey_message or non-review stage
      - errors: count that encountered DB errors
    """
    if not settings.admin_secret or token != settings.admin_secret:
        raise HTTPException(status_code=403, detail="Unauthorized: invalid token")

    processed = 0
    skipped = 0
    errors = 0

    with get_db_connection() as conn:
        # Get all read status events (most recent first)
        read_events = conn.execute(
            """
            SELECT id, message_id, recipient_phone, created_at
            FROM whatsapp_message_status_events
            WHERE status = 'read'
            ORDER BY created_at DESC
            """
        ).fetchall()

        total_read = len(read_events)

        for event in read_events:
            try:
                message_id = event["message_id"]
                event_ts = event["created_at"]

                # Find journey_message for this Meta message_id
                msg_row = conn.execute(
                    """
                    SELECT id, customer_id, journey_stage, opened_at
                    FROM journey_messages
                    WHERE wabis_message_id = ?
                    ORDER BY sent_at DESC
                    LIMIT 1
                    """,
                    (message_id,),
                ).fetchone()

                if not msg_row:
                    # No matching message record — skip silently
                    skipped += 1
                    continue

                # Check if it's a review journey stage
                stage = str(msg_row["journey_stage"] or "")
                if not _is_review_stage(stage):
                    # Not a review stage — skip
                    skipped += 1
                    continue

                # Check if already has opened_at (idempotent)
                if msg_row["opened_at"]:
                    skipped += 1
                    continue

                # Backfill opened_at
                conn.execute(
                    """
                    UPDATE journey_messages
                    SET opened_at = ?
                    WHERE id = ?
                    """,
                    (event_ts, msg_row["id"]),
                )

                # Record the review event for engagement scoring
                customer_id = str(msg_row["customer_id"])
                record_review_event(
                    conn=conn,
                    customer_id=customer_id,
                    event_type="message_opened",
                    stage=stage,
                    channel="whatsapp",
                    metadata={
                        "meta_status": "read",
                        "message_id": message_id,
                        "source": "replay_backfill",
                    },
                )

                processed += 1

            except Exception as exc:
                errors += 1
                import logging
                logging.getLogger(__name__).error(
                    "Error replaying read event %s: %s", event["message_id"], exc
                )

    return {
        "status": "ok",
        "total_read_events": total_read,
        "processed": processed,
        "skipped": skipped,
        "errors": errors,
        "message": f"Backfilled {processed} opened_at timestamps for review journey messages",
    }
