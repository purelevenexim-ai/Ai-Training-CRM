"""
24-Hour Conversation Session Manager and AI Dispatch routes.

Endpoints:
  POST /api/ai/session/open          — Open a 24h session after template delivery
  GET  /api/ai/session/{session_id}  — Get session state
  POST /api/ai/session/generate-followups — Generate + schedule 4 follow-up messages
  POST /api/ai/dispatch              — n8n calls this to get next message for customer
  POST /api/ai/dispatch/send-followup/{id} — n8n sends a scheduled followup
  GET  /api/ai/catalog               — List synced Shopify products
  POST /api/ai/sync                  — Trigger manual Shopify sync
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from app.ai.message_renderer import render_followup_message
from app.ai.openrouter_client import ai_client
from app.intelligence.shopify_sync import (
    get_active_offer_for_product,
    get_active_products,
    get_product_by_id,
    run_full_sync,
)
from app.storage import get_db_connection

logger = logging.getLogger(__name__)
router = APIRouter()

# ── Follow-up schedule (minutes after session start) ─────────────────────────
FOLLOWUP_SCHEDULE = [
    {"offset_minutes": 10, "message_type": "story"},
    {"offset_minutes": 60, "message_type": "social_proof"},
    {"offset_minutes": 240, "message_type": "offer"},
    {"offset_minutes": 720, "message_type": "urgency"},
    {"offset_minutes": 1380, "message_type": "soft_exit"},  # T+23h
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────

class OpenSessionRequest(BaseModel):
    customer_phone: str = Field(min_length=7, max_length=20)
    shop_domain: str
    trigger_template: str
    trigger_product_id: str = ""


class DispatchRequest(BaseModel):
    customer_phone: str = Field(min_length=7, max_length=20)
    shop_domain: str
    incoming_reply: str = ""  # If customer replied, classify + use


# ─────────────────────────────────────────────────────────────────────────────
# Session Management
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/ai/session/open")
def open_session(req: OpenSessionRequest) -> dict[str, Any]:
    """
    Called when a template message is successfully delivered.
    Opens a 24-hour conversation session and pre-generates follow-up messages.
    """
    phone = _normalize_phone(req.customer_phone)
    now_dt = _now_dt()
    expires_dt = now_dt + timedelta(hours=23, minutes=50)  # slightly under 24h

    with get_db_connection() as conn:
        # Check if session already open for this phone
        existing = conn.execute(
            """
            SELECT id FROM conversation_sessions
            WHERE customer_phone = ? AND is_active = 1 AND session_expires > ?
            """,
            (phone, _now()),
        ).fetchone()

        if existing:
            return {"session_id": existing["id"], "status": "already_open"}

        # Fetch customer
        customer = conn.execute(
            "SELECT * FROM journey_customers WHERE phone = ? ORDER BY created_at DESC LIMIT 1",
            (phone,),
        ).fetchone()
        customer_dict = dict(customer) if customer else {"phone": phone, "name": "Customer"}

        # Get available products from synced catalog
        products = get_active_products(conn, limit=10)
        if not products:
            logger.warning("No synced products — cannot open AI session for %s", phone)
            return {"session_id": None, "status": "no_products_synced"}

        # Pick product (from trigger or best match)
        if req.trigger_product_id:
            trigger_product = get_product_by_id(conn, req.trigger_product_id)
            if not trigger_product:
                trigger_product = products[0]
        else:
            trigger_product = products[0]

        session_id = str(uuid.uuid4())

        conn.execute(
            """
            INSERT INTO conversation_sessions
              (id, customer_id, customer_phone, shop_domain, trigger_template,
               trigger_product_id, session_start, session_expires, is_active,
               messages_sent, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?)
            """,
            (
                session_id,
                str(customer_dict.get("id") or ""),
                phone,
                req.shop_domain,
                req.trigger_template,
                trigger_product["id"],
                now_dt.isoformat(),
                expires_dt.isoformat(),
                _now(),
            ),
        )

        # Generate follow-up decisions and schedule them
        followup_count = _generate_followups(conn, session_id, customer_dict, trigger_product, products, now_dt)

    return {
        "session_id": session_id,
        "status": "opened",
        "session_expires": expires_dt.isoformat(),
        "followups_scheduled": followup_count,
        "product": trigger_product.get("title"),
    }


@router.get("/ai/session/{session_id}")
def get_session(session_id: str) -> dict[str, Any]:
    with get_db_connection() as conn:
        session = conn.execute(
            "SELECT * FROM conversation_sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        followups = conn.execute(
            "SELECT * FROM conversation_followups WHERE session_id = ? ORDER BY scheduled_at",
            (session_id,),
        ).fetchall()

        messages = conn.execute(
            "SELECT * FROM conversation_messages WHERE session_id = ? ORDER BY turn_number",
            (session_id,),
        ).fetchall()

    return {
        "session": dict(session),
        "followups": [dict(f) for f in followups],
        "messages": [dict(m) for m in messages],
    }


# ─────────────────────────────────────────────────────────────────────────────
# AI Dispatch (n8n calls this)
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/ai/dispatch")
def ai_dispatch(req: DispatchRequest) -> dict[str, Any]:
    """
    Main AI dispatch endpoint called by n8n.

    If customer replied: classify intent → decide action.
    If scheduled followup: render next message in sequence.

    Returns:
      {
        "should_send": bool,
        "message": "rendered text",
        "message_type": "story|offer|...",
        "action": "send|alert_owner|unsubscribe|no_action",
        "product_title": "...",
        "session_id": "..."
      }
    """
    phone = _normalize_phone(req.customer_phone)

    with get_db_connection() as conn:
        # Get active session
        session = conn.execute(
            """
            SELECT * FROM conversation_sessions
            WHERE customer_phone = ? AND is_active = 1 AND session_expires > ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (phone, _now()),
        ).fetchone()

        customer = conn.execute(
            "SELECT * FROM journey_customers WHERE phone = ? ORDER BY created_at DESC LIMIT 1",
            (phone,),
        ).fetchone()
        customer_dict = dict(customer) if customer else {"phone": phone, "name": "Customer", "id": ""}

        # Handle incoming reply (customer sent something)
        if req.incoming_reply.strip():
            return _handle_reply(conn, req, customer_dict, session, phone)

        if not session:
            return {"should_send": False, "action": "no_active_session"}

        session_dict = dict(session)

        # Find next pending followup
        pending = conn.execute(
            """
            SELECT * FROM conversation_followups
            WHERE session_id = ? AND sent = 0 AND scheduled_at <= ?
            ORDER BY scheduled_at ASC LIMIT 1
            """,
            (session_dict["id"], _now()),
        ).fetchone()

        if not pending:
            return {"should_send": False, "action": "no_pending_followup"}

        followup = dict(pending)
        product_id = followup.get("product_id") or session_dict.get("trigger_product_id", "")
        product = get_product_by_id(conn, product_id) if product_id else None

        if not product:
            products = get_active_products(conn, limit=1)
            product = products[0] if products else None

        if not product:
            return {"should_send": False, "action": "no_product_available"}

        # Render the pre-generated message (already stored in followup row)
        message = followup.get("message_content")
        if not message:
            message = render_followup_message(
                message_type=followup["message_type"],
                decision={"product_id": product["id"], "story_type": "harvest_quality",
                          "tone": "friendly", "urgency": "low"},
                customer=customer_dict,
                session_id=session_dict["id"],
            )

        # Mark followup as sent
        conn.execute(
            "UPDATE conversation_followups SET sent = 1, sent_at = ? WHERE id = ?",
            (_now(), followup["id"]),
        )
        # Increment messages_sent counter on session
        conn.execute(
            "UPDATE conversation_sessions SET messages_sent = messages_sent + 1 WHERE id = ?",
            (session_dict["id"],),
        )

        return {
            "should_send": True,
            "message": message,
            "message_type": followup["message_type"],
            "action": "send",
            "product_title": product.get("title"),
            "product_id": product["id"],
            "session_id": session_dict["id"],
            "followup_id": followup["id"],
        }


@router.post("/ai/dispatch/mark-clicked/{followup_id}")
def mark_followup_clicked(followup_id: str) -> dict[str, str]:
    """Called by n8n when customer clicks a link. Tracks conversion signals."""
    with get_db_connection() as conn:
        conn.execute(
            "UPDATE conversation_followups SET clicked = 1, clicked_at = ? WHERE id = ?",
            (_now(), followup_id),
        )
    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────────────────────
# Catalog & Sync
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/ai/catalog")
def get_catalog(limit: int = 20) -> dict[str, Any]:
    """Return synced product catalog for inspection."""
    with get_db_connection() as conn:
        products = get_active_products(conn, limit=min(limit, 100))
        offers = conn.execute(
            "SELECT * FROM shopify_offers WHERE is_active = 1 ORDER BY discount_value DESC LIMIT 20",
        ).fetchall()
        last_sync = conn.execute(
            "SELECT MAX(synced_at) as last FROM shopify_products",
        ).fetchone()

    return {
        "products": products,
        "active_offers": [dict(o) for o in offers],
        "last_sync": last_sync["last"] if last_sync else None,
        "product_count": len(products),
    }


@router.post("/ai/sync")
def trigger_sync(background_tasks: BackgroundTasks) -> dict[str, str]:
    """Trigger a Shopify data sync in the background."""
    background_tasks.add_task(run_full_sync)
    return {"status": "sync_started", "message": "Shopify sync running in background"}


# ─────────────────────────────────────────────────────────────────────────────
# Private helpers
# ─────────────────────────────────────────────────────────────────────────────

def _generate_followups(
    conn: Any,
    session_id: str,
    customer: dict[str, Any],
    trigger_product: dict[str, Any],
    all_products: list[dict[str, Any]],
    session_start: datetime,
) -> int:
    """
    Pre-generate and store follow-up messages for the 24h session.
    Uses AI decision engine for personalization, falls back to rules.
    """
    now = _now()
    # Get conversation history (empty for new session)
    history = conn.execute(
        "SELECT * FROM conversation_messages WHERE session_id = ? ORDER BY turn_number",
        (session_id,),
    ).fetchall()
    history_list = [dict(h) for h in history]

    count = 0
    for slot in FOLLOWUP_SCHEDULE:
        offset = slot["offset_minutes"]
        msg_type = slot["message_type"]
        scheduled_at = (session_start + timedelta(minutes=offset)).isoformat()

        # AI decides parameters (guardrailed — only picks from real catalog)
        decision = ai_client.decide_next_message(
            customer=customer,
            conversation_history=history_list,
            available_products=all_products,
            session_turn=count,
        )
        # Ensure product_id is the trigger product for continuity
        if trigger_product and not decision.get("product_id"):
            decision["product_id"] = trigger_product["id"]

        # Render message using REAL data
        message = render_followup_message(
            message_type=msg_type,
            decision=decision,
            customer=customer,
            session_id=session_id,
        )

        if not message:
            logger.warning("Could not render followup type=%s for session %s", msg_type, session_id)
            continue

        conn.execute(
            """
            INSERT INTO conversation_followups
              (id, session_id, message_type, message_content, product_id,
               scheduled_at, sent, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                str(uuid.uuid4()),
                session_id,
                msg_type,
                message,
                decision.get("product_id", ""),
                scheduled_at,
                now,
            ),
        )
        count += 1

    return count


def _handle_reply(
    conn: Any,
    req: DispatchRequest,
    customer: dict[str, Any],
    session: Any,
    phone: str,
) -> dict[str, Any]:
    """
    Handle an incoming customer reply inside or outside a 24h session.
    Classify intent, decide action, optionally alert owner.
    """
    from app.ai.alert_sender import alert_bulk_inquiry, alert_complaint, alert_purchase_intent

    reply = req.incoming_reply.strip()
    classification = ai_client.classify_reply(reply)
    intent = classification["intent"]
    action = classification["action"]

    # Record the reply in conversation_messages if session is active
    if session:
        session_dict = dict(session)
        turn = (session_dict.get("messages_sent") or 0) + 1
        conn.execute(
            """
            INSERT INTO conversation_messages
              (id, session_id, turn_number, actor, customer_text, created_at)
            VALUES (?, ?, ?, 'customer', ?, ?)
            """,
            (str(uuid.uuid4()), session_dict["id"], turn, reply[:1000], _now()),
        )

    # Take action based on intent
    if intent == "bulk_inquiry":
        alert_bulk_inquiry(phone, reply)
        return {"should_send": False, "action": "alert_sent_bulk_inquiry", "intent": intent}

    elif intent == "complaint":
        alert_complaint(phone, reply)
        # Pause campaigns
        conn.execute(
            "UPDATE journey_customers SET do_not_message = 1 WHERE phone = ?",
            (phone,),
        )
        return {"should_send": False, "action": "campaigns_paused_complaint", "intent": intent}

    elif intent == "purchase_intent":
        alert_purchase_intent(phone, reply)
        return {"should_send": False, "action": "alert_sent_purchase_intent", "intent": intent}

    elif intent == "unsubscribe":
        conn.execute(
            """
            UPDATE journey_customers
            SET do_not_message = 1, whatsapp_subscription_status = 'unsubscribed'
            WHERE phone = ?
            """,
            (phone,),
        )
        # Close active session
        if session:
            conn.execute(
                "UPDATE conversation_sessions SET is_active = 0 WHERE id = ?",
                (dict(session)["id"],),
            )
        return {"should_send": False, "action": "unsubscribed", "intent": intent}

    elif intent in ("recipe_interest", "question_product"):
        # Tag for educational content preference
        conn.execute(
            """
            UPDATE journey_customers
            SET is_responsive = 1
            WHERE phone = ?
            """,
            (phone,),
        )
        return {"should_send": False, "action": "tagged_educational_preference", "intent": intent}

    else:
        # affirmation / feedback_positive / ignore / unknown → log and continue
        return {"should_send": False, "action": action, "intent": intent}


def _normalize_phone(raw: str) -> str:
    return "".join(c for c in raw if c.isdigit())
