from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.ai.audit_logger import log_routing_decision as audit_log_routing_decision
from app.ai.conversation_state_manager import get_conversation_state, mark_activity, reset_conversation_state
from app.ai.flow_helpers import flow_match, log_flow_abandoned
from app.ai.intent_registry import intent_metadata
from app.ai.product_knowledge import detect_product
from app.storage import get_db_connection

logger = logging.getLogger(__name__)

WELCOME_IDLE_TIMEOUT_MINUTES = 2
AUTOMATION_IDLE_TIMEOUT_MINUTES = 3


def _looks_like_wabis_button_reply_text(raw_message: str) -> bool:
    message = (raw_message or "").strip().lower()
    return bool(message.startswith("#button reply#"))


def _structured_button_click(message: str, message_meta: dict[str, Any]) -> bool:
    return bool(
        message_meta.get("structured_button_click")
        or message_meta.get("postback_id")
        or message_meta.get("provider_postback_id")
        or message_meta.get("reply_message_id")
        or str(message_meta.get("message_type") or "").lower() == "postback"
        or _looks_like_wabis_button_reply_text(message)
    )


def _wabis_timeout_minutes(flow_step: str | None) -> int:
    if flow_step in {"welcome_active", "awaiting_language"}:
        return WELCOME_IDLE_TIMEOUT_MINUTES
    return AUTOMATION_IDLE_TIMEOUT_MINUTES


def _within_timeout(state: dict[str, Any]) -> bool:
    if not state:
        return False
    last_activity = state.get("last_activity") or state.get("updated_at")
    if not last_activity:
        return False
    try:
        last_seen = datetime.fromisoformat(str(last_activity))
    except ValueError:
        return False
    timeout_minutes = _wabis_timeout_minutes(state.get("flow_step"))
    return (datetime.now(timezone.utc) - last_seen).total_seconds() <= timeout_minutes * 60


def _latent_handoff_action(
    *,
    message: str,
    product_key: str,
    detected_intent: str,
    reply_style: str,
    customer_reference: str | None = None,
    after_minutes: int,
) -> dict[str, Any]:
    return {
        "product_key": product_key,
        "detected_intent": detected_intent,
        "source_message": message[:500],
        "reply_style": reply_style,
        "customer_reference": customer_reference,
        "after_minutes": max(1, int(after_minutes)),
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }


def _route_catalog(reason: str, *, intent: str, product_key: str | None = None, product_context: dict[str, Any] | None = None) -> dict[str, Any]:
    decision = {
        "route": "catalog",
        "reason": reason,
        "intent": intent,
    }
    if product_key:
        decision["resolved_product_key"] = product_key
    if product_context:
        decision["product_context"] = product_context
    return decision


def route_message(phone: str, message: str, message_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    message_meta = message_meta or {}
    state = get_conversation_state(phone)
    product_key = detect_product(message)
    metadata = intent_metadata(message, product_detected=bool(product_key))
    structured_button_click = _structured_button_click(message, message_meta)
    has_previous_interaction = bool(message_meta.get("has_previous_interaction"))
    flow_break_detection_enabled = bool(message_meta.get("flow_break_detection_enabled", True))
    expected_responses = [
        option.strip().lower()
        for option in str((state or {}).get("expected_responses") or "").split(",")
        if option.strip()
    ]

    if structured_button_click and not (state and state.get("owner") == "wabis"):
        return {
            "route": "wabis",
            "reason": "Structured Wabis reply without active local state",
            "intent": metadata["detected_intent"],
            "message_understanding": metadata,
            "action_set_owner": {
                "owner": "wabis",
                "flow_id": "automation_flow",
                "flow_step": "automation_active",
                "reason": "structured_wabis_reply",
                "timeout_minutes": AUTOMATION_IDLE_TIMEOUT_MINUTES,
                "context": {
                    "timeout_minutes": AUTOMATION_IDLE_TIMEOUT_MINUTES,
                    "wabis_status": "automation_active",
                },
            },
        }

    if state and state.get("owner") == "human":
        return {
            "route": "human_only",
            "reason": f"Human agent owns conversation: {state.get('owner_reason')}",
            "owner": "human",
            "intent": metadata["detected_intent"],
            "message_understanding": metadata,
        }

    if state and state.get("owner") == "campaign":
        mark_activity(phone)
        return {
            "route": "campaign",
            "reason": f"Campaign {state.get('flow_id')} active",
            "owner": "campaign",
            "intent": metadata["detected_intent"],
            "message_understanding": metadata,
        }

    if state and state.get("flow_id") == "product_journey":
        product_context = dict(state.get("context") or {})
        context_product = str(product_context.get("product_key") or "").strip()
        active_product = product_key or detect_product(context_product) or context_product
        if metadata["detected_intent"] in {"complaint", "return_refund", "human_handoff"}:
            return {
                "route": "escalation",
                "reason": "Complaint or handoff requested during product journey",
                "intent": metadata["detected_intent"],
                "message_understanding": metadata,
            }
        if active_product:
            product_context["product_key"] = active_product
            return _route_catalog(
                "Continue AI product journey",
                intent=metadata["detected_intent"],
                product_key=active_product,
                product_context=product_context,
            ) | {"message_understanding": metadata}

    if state and state.get("owner") == "wabis":
        if structured_button_click or (expected_responses and flow_match(message, expected_responses)):
            mark_activity(phone)
            response = {
                "route": "wabis",
                "reason": "Structured Wabis interaction keeps automation active",
                "owner": "wabis",
                "intent": metadata["detected_intent"],
                "message_understanding": metadata,
                "action_set_owner": {
                    "owner": "wabis",
                    "flow_id": state.get("flow_id") or "automation_flow",
                    "flow_step": "automation_active",
                    "reason": "wabis_automation_active",
                    "expected_responses": state.get("expected_responses"),
                    "timeout_minutes": AUTOMATION_IDLE_TIMEOUT_MINUTES,
                    "context": {
                        **(state.get("context") or {}),
                        "timeout_minutes": AUTOMATION_IDLE_TIMEOUT_MINUTES,
                        "wabis_status": "automation_active",
                    },
                },
            }
            latent = dict((state.get("context") or {}).get("latent_handoff") or {})
            if latent.get("product_key"):
                latent["after_minutes"] = AUTOMATION_IDLE_TIMEOUT_MINUTES
                response["action_schedule_latent_handoff"] = latent
            return response

        if _within_timeout(state):
            response = {
                "route": "wabis",
                "reason": "Wabis automation still active",
                "owner": "wabis",
                "intent": metadata["detected_intent"],
                "message_understanding": metadata,
            }
            if product_key:
                latent = _latent_handoff_action(
                    message=message,
                    product_key=product_key,
                    detected_intent=metadata["detected_intent"],
                    reply_style=metadata["detected_language"],
                    customer_reference=product_key.replace("_", " "),
                    after_minutes=_wabis_timeout_minutes(state.get("flow_step")),
                )
                response["action_merge_context"] = {
                    "latent_handoff": latent,
                    "timeout_minutes": _wabis_timeout_minutes(state.get("flow_step")),
                }
                response["action_schedule_latent_handoff"] = latent
            return response

        if flow_break_detection_enabled:
            log_flow_abandoned(
                phone,
                flow_name=str(state.get("flow_id") or "wabis_flow"),
                reason="automation_timeout_handoff",
                expected_options=expected_responses,
                received_message=message,
            )
            latent = dict((state.get("context") or {}).get("latent_handoff") or {})
            reset_conversation_state(phone)
            if latent.get("product_key"):
                product_context = {
                    "product_key": latent.get("product_key"),
                    "reply_style": latent.get("reply_style"),
                    "customer_reference": latent.get("customer_reference"),
                }
                return _route_catalog(
                    "Wabis flow timed out; answering deferred product intent",
                    intent=str(latent.get("detected_intent") or "fallback"),
                    product_key=str(latent.get("product_key")),
                    product_context=product_context,
                ) | {
                    "action_cancel_followups": {
                        "reason": "latent_handoff_consumed",
                        "stages": ["latent_handoff"],
                    },
                    "message_understanding": {
                        **metadata,
                        "detected_product": str(latent.get("product_key")),
                    }
                }
            if product_key:
                return _route_catalog(
                    "Wabis flow timed out; handling current product query",
                    intent=metadata["detected_intent"],
                    product_key=product_key,
                ) | {
                    "action_cancel_followups": {
                        "reason": "latent_handoff_consumed",
                        "stages": ["latent_handoff"],
                    },
                    "message_understanding": metadata,
                }

    if metadata["is_pure_greeting"] and not product_key and not has_previous_interaction:
        return {
            "route": "wabis",
            "reason": "New customer greeting starts welcome flow",
            "intent": "fallback",
            "message_understanding": metadata,
            "action_set_owner": {
                "owner": "wabis",
                "flow_id": "welcome_flow",
                "flow_step": "awaiting_language",
                "reason": "welcome_flow",
                "expected_responses": "english,malayalam,1,2",
                "timeout_minutes": WELCOME_IDLE_TIMEOUT_MINUTES,
                "context": {
                    "timeout_minutes": WELCOME_IDLE_TIMEOUT_MINUTES,
                    "wabis_status": "awaiting_language",
                },
            },
            "action_cancel_followups": {
                "reason": "new_customer_welcome",
            },
        }

    if metadata["detected_intent"] in {"complaint", "return_refund", "human_handoff"}:
        return {
            "route": "escalation",
            "reason": "Human support path triggered",
            "intent": metadata["detected_intent"],
            "message_understanding": metadata,
        }

    if product_key:
        return _route_catalog(
            "Product-first query bypasses welcome flow",
            intent=metadata["detected_intent"],
            product_key=product_key,
        ) | {"message_understanding": {**metadata, "detected_product": product_key}}

    return {
        "route": "ai",
        "reason": "No product detected; using AI fallback",
        "intent": metadata["detected_intent"],
        "message_understanding": metadata,
    }


def log_routing_decision(phone: str, message: str, state_before: dict, decision: dict[str, Any]) -> None:
    try:
        conn = get_db_connection()
        understanding = decision.get("message_understanding") or {}
        conn.execute(
            """
            INSERT INTO routing_log
            (id, phone, message, owner_before, route_taken, context, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                phone,
                message[:200],
                state_before.get("owner") if state_before else None,
                decision.get("route"),
                json.dumps(
                    {
                        "intent": decision.get("intent"),
                        "reason": decision.get("reason"),
                        "flow": state_before.get("flow_id") if state_before else None,
                        "product": understanding.get("detected_product") or decision.get("resolved_product_key"),
                        "language": understanding.get("detected_language"),
                    },
                    ensure_ascii=False,
                ),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()

        owner_before = state_before.get("owner") if state_before else None
        owner_after = decision.get("action_set_owner", {}).get("owner") or decision.get("owner") or owner_before
        audit_log_routing_decision(
            phone=phone,
            owner_before=owner_before,
            owner_after=owner_after or owner_before,
            route_decision=decision.get("route"),
            reason=decision.get("reason"),
            active_flow=state_before.get("flow_id") if state_before else None,
            detected_intent=decision.get("intent"),
            message=message[:200],
            metadata={
                "route": decision.get("route"),
                "reason": decision.get("reason"),
                "intent": decision.get("intent"),
                "message_understanding": decision.get("message_understanding") or {},
                "resolved_product_key": decision.get("resolved_product_key"),
            },
        )
    except Exception as exc:
        logger.error("Failed to log routing: %s", exc)
