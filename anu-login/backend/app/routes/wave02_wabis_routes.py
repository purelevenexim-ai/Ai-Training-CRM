"""
Wave 0.2 AI Reply Routes - Handle incoming Wabis messages and send AI-generated replies

Endpoints:
  POST /api/ai/wave02/webhook/wabis/incoming - Receive incoming messages from Wabis
  POST /api/ai/wave02/webhook/wabis/reply-async - Send AI reply asynchronously
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Optional
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Body
from pydantic import BaseModel, Field

from app.storage import get_db_connection
from app.ai.wabis_reply_generator import WabisReplyGenerator
from app.services.owner_dashboard_service import get_ai_control_settings
from app.ai.intent_router import route_message, log_routing_decision
from app.ai.conversation_state_manager import get_conversation_state, merge_conversation_context, set_conversation_state
from app.ai.clarification_flow import send_clarification_menu, log_knowledge_gap, log_missing_product
from app.ai.audit_logger import log_customer_message
from app.ai.audit_logger import log_ai_response
from app.ai.customer_state_engine import get_customer_state, record_ai_reply, reply_hash
from app.ai.message_processing_lock import claim_message_owner, finish_message_owner
from app.ai.whatsapp_delivery_service import send_whatsapp_reply_with_fallback
from app.services.product_followup_service import cancel_product_followups, queue_latent_handoff_followup
from app.services.customer_journey_service import stop_customer_journeys_for_customer
from app.services.ai_reply_queue_service import (
    enqueue_ai_reply_job,
    log_ai_decision,
    mark_processed_event,
    normalize_event_id,
    stable_payload_hash,
)

logger = logging.getLogger(__name__)
# Mounted in app.main with prefix="/api", so the public path becomes:
# /api/ai/wave02/webhook/wabis/...
router = APIRouter(prefix="/ai/wave02/webhook/wabis", tags=["wave02-wabis"])


# ─────────────────────────────────────────────────────────────────────────────
# Models
# ─────────────────────────────────────────────────────────────────────────────

class WabisIncomingMessage(BaseModel):
    """
    Incoming payload from Wabis Out-bound Webhook.
    Wabis sends: subscriber_id, phone (or chat_id), first_name,
    postback_id / input_flow_id / user_input, type, text/value.
    We also accept our internal format for direct API calls.
    """
    # Wabis native fields
    subscriber_id: Optional[str] = None
    phone: Optional[str] = None          # Wabis: subscriber phone number
    chat_id: Optional[str] = None        # alternative Wabis phone field
    first_name: Optional[str] = None
    postback_id: Optional[str] = None
    postbackid: Optional[str] = None
    reply_message_id: Optional[str] = None
    input_flow_id: Optional[str] = None
    user_input: Optional[str] = None     # text typed by user in input flow
    text: Optional[str] = None           # postback button text
    value: Optional[str] = None          # input flow response value
    type: Optional[str] = None           # "postback", "user_input", "location"
    label_names: Optional[str] = None
    # Wabis incoming message webhook fields
    message: Optional[str] = None           # Old format
    user_message: Optional[str] = None      # Real Wabis incoming webhook format
    # Internal / direct-call fields (all optional for Wabis compat)
    webhook_id: Optional[str] = None
    conversation_id: Optional[str] = None
    from_phone: Optional[str] = None
    to_phone: Optional[str] = None
    message_type: str = "text"
    body: Optional[str] = None
    timestamp: Optional[str] = None
    template_id: Optional[str] = None

    model_config = {"extra": "allow"}

    # Bot's own phone — never use as the reply target
    _BOT_PHONE = "918848265849"

    def resolved_phone(self) -> str:
        """Return the caller's (customer's) phone number from any Wabis field variant."""
        # Prefer explicit from_phone, subscriber_phone, or chat_id over phone
        # because 'phone' in incoming webhooks is sometimes the bot's own number
        candidates = [
            self.from_phone,
            getattr(self, "subscriber_phone", None),
            self.chat_id,
        ]
        for raw in candidates:
            if raw:
                digits = "".join(c for c in raw if c.isdigit())
                if digits and digits != self._BOT_PHONE:
                    return digits

        # Try extracting from subscriber_id (format: "phone-botid")
        if self.subscriber_id and "-" in self.subscriber_id:
            phone_part = self.subscriber_id.split("-")[0]
            digits = "".join(c for c in phone_part if c.isdigit())
            if digits and digits != self._BOT_PHONE:
                return digits

        # Fall back to phone field (even if it might be the bot phone)
        raw = self.phone or ""
        return "".join(c for c in raw if c.isdigit())

    def resolved_conversation_id(self) -> str:
        return self.conversation_id or self.subscriber_id or str(uuid.uuid4())

    def resolved_message(self) -> str:
        """Return the best available message text."""
        def normalize_message_value(value: Optional[str]) -> str:
            if not value:
                return ""
            text_value = str(value).strip()
            if not text_value:
                return ""
            if text_value.startswith("{") and text_value.endswith("}"):
                try:
                    parsed = json.loads(text_value)
                except Exception:
                    parsed = None
                if isinstance(parsed, dict):
                    caption = str(parsed.get("caption") or parsed.get("text") or parsed.get("body") or "").strip()
                    if caption:
                        return caption
                    media_type = str(parsed.get("type") or "media").strip().lower() or "media"
                    return f"[[media:{media_type}]]"
            return text_value

        return (
            normalize_message_value(self.user_message)      # Real Wabis incoming webhook (priority)
            or normalize_message_value(self.message)        # Test format
            or normalize_message_value(self.body)
            or normalize_message_value(self.user_input)
            or normalize_message_value(self.value)
            or normalize_message_value(self.text)
            or normalize_message_value(self.postback_id)
            or normalize_message_value(self.postbackid)
            or ""
        )

    def resolved_name(self) -> str:
        return self.first_name or "Customer"


class WabisReplyRequest(BaseModel):
    """Request to send AI reply"""
    conversation_id: str
    customer_phone: str
    customer_name: str = "Customer"
    incoming_message: str
    product_id: Optional[str] = None


def _has_previous_interaction(phone: str) -> bool:
    if not phone:
        return False
    try:
        conn = get_db_connection()
        incoming_count = conn.execute(
            "SELECT COUNT(*) AS total FROM ai_incoming_messages WHERE customer_phone = ?",
            (phone,),
        ).fetchone()
        if incoming_count and int(incoming_count["total"] or 0) > 1:
            return True
        outgoing_count = conn.execute(
            "SELECT COUNT(*) AS total FROM ai_outgoing_replies WHERE customer_phone = ?",
            (phone,),
        ).fetchone()
        if outgoing_count and int(outgoing_count["total"] or 0) > 0:
            return True
        audit_count = conn.execute(
            "SELECT COUNT(*) AS total FROM conversation_audit_log WHERE phone = ?",
            (phone,),
        ).fetchone()
        if audit_count and int(audit_count["total"] or 0) > 1:
            return True
        return False
    except Exception as exc:
        logger.warning("Failed to inspect previous interaction for %s: %s", phone, exc)
        return False


def _structured_wabis_event(payload: WabisIncomingMessage, incoming_message: str) -> bool:
    message = (incoming_message or "").strip().lower()
    return bool(
        payload.postback_id
        or payload.postbackid
        or payload.reply_message_id
        or str(payload.type or "").lower() == "postback"
        or message.startswith("#button reply#")
    )


def _system_or_label_event(payload: WabisIncomingMessage, incoming_message: str) -> bool:
    event_type = str(getattr(payload, "event_type", "") or payload.type or "").strip().lower()
    sender_type = str(getattr(payload, "sender_type", "") or getattr(payload, "from_type", "") or "").strip().lower()
    if sender_type in {"bot", "admin", "agent", "system"}:
        return True
    if event_type in {"label_added", "label_removed", "status_changed", "message_status", "delivered", "read"}:
        return True
    if payload.label_names and not incoming_message.strip():
        return True
    return False


def _coerce_wabis_payload(raw_payload: dict[str, Any]) -> dict[str, Any]:
    """Accept Wabis' loose webhook shapes without failing FastAPI/Pydantic validation."""
    payload = dict(raw_payload or {})
    string_fields = {
        "subscriber_id",
        "phone",
        "chat_id",
        "first_name",
        "postback_id",
        "postbackid",
        "reply_message_id",
        "input_flow_id",
        "user_input",
        "text",
        "value",
        "type",
        "label_names",
        "message",
        "user_message",
        "webhook_id",
        "conversation_id",
        "from_phone",
        "to_phone",
        "message_type",
        "body",
        "timestamp",
        "template_id",
    }
    for key in string_fields:
        value = payload.get(key)
        if value is None or isinstance(value, str):
            continue
        if isinstance(value, (dict, list)):
            payload[key] = json.dumps(value, ensure_ascii=False)
        else:
            payload[key] = str(value)
    return payload


def _journey_stop_flag_for_customer_message(incoming_message: str) -> str:
    """Map customer replies to the most specific saved journey stop rule."""
    normalized = f" {str(incoming_message or '').strip().lower()} "
    if any(token in normalized for token in (" venda", " vendaa", " no need", " not interested", " don't want", " dont want")):
        return "stop_on_not_interested"
    if any(token in normalized for token in (" stop", " cancel", " unsubscribe")):
        return "stop_on_stop"
    if any(token in normalized for token in (" paid", " payment done", " cash paid", " order confirm", " confirm order")):
        return "stop_on_order"
    return "stop_on_reply"


def _message_meta(
    payload: WabisIncomingMessage,
    incoming_message: str,
    customer_phone: str,
    control: dict[str, Any] | None = None,
) -> dict[str, Any]:
    def collect_media_fragments(value: Any, fragments: list[str]) -> None:
        if value is None:
            return
        if isinstance(value, dict):
            for key, item in value.items():
                key_name = str(key or "").strip().lower()
                if key_name in {
                    "caption",
                    "text",
                    "body",
                    "ocr_text",
                    "ocr",
                    "analysis_text",
                    "media_text",
                    "title",
                    "description",
                    "filename",
                    "file_name",
                    "message",
                }:
                    collect_media_fragments(item, fragments)
                elif isinstance(item, (dict, list)):
                    collect_media_fragments(item, fragments)
            return
        if isinstance(value, list):
            for item in value:
                collect_media_fragments(item, fragments)
            return
        text = str(value or "").strip()
        if not text or text.startswith("http://") or text.startswith("https://"):
            return
        fragments.append(text)

    def extract_media_hints() -> dict[str, Any]:
        fragments: list[str] = []
        for raw_value in (
            payload.user_message,
            payload.message,
            payload.body,
            payload.user_input,
            payload.value,
            payload.text,
        ):
            if not raw_value:
                continue
            text = str(raw_value).strip()
            if text.startswith("{") and text.endswith("}"):
                try:
                    parsed = json.loads(text)
                except Exception:
                    parsed = text
                collect_media_fragments(parsed, fragments)
            else:
                collect_media_fragments(text, fragments)

        unique: list[str] = []
        seen: set[str] = set()
        for fragment in fragments:
            lowered = fragment.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            unique.append(fragment)

        media_type = str(payload.message_type or payload.type or "").strip().lower()
        if not media_type and incoming_message.startswith("[[media:"):
            media_type = incoming_message.removeprefix("[[media:").removesuffix("]]").strip().lower()

        return {
            "media_type": media_type,
            "media_text": " ".join(unique).strip(),
            "media_caption": unique[0] if unique else "",
            "raw_message": payload.user_message or payload.message or payload.body or "",
        }

    control = control or get_ai_control_settings()
    meta = {
        "message_type": payload.type or payload.message_type or "text",
        "postback_id": payload.postback_id or payload.postbackid,
        "provider_postback_id": payload.postback_id or payload.postbackid,
        "reply_message_id": payload.reply_message_id,
        "input_flow_id": payload.input_flow_id,
        "structured_button_click": _structured_wabis_event(payload, incoming_message),
        "flow_break_detection_enabled": control.get("flow_break_detection_enabled", True),
        "structured_button_passthrough_enabled": control.get(
            "structured_button_passthrough_enabled",
            True,
        ),
        "wabis_priority_minutes": control.get("wabis_priority_minutes", 5),
        "has_previous_interaction": _has_previous_interaction(customer_phone),
    }
    meta.update(extract_media_hints())
    return meta


def _ai_routes_need_queue(route: str | None) -> bool:
    return route in {"ai", "catalog", "clarification", "escalation", "silent_wait"}


def _extract_unknown_product_candidate(message: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in str(message or ""))
    normalized = " ".join(cleaned.split())
    stopwords = {
        "available", "availability", "stock", "price", "rate", "details", "detail", "info", "more",
        "undo", "undu", "venam", "need", "want", "order", "delivery", "charge", "question", "pls",
        "please", "can", "get", "about", "help", "is", "are", "any", "do", "you", "have",
    }
    tokens = [token for token in normalized.split() if token not in stopwords]
    if not tokens:
        return ""
    candidate = " ".join(tokens[:3]).strip()
    if candidate in {"what", "which", "hello", "hi", "hey"}:
        return ""
    return candidate


def _log_silent_wait_gap(
    *,
    conversation_id: str,
    customer_phone: str,
    incoming_message: str,
    route_reason: str,
    decision: dict[str, Any] | None = None,
) -> str:
    understanding = (decision or {}).get("message_understanding") or {}
    gap_id = log_knowledge_gap(
        customer_phone,
        incoming_message,
        conversation_id,
        detected_intent=str((decision or {}).get("intent") or understanding.get("detected_intent") or ""),
        detected_product=str(understanding.get("detected_product") or (decision or {}).get("resolved_product_key") or ""),
        confidence=float(understanding.get("confidence") or 0.2),
        reason=route_reason,
        status="open",
    )
    candidate = str(understanding.get("unknown_product_candidate") or _extract_unknown_product_candidate(incoming_message) or "").strip()
    if candidate:
        try:
            log_missing_product(candidate, clarification=incoming_message[:200])
        except Exception as exc:
            logger.warning("Failed to log missing product candidate %s: %s", candidate, exc)
    return gap_id


def _store_generated_reply(
    conversation_id: str,
    customer_phone: str,
    reply_result: dict[str, Any],
    route: str,
    customer_name: str = "Customer",
    inbound_message: str = "",
    message_lock_id: str = "",
) -> dict[str, Any]:
    """Persist a generated reply in the audit tables and send it to WhatsApp."""
    reply_text = reply_result.get("reply_text") or ""
    intent = reply_result.get("intent", "unknown")
    should_escalate = bool(reply_result.get("should_escalate", False))
    image_urls = list(reply_result.get("image_urls") or [])
    media_mode = str(reply_result.get("media_mode") or ("image" if image_urls else "text"))

    if not reply_text:
        if message_lock_id:
            finish_message_owner(lock_id=message_lock_id, status="skipped", metadata={"reason": "empty_reply"})
        return {
            "status": "skipped",
            "reply_id": "",
            "intent": intent,
            "escalated": should_escalate,
            "route": route,
        }

    state_before = get_customer_state(customer_phone)
    normalized_reply_hash = reply_hash(reply_text)
    try:
        last_hash = str(state_before.get("last_ai_reply_hash") or "").strip()
        if last_hash and last_hash == normalized_reply_hash:
            logger.warning("[AI-RESPONSE-DEDUPE] %s duplicate reply suppressed", customer_phone)
            if message_lock_id:
                finish_message_owner(
                    lock_id=message_lock_id,
                    status="skipped",
                    metadata={"reason": "duplicate_ai_reply_hash"},
                )
            return {
                "status": "skipped",
                "reason": "duplicate_ai_reply_hash",
                "reply_id": "",
                "intent": intent,
                "escalated": should_escalate,
                "route": route,
                "reply_text": reply_text,
            }
    except Exception as exc:
        logger.warning("AI reply dedupe check failed for %s: %s", customer_phone, exc)

    send_result: dict[str, Any] = {
        "success": False,
        "message_id": "",
        "note": "NOT_SENT",
    }
    try:
        send_result = send_whatsapp_reply_with_fallback(
            phone_number=customer_phone,
            message_text=reply_text,
            conversation_id=conversation_id,
            reply_result=reply_result,
            customer_name=customer_name,
            media_urls=image_urls,
            media_caption=str(reply_result.get("media_caption") or ""),
            media_only=media_mode == "image_only",
        )
        if send_result.get("success"):
            if send_result.get("mode") == "template":
                logger.warning(
                    "[AI-RESPONSE-SENT] %s: template fallback=%s reply_text='%s...'",
                    customer_phone,
                    send_result.get("template_name"),
                    reply_text[:80],
                )
            else:
                logger.warning(
                    f"[AI-RESPONSE-SENT] {customer_phone}: reply_text='{reply_text[:80]}...' "
                    f"success={send_result.get('success')}"
                )
        else:
            logger.error(
                "[AI-RESPONSE-SEND-FAILED] %s: %s",
                customer_phone,
                send_result.get("error"),
            )
    except Exception as exc:
        logger.error(f"[AI-RESPONSE-SEND-FAILED] {customer_phone}: {exc}")
        send_result = {"success": False, "error": str(exc)}

    reply_id = str(uuid.uuid4())
    try:
        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO ai_outgoing_replies
            (id, conversation_id, customer_phone, reply_text, intent,
             escalated, send_status, message_mode, media_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reply_id,
                conversation_id,
                customer_phone,
                reply_text,
                intent,
                should_escalate,
                "sent" if send_result.get("success") else "failed",
                media_mode,
                json.dumps({"image_urls": image_urls}, ensure_ascii=False),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        if should_escalate:
            reason = reply_result.get("escalation_reason", "AI escalation")
            conn.execute(
                """
                INSERT INTO escalation_queue
                (id, customer_phone, reason, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    customer_phone,
                    reason,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

        conn.commit()
    except Exception as e:
        logger.error(f"[DB-ERROR] {e}")

    guard_action = str(send_result.get("mode") or "sent")
    guard_issues = list(send_result.get("issues_found") or [])
    try:
        record_ai_reply(
            customer_id=customer_phone,
            inbound_message=inbound_message,
            generated_reply=reply_text,
            final_reply=reply_text,
            reply_result=reply_result,
            guard_action=guard_action,
            issues_found=guard_issues,
            detected_intent=intent,
            active_product=str(reply_result.get("product_key") or ""),
            journey_stage=str((reply_result.get("message_understanding") or {}).get("scenario") or ""),
        )
    except Exception as exc:
        logger.warning("Failed to sync customer state after AI reply for %s: %s", customer_phone, exc)

    try:
        log_ai_response(
            phone=customer_phone,
            response_message=reply_text,
            owner="ai",
            active_flow="product_journey" if reply_result.get("product_key") else None,
            detected_intent=intent,
            customer_id=customer_phone,
            inbound_message=inbound_message,
            generated_reply=reply_text,
            final_reply=reply_text,
            guard_action=guard_action,
            issues_found=guard_issues,
            active_product=str(reply_result.get("product_key") or ""),
            journey_stage=str((reply_result.get("message_understanding") or {}).get("scenario") or ""),
            metadata={
                "route": route,
                "media_mode": media_mode,
                "image_urls": image_urls,
                "message_understanding": reply_result.get("message_understanding") or {},
                "prompt_trace": reply_result.get("prompt_trace") or {},
                "generated_response": reply_text,
            },
        )
    except Exception as exc:
        logger.warning("Failed to write AI audit response for %s: %s", customer_phone, exc)

    if message_lock_id:
        finish_message_owner(
            lock_id=message_lock_id,
            status="replied" if send_result.get("success") else "failed",
            reply_message_id=str(send_result.get("message_id") or ""),
            metadata={
                "route": route,
                "intent": intent,
                "send_mode": send_result.get("mode"),
                "issues_found": guard_issues,
            },
        )

    # Default: one inbound message gets one AI text reply. Extra CTA messages are
    # disabled unless a future deterministic handler explicitly opts in.
    extra_messages = []
    if reply_result.get("allow_extra_messages"):
        extra_messages = [
            str(item or "").strip()
            for item in list(reply_result.get("extra_messages") or [])
            if str(item or "").strip()
        ]
    for extra_text in extra_messages:
        try:
            extra_send = send_whatsapp_reply_with_fallback(
                phone_number=customer_phone,
                message_text=extra_text,
                conversation_id=conversation_id,
                reply_result={
                    "intent": f"{intent}_cta",
                    "message_understanding": reply_result.get("message_understanding") or {},
                },
                customer_name=customer_name,
            )
            conn = get_db_connection()
            conn.execute(
                """
                INSERT INTO ai_outgoing_replies
                (id, conversation_id, customer_phone, reply_text, intent,
                 escalated, send_status, message_mode, media_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    conversation_id,
                    customer_phone,
                    extra_text,
                    f"{intent}_cta",
                    0,
                    "sent" if extra_send.get("success") else "failed",
                    "text",
                    json.dumps({"image_urls": []}, ensure_ascii=False),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            conn.commit()
            conn.close()
            log_ai_response(
                phone=customer_phone,
                response_message=extra_text,
                owner="ai",
                active_flow="product_journey" if reply_result.get("product_key") else None,
                detected_intent=f"{intent}_cta",
                customer_id=customer_phone,
                inbound_message=inbound_message,
                generated_reply=extra_text,
                final_reply=extra_text,
                guard_action="sent",
                issues_found=[],
                active_product=str(reply_result.get("product_key") or ""),
                journey_stage=str((reply_result.get("message_understanding") or {}).get("scenario") or ""),
                metadata={"route": route, "generated_response": extra_text, "extra_message": True},
            )
        except Exception as exc:
            logger.warning("Failed to send/store extra AI CTA for %s: %s", customer_phone, exc)

    return {
        "status": "sent" if send_result.get("success") else "failed",
        "reply_id": reply_id,
        "intent": intent,
        "escalated": should_escalate,
        "route": route,
        "reply_text": reply_text,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Incoming Message Handler
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/incoming")
async def handle_wabis_incoming_message(
    background_tasks: BackgroundTasks,
    request: Request,
    payload_data: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """
    Handle incoming message from Wabis webhook.
    Stores message and triggers async AI reply generation.
    """
    try:
        # Log raw payload for debugging (truncated for safety)
        raw_payload_dict = dict(payload_data or {})
        try:
            raw_body = await request.body()
            logger.warning(f"Wabis incoming raw payload: {raw_body.decode('utf-8', errors='replace')[:500]}")
            if raw_body:
                try:
                    parsed_body = json.loads(raw_body.decode("utf-8"))
                    if isinstance(parsed_body, dict):
                        raw_payload_dict = parsed_body
                except Exception:
                    pass
        except Exception:
            pass
        payload = WabisIncomingMessage.model_validate(_coerce_wabis_payload(raw_payload_dict))
        logger.warning(f"Wabis incoming parsed fields: {payload.model_dump()}")  # noqa
        phone = payload.resolved_phone()
        conversation_id = payload.resolved_conversation_id()
        incoming_message = payload.resolved_message()
        message_id = str(uuid.uuid4())
        
        logger.warning(f"[PARSE] Resolved phone: '{phone}', msg: '{incoming_message[:30]}'")

        if not phone:
            logger.warning("Wabis webhook: no phone in payload %s", payload.model_dump())
            return {"status": "ignored", "reason": "no_phone"}

        payload_hash = stable_payload_hash(raw_payload_dict)
        event_id = normalize_event_id(raw_payload_dict, payload_hash)
        is_new_event = mark_processed_event(
            source="wabis",
            event_id=event_id,
            conversation_id=conversation_id,
            customer_phone=phone,
            event_type=str(payload.type or payload.message_type or ""),
            payload_hash=payload_hash,
        )
        if not is_new_event:
            return {"status": "ignored", "reason": "duplicate_event", "event_id": event_id}
        
        try:
            conn = get_db_connection()
            try:
                # Store incoming message in database
                logger.warning(f"[DB] Storing message for {phone}")
                conn.execute(
                    """
                    INSERT INTO ai_incoming_messages 
                    (id, conversation_id, customer_phone, message_type, body, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        message_id,
                        conversation_id,
                        phone,
                        payload.message_type,
                        incoming_message,
                        payload.timestamp or datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()
                logger.warning(f"[DB] Stored successfully")

                log_customer_message(
                    phone=phone,
                    message=incoming_message,
                    owner=(get_conversation_state(phone) or {}).get("owner"),
                    active_flow=(get_conversation_state(phone) or {}).get("flow_id"),
                    metadata={
                        "conversation_id": conversation_id,
                        "message_type": payload.message_type,
                        "raw_payload_type": payload.type,
                    },
                )
                
                # Get or create customer record
                customer = conn.execute(
                    "SELECT id, name FROM journey_customers WHERE phone = ? ORDER BY created_at DESC LIMIT 1",
                    (phone,),
                ).fetchone()
                
                customer_name = dict(customer)["name"] if customer else "Customer"
            finally:
                conn.close()
        except Exception as db_err:
            logger.error(f"[DB-ERROR] {db_err}")
            customer_name = "Customer"

        if _system_or_label_event(payload, incoming_message):
            log_ai_decision(
                conversation_id=conversation_id,
                customer_phone=phone,
                incoming_message=incoming_message,
                final_route_owner="ignored_system_event",
                metadata={"event_id": event_id, "payload_type": payload.type},
            )
            return {"status": "ignored", "reason": "system_or_label_event", "message_id": message_id}

        control = get_ai_control_settings()
        if incoming_message.strip() and not _structured_wabis_event(payload, incoming_message):
            stop_flag = _journey_stop_flag_for_customer_message(incoming_message)
            try:
                stopped_count = stop_customer_journeys_for_customer(
                    customer_phone=phone,
                    reason=f"customer_message:{incoming_message[:120]}",
                    stop_flag=stop_flag,
                )
                if stopped_count:
                    logger.warning(
                        "[JOURNEY-STOP] stopped %s active journey(s) for %s via %s",
                        stopped_count,
                        phone,
                        stop_flag,
                    )
            except Exception as exc:
                logger.warning("[JOURNEY-STOP] failed for %s: %s", phone, exc)
        meta = _message_meta(payload, incoming_message, phone, control=control)
        meta["event_id"] = event_id
        meta["incoming_message_id"] = message_id
        meta["payload_hash"] = payload_hash
        route_preview = route_message(phone, incoming_message, message_meta=meta)
        preview_route = route_preview.get("route")
        logger.warning("[MAIN] route preview for %s: %s (%s)", phone, preview_route, route_preview.get("reason"))

        if not _ai_routes_need_queue(preview_route):
            result = _generate_and_send_reply(
                conversation_id=conversation_id,
                customer_phone=phone,
                customer_name=customer_name,
                incoming_message=incoming_message,
                message_type=payload.type or "text",
                postback_id=payload.postback_id or payload.postbackid,
                reply_message_id=payload.reply_message_id,
                input_flow_id=payload.input_flow_id,
                message_meta_extra=meta,
            )
            return {
                "status": "received",
                "message_id": message_id,
                "reply_queued": False,
                "route": result.get("route") or preview_route,
                "result": result,
            }

        queue_result = enqueue_ai_reply_job(
            conversation_id=conversation_id,
            customer_phone=phone,
            customer_name=customer_name,
            source_message_id=message_id,
            incoming_message=incoming_message,
            message_type=payload.type or "text",
            metadata={
                "route_preview": route_preview,
                "event_id": event_id,
                "postback_id": payload.postback_id or payload.postbackid,
                "reply_message_id": payload.reply_message_id,
                "message_meta": meta,
            },
        )
        logger.warning("[MAIN] AI reply queued for %s: %s", phone, queue_result)
        
        return {
            "status": "received",
            "message_id": message_id,
            "reply_queued": True,
            "queue": queue_result,
        }
        
    except Exception as e:
        logger.error(f"Error handling Wabis incoming message: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


# ─────────────────────────────────────────────────────────────────────────────
# AI Reply Generation & Sending
# ─────────────────────────────────────────────────────────────────────────────

def _generate_and_send_reply(
    conversation_id: str,
    customer_phone: str,
    customer_name: str,
    incoming_message: str,
    message_type: str = "text",
    postback_id: str | None = None,
    reply_message_id: str | None = None,
    input_flow_id: str | None = None,
    message_meta_extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Route message to correct handler using unified conversation state.
    Corrected Phase 1A routing with knowledge gap capture.
    """
    logger.warning(f"[ROUTE-START] {customer_phone}: {incoming_message[:50]}")
    try:
        control = get_ai_control_settings()

        if not control.get("server_orchestration_enabled", True):
            fallback_enabled = bool(control.get("wabis_fallback_when_disabled", True))
            logger.warning(
                "[ORCHESTRATOR-OFF] %s: backend standing down; wabis_fallback=%s",
                customer_phone,
                fallback_enabled,
            )
            return {
                "status": "skipped",
                "reason": "server_orchestration_disabled",
                "route": "wabis_fallback" if fallback_enabled else "silent_audit",
            }

        if not control.get("ai_running", True):
            logger.warning(f"[AI-PAUSED] {customer_phone}: owner paused AI automation")
            return {"status": "paused", "reason": "owner_paused_ai", "route": "paused"}

        # Get current state BEFORE routing
        state_before = get_conversation_state(customer_phone)
        conversation_context = (
            state_before.get("context") or {}
            if state_before and state_before.get("flow_id") == "product_journey"
            else {}
        )
        customer_state = get_customer_state(customer_phone) or {}
        
        # Route message
        decision = route_message(
            customer_phone,
            incoming_message,
            message_meta={
                "message_type": message_type,
                "postback_id": postback_id,
                "provider_postback_id": postback_id,
                "reply_message_id": reply_message_id,
                "input_flow_id": input_flow_id,
                "structured_button_click": bool(
                    postback_id
                    or reply_message_id
                    or message_type == "postback"
                    or incoming_message.strip().lower().startswith("#button reply#")
                ),
                "flow_break_detection_enabled": control.get("flow_break_detection_enabled", True),
                "structured_button_passthrough_enabled": control.get(
                    "structured_button_passthrough_enabled",
                    True,
                ),
                "wabis_priority_minutes": control.get("wabis_priority_minutes", 5),
                "has_previous_interaction": _has_previous_interaction(customer_phone),
                **(message_meta_extra or {}),
            },
        )
        route = decision.get("route")
        lock_id = ""
        lock_key = str((message_meta_extra or {}).get("event_id") or (message_meta_extra or {}).get("incoming_message_id") or "").strip()
        if lock_key:
            lock_owner = "ai" if route in {"ai", "catalog", "clarification", "escalation"} else str(route or "unknown")
            lock = claim_message_owner(
                customer_id=customer_phone,
                incoming_message_id=lock_key,
                owner=lock_owner,
                conversation_id=conversation_id,
                metadata={
                    "route": route,
                    "reason": decision.get("reason"),
                    "incoming_message": incoming_message[:500],
                },
            )
            if not lock.get("claimed"):
                logger.warning(
                    "[MESSAGE-LOCK] %s event=%s already owned by %s/%s; skipping route=%s",
                    customer_phone,
                    lock_key,
                    lock.get("owner"),
                    lock.get("status"),
                    route,
                )
                return {
                    "status": "skipped",
                    "reason": "message_already_claimed",
                    "route": route,
                    "owner": lock.get("owner"),
                    "lock_status": lock.get("status"),
                }
            lock_id = str(lock.get("lock_id") or "")
        reply_context = dict(conversation_context or {})
        reply_context.update(
            {
                "language": customer_state.get("language"),
                "active_product": customer_state.get("active_product"),
                "latest_intent": customer_state.get("latest_intent"),
                "price_shared": customer_state.get("price_shared"),
                "quantity_selected": customer_state.get("quantity_selected"),
                "address_received": customer_state.get("address_received"),
                "pincode_received": customer_state.get("pincode_received"),
                "payment_claimed": customer_state.get("payment_claimed"),
                "payment_screenshot_received": customer_state.get("payment_screenshot_received"),
                "defer_intent": customer_state.get("defer_intent"),
                "followups_allowed": customer_state.get("followups_allowed"),
                "journey_stage": customer_state.get("journey_stage"),
            }
        )
        reply_context["message_meta"] = dict(message_meta_extra or {})
        if isinstance(decision.get("product_context"), dict):
            reply_context.update(decision["product_context"])
        if decision.get("resolved_product_key") and "product_key" not in reply_context:
            reply_context["product_key"] = decision["resolved_product_key"]
        if "product_key" not in reply_context:
            active_product = str((state_before or {}).get("active_product") or "").strip()
            if active_product:
                reply_context["product_key"] = active_product
        
        # Log decision
        log_routing_decision(customer_phone, incoming_message, state_before or {}, decision)
        
        logger.warning(f"[ROUTE-DECISION] {customer_phone} → {route} ({decision.get('reason')})")
        
        # If router says to set owner, do it NOW
        if "action_set_owner" in decision:
            action = decision["action_set_owner"]
            set_conversation_state(
                customer_phone,
                owner=action.get("owner"),
                owner_reason=action.get("reason"),
                flow_id=action.get("flow_id"),
                flow_step=action.get("flow_step"),
                expected_responses=action.get("expected_responses"),
                context=action.get("context"),
                timeout_minutes=action.get("timeout_minutes"),
            )

        if "action_merge_context" in decision:
            merge_conversation_context(customer_phone, decision["action_merge_context"])

        if "action_cancel_followups" in decision:
            cancel_action = decision["action_cancel_followups"] or {}
            stages = cancel_action.get("stages")
            cancel_product_followups(
                customer_phone,
                reason=str(cancel_action.get("reason") or "route_cancelled"),
                stages=set(stages) if isinstance(stages, (list, set, tuple)) else None,
            )

        if "action_schedule_latent_handoff" in decision:
            latent = decision["action_schedule_latent_handoff"] or {}
            queue_latent_handoff_followup(
                phone=customer_phone,
                product_key=latent.get("product_key"),
                detected_intent=str(latent.get("detected_intent") or ""),
                reply_style=str(latent.get("reply_style") or "english"),
                customer_reference=latent.get("customer_reference"),
                source_message=str(latent.get("source_message") or incoming_message),
                after_minutes=int(latent.get("after_minutes") or control.get("wabis_priority_minutes", 5)),
            )
        
        # ────────────────────────────────────────────────────────────────────────
        # ROUTE HANDLING
        # ────────────────────────────────────────────────────────────────────────
        
        # [1] HUMAN ONLY
        if route == "human_only":
            logger.info(f"[SKIP] {customer_phone} - human agent owns conversation")
            if lock_id:
                finish_message_owner(lock_id=lock_id, status="skipped", metadata={"reason": "human_only"})
            return {"status": "skipped", "reason": "human_only", "route": route}
        
        # [2] CAMPAIGN
        if route == "campaign":
            logger.info(f"[SKIP] {customer_phone} - campaign owns conversation")
            if lock_id:
                finish_message_owner(lock_id=lock_id, status="skipped", metadata={"reason": "campaign_owns"})
            return {"status": "skipped", "reason": "campaign_owns", "route": route}
        
        # [3] WABIS FLOW
        if route == "wabis":
            logger.info(f"[SKIP] {customer_phone} - Wabis bot owns conversation")
            if lock_id:
                finish_message_owner(lock_id=lock_id, status="skipped", metadata={"reason": "wabis_owns"})
            return {"status": "skipped", "reason": "wabis_owns", "route": route}
        
        # [4] ORDER TRACKING SYSTEM
        if route == "order_system":
            logger.info(f"[SKIP] {customer_phone} - Order tracking system")
            # TODO: Route to order tracking system
            if lock_id:
                finish_message_owner(lock_id=lock_id, status="skipped", metadata={"reason": "order_system"})
            return {"status": "skipped", "reason": "order_system", "route": route}
        
        # [5] ESCALATION
        if route == "escalation":
            logger.info(f"[ESCALATE] {customer_phone} - Complaint detected")
            reply_result = WabisReplyGenerator.generate_reply(
                incoming_message=incoming_message,
                customer_phone=customer_phone,
                customer_name=customer_name,
                conversation_id=conversation_id,
                context=reply_context,
            )
            if reply_result.get("reply_text"):
                result = _store_generated_reply(
                    conversation_id,
                    customer_phone,
                    reply_result,
                    route,
                    customer_name=customer_name,
                    inbound_message=incoming_message,
                    message_lock_id=lock_id,
                )
                result["status"] = "escalated"
                return result
            try:
                conn = get_db_connection()
                conn.execute(
                    """
                    INSERT INTO escalation_queue
                    (id, customer_phone, reason, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        customer_phone,
                        incoming_message[:100],
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                conn.commit()
            except Exception as e:
                logger.error(f"Failed to escalate: {e}")
            if lock_id:
                finish_message_owner(lock_id=lock_id, status="replied", metadata={"reason": "escalation_queue"})
            return {"status": "escalated", "reason": "complaint", "route": route}
        
        # [6] CATALOG SEARCH - NO AI
        if route == "catalog":
            logger.info(f"[CATALOG] {customer_phone} - Product search")
            reply_result = WabisReplyGenerator.generate_reply(
                incoming_message=incoming_message,
                customer_phone=customer_phone,
                customer_name=customer_name,
                conversation_id=conversation_id,
                context=reply_context,
            )

            if reply_result.get("suggested_action") == "wait_for_user" or not reply_result.get("reply_text"):
                gap_id = _log_silent_wait_gap(
                    conversation_id=conversation_id,
                    customer_phone=customer_phone,
                    incoming_message=incoming_message,
                    route_reason=str(reply_result.get("knowledge_gap_reason") or decision.get("reason") or "catalog_without_useful_reply"),
                    decision={**decision, "message_understanding": reply_result.get("message_understanding") or decision.get("message_understanding") or {}},
                )
                logger.warning(f"[CATALOG-SEARCH] {customer_phone}: query='{incoming_message[:50]}' (SILENT_WAIT)")
                if lock_id:
                    finish_message_owner(lock_id=lock_id, status="skipped", metadata={"reason": "silent_wait", "gap_id": gap_id})
                return {"status": "skipped", "reason": "silent_wait", "route": "silent_wait", "gap_id": gap_id}

            if reply_result.get("reply_text"):
                logger.warning(f"[CATALOG-REPLY] {customer_phone}: reply ready for catalog topic")
                return _store_generated_reply(
                    conversation_id,
                    customer_phone,
                    reply_result,
                    route,
                    customer_name=customer_name,
                    inbound_message=incoming_message,
                    message_lock_id=lock_id,
                )
            gap_id = _log_silent_wait_gap(
                conversation_id=conversation_id,
                customer_phone=customer_phone,
                incoming_message=incoming_message,
                route_reason="catalog_without_useful_reply",
                decision=decision,
            )
            if lock_id:
                finish_message_owner(lock_id=lock_id, status="skipped", metadata={"reason": "silent_wait", "gap_id": gap_id})
            return {"status": "skipped", "reason": "silent_wait", "route": "silent_wait", "gap_id": gap_id}
        
        # [7] SALES FLOW
        if route == "sales":
            logger.info(f"[SALES] {customer_phone} - Purchase intent")
            # TODO: Route to sales/cart system
            if lock_id:
                finish_message_owner(lock_id=lock_id, status="skipped", metadata={"reason": "sales_intent"})
            return {"status": "sales_intent", "route": route}
        
        # [8] FAQ
        if route == "faq":
            logger.info(f"[FAQ] {customer_phone} - FAQ question")
            # TODO: Implement FAQ knowledge base lookup
            if lock_id:
                finish_message_owner(lock_id=lock_id, status="skipped", metadata={"reason": "faq_lookup"})
            return {"status": "faq_lookup", "route": route}

        if route == "silent_wait":
            logger.info(f"[SILENT-WAIT] {customer_phone} - no useful AI reply")
            gap_id = _log_silent_wait_gap(
                conversation_id=conversation_id,
                customer_phone=customer_phone,
                incoming_message=incoming_message,
                route_reason=str(decision.get("reason") or "low_confidence_unclear_message"),
                decision=decision,
            )
            if lock_id:
                finish_message_owner(lock_id=lock_id, status="skipped", metadata={"reason": "silent_wait", "gap_id": gap_id})
            return {"status": "skipped", "reason": "silent_wait", "route": route, "gap_id": gap_id}

        # [9] CLARIFICATION - Knowledge gap capture
        if route == "clarification":
            logger.info(f"[CLARIFICATION] {customer_phone} - Intent unclear")
            gap_id = log_knowledge_gap(
                customer_phone,
                incoming_message,
                conversation_id,
                detected_intent=str(decision.get("intent") or ""),
                detected_product=str((decision.get("message_understanding") or {}).get("detected_product") or ""),
                confidence=float(((decision.get("message_understanding") or {}).get("confidence") or 0.2)),
                reason=str(decision.get("reason") or "clarification"),
                status="open",
            )
            fallback_reply = WabisReplyGenerator.generate_reply(
                incoming_message=incoming_message,
                customer_phone=customer_phone,
                customer_name=customer_name,
                conversation_id=conversation_id,
                context=reply_context,
            )
            logger.warning(f"[CLARIFICATION-GAP] {customer_phone}: gap_id={gap_id}, message='{incoming_message[:50]}'")
            if fallback_reply.get("suggested_action") == "wait_for_user" or not fallback_reply.get("reply_text"):
                if lock_id:
                    finish_message_owner(lock_id=lock_id, status="skipped", metadata={"reason": "silent_wait", "gap_id": gap_id})
                return {"status": "skipped", "reason": "silent_wait", "route": "silent_wait", "gap_id": gap_id}
            result = _store_generated_reply(
                conversation_id,
                customer_phone,
                fallback_reply,
                route,
                customer_name=customer_name,
                inbound_message=incoming_message,
                message_lock_id=lock_id,
            )
            result["gap_id"] = gap_id
            return result
        
        # [10] AI - ONLY with knowledge grounding
        if route == "ai":
            logger.info(f"[AI] {customer_phone} - AI with knowledge")
            
            # Generate AI reply
            reply_result = WabisReplyGenerator.generate_reply(
                incoming_message=incoming_message,
                customer_phone=customer_phone,
                customer_name=customer_name,
                conversation_id=conversation_id,
                context=reply_context,
            )
            
            reply_text = reply_result.get("reply_text", "")
            intent = reply_result.get("intent", "unknown")
            should_escalate = reply_result.get("should_escalate", False)
            
            logger.warning(f"[AI-REPLY] Generated: intent={intent}, text_len={len(reply_text)}")

            if reply_result.get("suggested_action") == "wait_for_user" or not reply_text:
                gap_id = _log_silent_wait_gap(
                    conversation_id=conversation_id,
                    customer_phone=customer_phone,
                    incoming_message=incoming_message,
                    route_reason=str(reply_result.get("knowledge_gap_reason") or decision.get("reason") or "low_confidence_unclear_message"),
                    decision={**decision, "message_understanding": reply_result.get("message_understanding") or decision.get("message_understanding") or {}},
                )
                if lock_id:
                    finish_message_owner(lock_id=lock_id, status="skipped", metadata={"reason": "silent_wait", "gap_id": gap_id, "intent": intent})
                return {
                    "status": "skipped",
                    "reason": "silent_wait",
                    "route": "silent_wait",
                    "gap_id": gap_id,
                    "intent": intent,
                }
            
            # Augment with knowledge if flagged
            if decision.get("require_knowledge"):
                # TODO: Add knowledge context to prompt
                pass
            
            # Send the generated reply through the Wabis API and audit the result.
            return _store_generated_reply(
                conversation_id,
                customer_phone,
                reply_result,
                route,
                customer_name=customer_name,
                inbound_message=incoming_message,
                message_lock_id=lock_id,
            )
        
        # Unknown route
        logger.error(f"[UNKNOWN-ROUTE] {customer_phone} → {route}")
        if lock_id:
            finish_message_owner(lock_id=lock_id, status="failed", metadata={"reason": f"unknown_route:{route}"})
        return {
            "status": "error",
            "error": f"Unknown route: {route}",
        }
        
    except Exception as e:
        logger.error(f"[ERROR] {customer_phone}: {e}")
        return {"status": "error", "error": str(e)}


@router.post("/reply-async")
async def send_ai_reply_async(
    payload: WabisReplyRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """
    Manually trigger AI reply for a message (sync request, async execution).
    Useful for testing or triggering replies for existing conversations.
    """
    background_tasks.add_task(
        _generate_and_send_reply,
        conversation_id=payload.conversation_id,
        customer_phone=payload.customer_phone,
        customer_name=payload.customer_name,
        incoming_message=payload.incoming_message,
        message_type="text",
    )
    
    return {
        "status": "queued",
        "message": "AI reply generation queued",
        "customer_phone": payload.customer_phone,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Status & Monitoring
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/status")
def get_wabis_integration_status() -> dict[str, Any]:
    """Get status of Wabis AI integration"""
    try:
        conn = get_db_connection()
        try:
            incoming_count = conn.execute(
                "SELECT COUNT(*) as count FROM ai_incoming_messages"
            ).fetchone()["count"]
            
            outgoing_count = conn.execute(
                "SELECT COUNT(*) as count FROM ai_outgoing_replies"
            ).fetchone()["count"]
            
            escalation_count = conn.execute(
                "SELECT COUNT(*) as count FROM escalation_queue"
            ).fetchone()["count"]
            
            return {
                "status": "active",
                "incoming_messages": incoming_count,
                "outgoing_replies": outgoing_count,
                "escalations_pending": escalation_count,
            }
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Error getting Wabis status: {e}")
        return {
            "status": "error",
            "error": str(e),
        }
