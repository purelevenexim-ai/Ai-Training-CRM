"""
Basil Commerce OS — Phase 5
routes/whatsapp_tracking.py

WhatsApp engagement tracking endpoints.
Wabis webhooks POST here whenever a customer interacts with a message.

Endpoints:
  POST /api/tracking/whatsapp-click        — button or link click (+5 pts)
  POST /api/tracking/whatsapp-reply        — customer replied (+7 pts, sets is_responsive)
  POST /api/tracking/whatsapp-call         — call initiated (+10 pts)
  POST /api/tracking/whatsapp-unsubscribe  — customer opted out
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.config import settings
from app.storage import get_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)

# ─── Engagement point values ──────────────────────────────────────────────────
POINTS = {
    "delivered": 0.5,
    "opened": 1.0,
    "click": 5.0,
    "reply": 7.0,
    "call": 10.0,
    "purchase": 50.0,
}

# Segment thresholds (used for recalculation on every event)
SEGMENT_THRESHOLDS = {
    "vip": 80.0,
    "responsive": 40.0,
    "low": 5.0,
    # below low → dormant
}


# ─── Models ───────────────────────────────────────────────────────────────────

class ClickPayload(BaseModel):
    customer_phone: str = Field(min_length=7, max_length=20)
    shop_domain: str = Field(min_length=1, max_length=200)
    template_name: str = ""
    button_text: str = ""
    journey_stage: str = ""
    wabis_message_id: str = ""
    metadata: dict[str, Any] = {}


class ReplyPayload(BaseModel):
    customer_phone: str = Field(min_length=7, max_length=20)
    shop_domain: str = Field(min_length=1, max_length=200)
    template_name: str = ""
    reply_text: str = ""
    journey_stage: str = ""
    wabis_message_id: str = ""
    metadata: dict[str, Any] = {}


class CallPayload(BaseModel):
    customer_phone: str = Field(min_length=7, max_length=20)
    shop_domain: str = Field(min_length=1, max_length=200)
    template_name: str = ""
    journey_stage: str = ""
    metadata: dict[str, Any] = {}


class UnsubscribePayload(BaseModel):
    customer_phone: str = Field(min_length=7, max_length=20)
    shop_domain: str = Field(min_length=1, max_length=200)
    reason: str = "customer_request"
    metadata: dict[str, Any] = {}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _resolve_customer(conn: Any, shop_domain: str, phone: str) -> dict[str, Any] | None:
    """Fetch journey_customer row by phone (normalized: digits only)."""
    normalized = "".join(c for c in phone if c.isdigit())
    row = conn.execute(
        """
        SELECT * FROM journey_customers
        WHERE shop_domain = ? AND (phone = ? OR phone = ?)
        ORDER BY created_at DESC LIMIT 1
        """,
        (shop_domain, phone, normalized),
    ).fetchone()
    return dict(row) if row else None


def _calculate_segment(score: float) -> str:
    if score >= SEGMENT_THRESHOLDS["vip"]:
        return "vip"
    if score >= SEGMENT_THRESHOLDS["responsive"]:
        return "responsive"
    if score >= SEGMENT_THRESHOLDS["low"]:
        return "low"
    return "dormant"


def _apply_engagement_event(
    conn: Any,
    customer: dict[str, Any],
    event_type: str,
    points: float,
    template_name: str,
    journey_stage: str,
    metadata: dict[str, Any],
) -> float:
    """
    Log engagement event, update customer engagement_score, segment, is_responsive,
    and per-stage engagement_status. Returns updated score.
    """
    now = _now_iso()
    event_id = str(uuid.uuid4())
    new_score = customer["engagement_score"] + points

    # Determine new segment
    new_segment = _calculate_segment(new_score)

    # is_responsive: any click, reply, or call sets it permanently
    is_responsive = customer["is_responsive"] or (event_type in ("click", "reply", "call"))

    # Update per-stage engagement status field if applicable
    stage_col = _stage_engagement_col(journey_stage)

    update_fields: dict[str, Any] = {
        "engagement_score": new_score,
        "last_engagement_at": now,
        "customer_segment": new_segment,
        "is_responsive": 1 if is_responsive else customer["is_responsive"],
        "updated_at": now,
    }
    if stage_col:
        update_fields[stage_col] = event_type

    # Build dynamic UPDATE
    set_clause = ", ".join(f"{k} = ?" for k in update_fields)
    conn.execute(
        f"UPDATE journey_customers SET {set_clause} WHERE id = ?",
        [*update_fields.values(), customer["id"]],
    )

    # Log the event
    conn.execute(
        """
        INSERT INTO journey_engagement_events
          (id, customer_id, event_type, template_name, journey_stage,
           points_awarded, metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            customer["id"],
            event_type,
            template_name or None,
            journey_stage or None,
            points,
            json.dumps(metadata, ensure_ascii=True),
            now,
        ),
    )

    return new_score


def _stage_engagement_col(journey_stage: str) -> str | None:
    """Map journey stage name to the engagement_status column."""
    mapping = {
        "day2": "day2_engagement_status",
        "delivery_begun": "day2_engagement_status",
        "day5": "day5_engagement_status",
        "delivered": "day5_engagement_status",
        "day15": "day15_engagement_status",
        "review": "day15_engagement_status",
        "day30": "day30_engagement_status",
        "upsell": "day30_engagement_status",
        "day60": "day60_engagement_status",
        "corporate": "day60_engagement_status",
    }
    return mapping.get(journey_stage)


async def _verify_wabis_signature(request: Request, x_wabis_signature: str | None) -> None:
    """
    Verify webhook authenticity using shared secret and HMAC-SHA256.
    Accepts either raw hex digest or "sha256=<hex>" format.
    """
    secret = settings.wabis_webhook_secret
    if not secret:
        logger.error('WABIS_WEBHOOK_SECRET is not configured; refusing tracking webhook requests.')
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Tracking webhook secret not configured.')

    if not x_wabis_signature:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing webhook signature.')

    raw_body = await request.body()
    provided = x_wabis_signature.strip()
    if provided.startswith('sha256='):
        provided = provided.split('=', 1)[1].strip()

    expected = hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, provided):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid webhook signature.')


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post(
    "/tracking/whatsapp-click",
    summary="Customer clicked a button or link in a WhatsApp message",
    status_code=status.HTTP_200_OK,
)
async def track_click(
    payload: ClickPayload,
    request: Request,
    x_wabis_signature: str | None = Header(default=None, alias='x-wabis-signature'),
) -> dict[str, Any]:
    await _verify_wabis_signature(request, x_wabis_signature)
    now = _now_iso()
    with get_db_connection() as conn:
        customer = _resolve_customer(conn, payload.shop_domain, payload.customer_phone)
        if not customer:
            # Create a minimal placeholder — full profile will arrive via order webhook
            return {"status": "no_customer", "message": "Customer not found; event not recorded"}

        meta = {**payload.metadata, "button_text": payload.button_text, "wabis_message_id": payload.wabis_message_id}
        new_score = _apply_engagement_event(
            conn, customer,
            event_type="click",
            points=POINTS["click"],
            template_name=payload.template_name,
            journey_stage=payload.journey_stage,
            metadata=meta,
        )

        # ── Also update the main customers table for last_engagement_at ─────────
        normalized = "".join(c for c in payload.customer_phone if c.isdigit())
        try:
            conn.execute(
                """
                UPDATE customers
                SET last_engagement_at = ?, engagement_label = 'responsive'
                WHERE (phone LIKE ? OR phone LIKE ? OR phone = ?)
                """,
                (now, f"%{normalized[-10:]}", f"%{normalized}", payload.customer_phone),
            )
        except Exception as e:
            logger.warning("Failed to update main customers table: %s", e)

    return {
        "status": "ok",
        "customer_id": customer["id"],
        "points_awarded": POINTS["click"],
        "new_score": new_score,
    }


@router.post(
    "/tracking/whatsapp-reply",
    summary="Customer replied to a WhatsApp template message",
    status_code=status.HTTP_200_OK,
)
async def track_reply(
    payload: ReplyPayload,
    request: Request,
    x_wabis_signature: str | None = Header(default=None, alias='x-wabis-signature'),
) -> dict[str, Any]:
    await _verify_wabis_signature(request, x_wabis_signature)
    with get_db_connection() as conn:
        customer = _resolve_customer(conn, payload.shop_domain, payload.customer_phone)
        if not customer:
            return {"status": "no_customer", "message": "Customer not found; event not recorded"}

        meta = {**payload.metadata, "reply_text": payload.reply_text, "wabis_message_id": payload.wabis_message_id}
        new_score = _apply_engagement_event(
            conn, customer,
            event_type="reply",
            points=POINTS["reply"],
            template_name=payload.template_name,
            journey_stage=payload.journey_stage,
            metadata=meta,
        )

        # ── Also update the main customers table for last_engagement_at ─────────
        # This is critical for the 24-hour marketing message window check
        now = _now_iso()
        normalized = "".join(c for c in payload.customer_phone if c.isdigit())
        try:
            conn.execute(
                """
                UPDATE customers
                SET last_engagement_at = ?, engagement_label = 'responsive'
                WHERE (phone LIKE ? OR phone LIKE ? OR phone = ?)
                """,
                (now, f"%{normalized[-10:]}", f"%{normalized}", payload.customer_phone),
            )
        except Exception as e:
            logger.warning("Failed to update main customers table: %s", e)

    # AI intent classification — async fire-and-forget
    ai_result: dict[str, Any] = {}
    if payload.reply_text.strip():
        try:
            from app.routes.ai_dispatch import _handle_reply as _ai_handle_reply
            from app.routes.ai_dispatch import _normalize_phone as _ai_normalize_phone
            with get_db_connection() as conn2:
                customer2 = _resolve_customer(conn2, payload.shop_domain, payload.customer_phone)
                customer_dict = dict(customer2) if customer2 else {"phone": payload.customer_phone, "name": "Customer", "id": ""}
                session = conn2.execute(
                    "SELECT * FROM conversation_sessions WHERE customer_phone = ? AND is_active = 1 ORDER BY created_at DESC LIMIT 1",
                    (_ai_normalize_phone(payload.customer_phone),),
                ).fetchone()

                class _FakeReq:
                    customer_phone = payload.customer_phone
                    shop_domain = payload.shop_domain
                    incoming_reply = payload.reply_text

                ai_result = _ai_handle_reply(conn2, _FakeReq(), customer_dict, session, _ai_normalize_phone(payload.customer_phone))
        except Exception as _ai_err:
            import logging as _log
            _log.getLogger(__name__).warning("AI intent dispatch error: %s", _ai_err)

    return {
        "status": "ok",
        "customer_id": customer["id"],
        "points_awarded": POINTS["reply"],
        "new_score": new_score,
        "is_responsive": True,
        "ai_action": ai_result.get("action"),
        "ai_intent": ai_result.get("intent"),
    }


@router.post(
    "/tracking/whatsapp-call",
    summary="Customer initiated a WhatsApp call",
    status_code=status.HTTP_200_OK,
)
async def track_call(
    payload: CallPayload,
    request: Request,
    x_wabis_signature: str | None = Header(default=None, alias='x-wabis-signature'),
) -> dict[str, Any]:
    await _verify_wabis_signature(request, x_wabis_signature)
    with get_db_connection() as conn:
        customer = _resolve_customer(conn, payload.shop_domain, payload.customer_phone)
        if not customer:
            return {"status": "no_customer", "message": "Customer not found; event not recorded"}

        meta = {**payload.metadata}
        new_score = _apply_engagement_event(
            conn, customer,
            event_type="call",
            points=POINTS["call"],
            template_name=payload.template_name,
            journey_stage=payload.journey_stage,
            metadata=meta,
        )

    return {
        "status": "ok",
        "customer_id": customer["id"],
        "points_awarded": POINTS["call"],
        "new_score": new_score,
        "is_responsive": True,
        "alert": "sales_team_notify",
    }


@router.post(
    "/tracking/whatsapp-unsubscribe",
    summary="Customer opted out of WhatsApp marketing",
    status_code=status.HTTP_200_OK,
)
async def track_unsubscribe(
    payload: UnsubscribePayload,
    request: Request,
    x_wabis_signature: str | None = Header(default=None, alias='x-wabis-signature'),
) -> dict[str, Any]:
    await _verify_wabis_signature(request, x_wabis_signature)
    now = _now_iso()
    with get_db_connection() as conn:
        customer = _resolve_customer(conn, payload.shop_domain, payload.customer_phone)
        if not customer:
            return {"status": "no_customer", "message": "Customer not found; suppression not recorded"}

        meta = {**payload.metadata, "reason": payload.reason}
        conn.execute(
            """
            UPDATE journey_customers SET
                whatsapp_subscription_status = 'unsubscribed',
                do_not_message = 1,
                updated_at = ?
            WHERE id = ?
            """,
            (now, customer["id"]),
        )
        # Log as a zero-point event for audit trail
        conn.execute(
            """
            INSERT INTO journey_engagement_events
              (id, customer_id, event_type, template_name, journey_stage,
               points_awarded, metadata_json, created_at)
            VALUES (?, ?, 'unsubscribe', NULL, NULL, 0, ?, ?)
            """,
            (str(uuid.uuid4()), customer["id"], json.dumps(meta, ensure_ascii=True), now),
        )

    return {
        "status": "ok",
        "customer_id": customer["id"],
        "suppressed": True,
        "message": "Customer unsubscribed from WhatsApp marketing. Only transactional messages will be sent.",
    }
