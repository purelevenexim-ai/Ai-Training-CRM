"""
Unified Conversation State Manager
Single source of truth for conversation ownership and flow state

Replaces: conversation_owner.py + flow_state_manager.py

Owners (priority order):
- human: Support agent owns conversation
- campaign: Campaign flow is active
- wabis: Bot flow is active
- system: System process (order tracking, etc.)
- ai: Default/fallback
"""

import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from app.runtime_db import ensure_runtime_tables, get_db_connection

logger = logging.getLogger(__name__)

FLOW_TIMEOUT_HOURS = 24


def _serialize_context(context: Optional[dict[str, Any]]) -> str | None:
    if not context:
        return None
    return json.dumps(context, ensure_ascii=False)


def set_conversation_state(
    phone: str,
    owner: str,
    owner_reason: str = "",
    flow_id: Optional[str] = None,
    flow_step: Optional[str] = None,
    expected_responses: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
    timeout_minutes: Optional[int] = None,
) -> None:
    """
    Set complete conversation state. Single source of truth.
    
    Owner types:
    - human: Support agent talking to customer (highest priority)
    - campaign: Campaign flow running
    - wabis: Bot flow running
    - system: System process (order tracking, etc.)
    - ai: AI fallback (default)
    
    Args:
        phone: Customer phone number
        owner: Who owns the conversation
        owner_reason: Why they own it (e.g., "greeting_flow", "language_selection")
        flow_id: Current flow ID (e.g., "greeting", "language_selection")
        flow_step: Current step in flow
        expected_responses: Comma-separated list of expected options from customer (e.g., "english,malayalam,1,2")
        context: Additional context dict
    """
    
    if owner not in ("human", "campaign", "wabis", "system", "ai"):
        logger.warning(f"Invalid owner: {owner}")
        return
    
    try:
        ensure_runtime_tables()
        conn = get_db_connection()
        now = datetime.now(timezone.utc).isoformat()
        
        # Calculate expiry (24h from now for flows, None for human/system)
        expires_at = None
        if owner in ("wabis", "campaign"):
            if timeout_minutes is not None:
                expires_at = (datetime.now(timezone.utc) + timedelta(minutes=max(1, int(timeout_minutes)))).isoformat()
            else:
                expires_at = (datetime.now(timezone.utc) + timedelta(hours=FLOW_TIMEOUT_HOURS)).isoformat()
        
        context_json = _serialize_context(context)
        
        conn.execute(
            """
            INSERT INTO conversation_state 
            (phone, owner, owner_reason, flow_id, flow_step, expected_responses, expires_at, 
             last_activity, context_json, started_at, updated_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(phone) DO UPDATE SET
                owner = excluded.owner,
                owner_reason = excluded.owner_reason,
                flow_id = excluded.flow_id,
                flow_step = excluded.flow_step,
                expected_responses = excluded.expected_responses,
                expires_at = excluded.expires_at,
                context_json = excluded.context_json,
                updated_at = excluded.updated_at,
                last_activity = excluded.updated_at
            """,
            (
                phone,
                owner,
                owner_reason,
                flow_id,
                flow_step,
                expected_responses,
                expires_at,
                now,
                context_json,
                now,
                now,
                now,
            ),
        )
        conn.commit()
        logger.warning(f"[STATE] {phone} → owner={owner}, reason={owner_reason}, flow={flow_id}")
        try:
            from app.ai.customer_state_engine import update_customer_state

            context_fields = context or {}
            update_customer_state(
                phone,
                product_key=str(context_fields.get("product_key") or context_fields.get("active_product") or "") or None,
                latest_intent=str(context_fields.get("latest_intent") or context_fields.get("scenario") or "") or None,
                language=str(context_fields.get("language") or context_fields.get("reply_style") or "") or None,
                journey_stage=str(context_fields.get("journey_stage") or flow_step or "") or None,
                followups_allowed=context_fields.get("followups_allowed"),
                context_updates=context_fields,
            )
        except Exception as exc:
            logger.debug("Failed to mirror state into customer_state columns for %s: %s", phone, exc)
    except Exception as e:
        logger.error(f"Failed to set state: {e}")


def get_conversation_state(phone: str) -> Optional[dict[str, Any]]:
    """
    Get current conversation state.
    Returns None if expired.
    Automatically cleans up expired flows.
    """
    try:
        ensure_runtime_tables()
        conn = get_db_connection()
        row = conn.execute(
            """
            SELECT owner, owner_reason, flow_id, flow_step, expected_responses, expires_at, last_activity, context_json, updated_at,
                   customer_id, language, active_product, latest_intent, price_shared, quantity_selected, address_received,
                   pincode_received, payment_claimed, payment_screenshot_received, defer_intent, followups_allowed,
                   journey_stage, last_ai_reply_hash, last_ai_reply_at
            FROM conversation_state
            WHERE phone = ?
            """,
            (phone,)
        ).fetchone()
        
        if not row:
            return None
        
        (
            owner,
            owner_reason,
            flow_id,
            flow_step,
            expected_responses,
            expires_at,
            last_activity,
            context_json,
            updated_at,
            customer_id,
            language,
            active_product,
            latest_intent,
            price_shared,
            quantity_selected,
            address_received,
            pincode_received,
            payment_claimed,
            payment_screenshot_received,
            defer_intent,
            followups_allowed,
            journey_stage,
            last_ai_reply_hash,
            last_ai_reply_at,
        ) = row
        
        # Check if expired
        if expires_at and datetime.fromisoformat(expires_at) < datetime.now(timezone.utc):
            logger.warning(f"[STATE-EXPIRED] {phone}, {owner} state expired")
            reset_conversation_state(phone)
            return None
        
        return {
            "phone": phone,
            "owner": owner,
            "owner_reason": owner_reason,
            "flow_id": flow_id,
            "flow_step": flow_step,
            "expected_responses": expected_responses,
            "expires_at": expires_at,
            "last_activity": last_activity,
            "context": json.loads(context_json) if context_json else {},
            "updated_at": updated_at,
            "customer_id": customer_id or phone,
            "language": language or "",
            "active_product": active_product or "",
            "latest_intent": latest_intent or "",
            "price_shared": bool(price_shared),
            "quantity_selected": quantity_selected or "",
            "address_received": bool(address_received),
            "pincode_received": pincode_received or "",
            "payment_claimed": bool(payment_claimed),
            "payment_screenshot_received": bool(payment_screenshot_received),
            "defer_intent": defer_intent or "",
            "followups_allowed": bool(followups_allowed if followups_allowed is not None else 1),
            "journey_stage": journey_stage or flow_step or "",
            "last_ai_reply_hash": last_ai_reply_hash or "",
            "last_ai_reply_at": last_ai_reply_at or "",
        }
    except Exception as e:
        logger.error(f"Failed to get state: {e}")
        return None


def reset_conversation_state(phone: str) -> None:
    """Reset conversation to default state (owner=ai)"""
    try:
        ensure_runtime_tables()
        conn = get_db_connection()
        now = datetime.now(timezone.utc).isoformat()
        
        conn.execute(
            """
            UPDATE conversation_state
            SET owner = 'ai', owner_reason = 'reset', flow_id = NULL, 
                flow_step = NULL, expected_responses = NULL, expires_at = NULL,
                context_json = NULL, last_activity = ?, updated_at = ?
            WHERE phone = ?
            """,
            (now, now, phone),
        )
        conn.commit()
        logger.info(f"[STATE-RESET] {phone} → owner=ai")
    except Exception as e:
        logger.error(f"Failed to reset state: {e}")


def mark_activity(phone: str) -> None:
    """
    Update last_activity and extend expiry for active flows.
    Call this whenever customer sends message during flow.
    """
    try:
        ensure_runtime_tables()
        state = get_conversation_state(phone)
        if not state:
            return
        
        conn = get_db_connection()
        now = datetime.now(timezone.utc).isoformat()
        
        # Extend expiry if flow is active
        expires_at = None
        if state["owner"] in ("wabis", "campaign"):
            timeout_minutes = None
            context = state.get("context") or {}
            if isinstance(context, dict) and context.get("timeout_minutes") is not None:
                try:
                    timeout_minutes = int(context.get("timeout_minutes"))
                except (TypeError, ValueError):
                    timeout_minutes = None
            if timeout_minutes is not None:
                expires_at = (datetime.now(timezone.utc) + timedelta(minutes=max(1, timeout_minutes))).isoformat()
            else:
                expires_at = (datetime.now(timezone.utc) + timedelta(hours=FLOW_TIMEOUT_HOURS)).isoformat()
        
        conn.execute(
            "UPDATE conversation_state SET last_activity = ?, expires_at = ? WHERE phone = ?",
            (now, expires_at, phone)
        )
        conn.commit()
        logger.info(f"[ACTIVITY] {phone} - extended expiry for {state['owner']} flow")
    except Exception as e:
        logger.error(f"Failed to mark activity: {e}")


def merge_conversation_context(phone: str, updates: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    """Merge new keys into the stored conversation context."""
    if not phone or not updates:
        return get_conversation_state(phone) if phone else None

    try:
        ensure_runtime_tables()
        state = get_conversation_state(phone)
        if not state:
            return None

        context = dict(state.get("context") or {})
        context.update(updates)
        now = datetime.now(timezone.utc).isoformat()

        conn = get_db_connection()
        conn.execute(
            """
            UPDATE conversation_state
            SET context_json = ?, updated_at = ?
            WHERE phone = ?
            """,
            (_serialize_context(context), now, phone),
        )
        conn.commit()
        return get_conversation_state(phone)
    except Exception as e:
        logger.error(f"Failed to merge conversation context: {e}")
        return None
