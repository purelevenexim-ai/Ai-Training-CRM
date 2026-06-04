"""
Basil Commerce OS — Phase 5
journey_engine.py

Shared core used by both real-time webhooks (Delhivery, Shopify) and the
daily cron orchestrator.  All message-send decisions funnel through here so
suppression, logging, and engagement scoring are never duplicated.

Public API:
  should_send(customer, stage) → bool
  send_journey_message(conn, customer, stage, dry_run=False) → SendResult
  record_delivery_event(conn, customer_id, event_type, points, meta) → None
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app import wabis_client
from app.whatsapp_templates import build_message_vars

logger = logging.getLogger(__name__)


# ─── Result ──────────────────────────────────────────────────────────────────

@dataclass
class SendResult:
    customer_id:   str
    phone:         str
    template_name: str
    stage:         str
    status:        str   # sent | suppressed | dry_run | error
    message_id:    str = ""
    error:         str = ""
    points_awarded: float = 0.5  # delivered confirmation points


# ─── Suppression guard ────────────────────────────────────────────────────────

def should_send(customer: dict[str, Any], stage: str) -> tuple[bool, str]:
    """
    Returns (True, "") when a message may be sent.
    Returns (False, reason) when suppressed.

    Checks (in order):
      1. Hard unsubscribe / do_not_message flag
      2. Subscription status
      3. Stage already sent (idempotency)
      4. Dormant customers only get transactional messages
    """
    if customer.get("do_not_message"):
        return False, "do_not_message flag set"

    sub = customer.get("whatsapp_subscription_status", "subscribed")
    if sub == "unsubscribed":
        return False, "unsubscribed"

    # Idempotency: skip if this stage was already sent
    sent_flag = _stage_sent_flag(stage)
    if sent_flag and customer.get(sent_flag):
        return False, f"already_sent ({sent_flag})"

    # Non-responsive / dormant customers skip marketing stages
    marketing_stages = {"review", "upsell", "corporate", "loyalty", "rfm", "seasonal",
                        "day15", "day30", "day60", "day75", "day95"}
    is_responsive = bool(customer.get("is_responsive"))
    segment = customer.get("customer_segment", "low")

    if stage in marketing_stages:
        if segment == "dormant" and stage not in ("rfm", "day95"):
            return False, "dormant: skip non-rfm marketing"
        if not is_responsive and stage in ("review", "upsell", "loyalty",
                                           "day15", "day30", "day75"):
            return False, "not_responsive"

    return True, ""


def _stage_sent_flag(stage: str) -> str | None:
    return {
        "order_confirmed": "day1_sent", "day1": "day1_sent",
        "in_transit":      "day2_sent", "day2": "day2_sent",
        "delivered":       "day5_sent", "day5": "day5_sent",
        "review":          "day15_sent", "day15": "day15_sent",
        "upsell":          "day30_sent", "day30": "day30_sent",
        "corporate":       "day60_sent", "day60": "day60_sent",
        "loyalty":         "day75_sent", "day75": "day75_sent",
        "rfm":             "day95_sent", "day95": "day95_sent",
    }.get(stage)


def _stage_sent_cols(stage: str) -> tuple[str, str] | None:
    mapping = {
        "order_confirmed": ("day1_sent", "day1_sent_at"),
        "day1":            ("day1_sent", "day1_sent_at"),
        "in_transit":      ("day2_sent", "day2_sent_at"),
        "day2":            ("day2_sent", "day2_sent_at"),
        "delivered":       ("day5_sent", "day5_sent_at"),
        "day5":            ("day5_sent", "day5_sent_at"),
        "review":          ("day15_sent", "day15_sent_at"),
        "day15":           ("day15_sent", "day15_sent_at"),
        "upsell":          ("day30_sent", "day30_sent_at"),
        "day30":           ("day30_sent", "day30_sent_at"),
        "corporate":       ("day60_sent", "day60_sent_at"),
        "day60":           ("day60_sent", "day60_sent_at"),
        "loyalty":         ("day75_sent", "day75_sent_at"),
        "day75":           ("day75_sent", "day75_sent_at"),
        "rfm":             ("day95_sent", "day95_sent_at"),
        "day95":           ("day95_sent", "day95_sent_at"),
    }
    return mapping.get(stage)


# ─── Core send ────────────────────────────────────────────────────────────────

def send_journey_message(
    conn: Any,
    customer: dict[str, Any],
    stage: str,
    dry_run: bool = False,
) -> SendResult:
    """
    Build, send, and log a journey message for a customer at a given stage.

    - Checks suppression first (idempotent)
    - Builds template vars from whatsapp_templates.build_message_vars
    - Calls wabis_client.send_template_message (or stubs if dry_run)
    - Writes to journey_messages
    - Sets dayX_sent=1 flag on journey_customers
    - Awards 0.5 engagement points for delivery confirmation

    Args:
        conn:     Open SQLite connection (caller manages transaction)
        customer: journey_customers row as dict
        stage:    Journey stage key (e.g. "delivered", "review", "upsell")
        dry_run:  If True, build vars but skip actual Wabis send

    Returns:
        SendResult describing outcome
    """
    customer_id = customer["id"]
    phone       = customer["phone"]

    # ── Suppression check ─────────────────────────────────────────────────────
    ok, reason = should_send(customer, stage)
    if not ok:
        logger.debug("Suppressed %s at %s: %s", customer_id, stage, reason)
        return SendResult(customer_id, phone, "", stage, "suppressed", error=reason)

    # ── Build message vars ────────────────────────────────────────────────────
    try:
        template_name, body_params, button_params = build_message_vars(stage, customer)
    except Exception as exc:
        logger.exception("Failed to build vars for %s at %s", customer_id, stage)
        return SendResult(customer_id, phone, "", stage, "error", error=str(exc))

    if dry_run:
        return SendResult(
            customer_id, phone, template_name, stage, "dry_run",
            message_id="dry_run",
        )

    # ── Send via Wabis ────────────────────────────────────────────────────────
    wabis_response: dict[str, Any] = {}
    message_id = ""
    try:
        wabis_response = wabis_client.send_template_message(
            phone=phone,
            template_name=template_name,
            body_params=body_params,
            button_params=button_params,
            shop_domain=customer.get("shop_domain") or "rwxtic-gz.myshopify.com",
        )
        message_id = wabis_client.extract_message_id(wabis_response) or ""
    except wabis_client.WabisError as exc:
        logger.error("Wabis send failed for %s: %s", customer_id, exc)
        return SendResult(
            customer_id, phone, template_name, stage, "error",
            message_id="", error=str(exc),
        )

    now = _now_iso()

    # ── Log journey_messages ─────────────────────────────────────────────────
    conn.execute(
        """
        INSERT INTO journey_messages
          (id, customer_id, template_name, journey_stage,
           wabis_message_id, delivery_status, variables_json, sent_at, created_at)
        VALUES (?, ?, ?, ?, ?, 'sent', ?, ?, ?)
        """,
        (
            str(uuid.uuid4()), customer_id, template_name, stage,
            message_id or None,
            json.dumps({"body": body_params}, ensure_ascii=True),
            now, now,
        ),
    )

    # ── Mark sent flag ────────────────────────────────────────────────────────
    cols = _stage_sent_cols(stage)
    if cols:
        flag_col, ts_col = cols
        conn.execute(
            f"UPDATE journey_customers SET {flag_col} = 1, {ts_col} = ?, updated_at = ? WHERE id = ?",
            (now, now, customer_id),
        )

    # ── Award delivery-confirmation engagement points (0.5) ───────────────────
    _award_points(conn, customer_id, "message_delivered", 0.5, template_name, stage, now)

    logger.info("Sent %s → %s at stage=%s mid=%s", template_name, phone, stage, message_id)
    return SendResult(
        customer_id, phone, template_name, stage, "sent",
        message_id=message_id,
        points_awarded=0.5,
    )


# ─── Engagement helpers ──────────────────────────────────────────────────────

def _award_points(
    conn: Any,
    customer_id: str,
    event_type: str,
    points: float,
    template_name: str,
    stage: str,
    now: str,
) -> None:
    conn.execute(
        """
        INSERT INTO journey_engagement_events
          (id, customer_id, event_type, template_name, journey_stage,
           points_awarded, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, '{}', ?)
        """,
        (str(uuid.uuid4()), customer_id, event_type, template_name, stage, points, now),
    )
    conn.execute(
        """
        UPDATE journey_customers
        SET engagement_score = engagement_score + ?,
            last_engagement_at = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (points, now, now, customer_id),
    )


def record_engagement(
    conn: Any,
    customer_id: str,
    event_type: str,
    points: float,
    template_name: str = "",
    stage: str = "",
    meta: dict[str, Any] | None = None,
) -> None:
    """
    Public helper: log an engagement event + update score + set is_responsive if warranted.
    Called from whatsapp_tracking.py and shopify_webhook.py.
    """
    now = _now_iso()
    _award_points(conn, customer_id, event_type, points, template_name, stage, now)
    if event_type in ("click", "reply", "call", "purchase"):
        conn.execute(
            "UPDATE journey_customers SET is_responsive = 1, updated_at = ? WHERE id = ?",
            (now, customer_id),
        )
    if meta:
        conn.execute(
            """
            UPDATE journey_engagement_events
            SET metadata_json = ?
            WHERE customer_id = ? AND event_type = ? AND created_at = ?
            """,
            (json.dumps(meta, ensure_ascii=True), customer_id, event_type, now),
        )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
