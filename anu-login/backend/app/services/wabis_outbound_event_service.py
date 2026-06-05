from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.ai.audit_logger import log_audit_event
from app.ai.conversation_state_manager import reset_conversation_state, set_conversation_state
from app.runtime_db import ensure_runtime_tables, get_db_connection
from app.services.human_loop_rule_service import human_inactivity_delay_seconds
from app.services.product_followup_service import cancel_product_followups


STATUS_VALUES = {"accepted", "sent", "delivered", "read", "failed", "undelivered", "unsupported"}
HUMAN_ACTOR_VALUES = {"admin", "agent", "human", "team_member", "operator", "live_chat"}
CONTROL_EVENT_TYPES = {
    "conversation.admin_reply.sent",
    "conversation.agent_assigned",
    "conversation.bot_paused",
    "conversation.archived",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_hash(payload: Any) -> str:
    raw = json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)


def _first_text(payload: dict[str, Any], keys: tuple[str, ...]) -> str:
    for node in _walk(payload):
        for key in keys:
            value = node.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, dict):
                body = value.get("body") or value.get("text")
                if isinstance(body, str) and body.strip():
                    return body.strip()
    return ""


def _first_phone(payload: dict[str, Any]) -> str:
    for node in _walk(payload):
        for key in (
            "customer_phone",
            "phone",
            "wa_id",
            "chat_id",
            "subscriber_phone",
            "recipient",
            "recipient_id",
            "to",
        ):
            value = str(node.get(key) or "").strip()
            digits = "".join(ch for ch in value if ch.isdigit())
            if len(digits) >= 10:
                return digits
    return ""


def _first_id(payload: dict[str, Any], keys: tuple[str, ...]) -> str:
    for node in _walk(payload):
        for key in keys:
            value = str(node.get(key) or "").strip()
            if value:
                return value[:240]
    return ""


def _flatten_haystack(payload: dict[str, Any]) -> str:
    parts: list[str] = []
    for node in _walk(payload):
        for key, value in node.items():
            if isinstance(value, (str, int, float, bool)):
                parts.append(f"{key}:{value}")
    return " ".join(parts).lower()


def _first_status(payload: dict[str, Any]) -> str:
    for node in _walk(payload):
        for key in ("status", "message_status", "delivery_status"):
            value = str(node.get(key) or "").strip().lower()
            if value in STATUS_VALUES:
                return value
    return ""


def _originator_from_payload(payload: dict[str, Any], haystack: str) -> str:
    for node in _walk(payload):
        for key in ("actor_type", "sender_type", "from_type", "originator_type", "source_type", "role"):
            value = str(node.get(key) or "").strip().lower()
            if value in HUMAN_ACTOR_VALUES:
                return "human"
            if value in {"bot", "automation", "system", "api"}:
                return value
    if any(token in haystack for token in HUMAN_ACTOR_VALUES):
        return "human"
    if any(token in haystack for token in ("automation", "bot", "template")):
        return "automation"
    return "status"


def ensure_wabis_outbound_tables() -> None:
    ensure_runtime_tables()
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS wabis_webhook_deliveries (
                id TEXT PRIMARY KEY,
                source_system TEXT NOT NULL DEFAULT 'wabis',
                delivery_id TEXT,
                event_hash TEXT NOT NULL UNIQUE,
                event_type TEXT,
                customer_phone TEXT,
                conversation_id TEXT,
                auth_verified INTEGER NOT NULL DEFAULT 0,
                headers_json TEXT NOT NULL DEFAULT '{}',
                raw_payload_json TEXT NOT NULL DEFAULT '{}',
                normalized_json TEXT NOT NULL DEFAULT '{}',
                processing_status TEXT NOT NULL DEFAULT 'processed',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS wabis_outbound_messages (
                id TEXT PRIMARY KEY,
                message_id TEXT,
                conversation_id TEXT,
                customer_phone TEXT NOT NULL,
                originator_type TEXT NOT NULL,
                event_type TEXT NOT NULL,
                message_text TEXT,
                delivery_status TEXT,
                actor_id TEXT,
                raw_delivery_id TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS wabis_message_status_events (
                id TEXT PRIMARY KEY,
                message_id TEXT,
                customer_phone TEXT,
                conversation_id TEXT,
                delivery_status TEXT NOT NULL,
                raw_delivery_id TEXT,
                metadata_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS wabis_human_locks (
                id TEXT PRIMARY KEY,
                customer_phone TEXT NOT NULL,
                conversation_id TEXT,
                event_type TEXT NOT NULL,
                lock_reason TEXT NOT NULL,
                lock_until TEXT NOT NULL,
                raw_delivery_id TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_wabis_outbound_phone ON wabis_outbound_messages(customer_phone, created_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_wabis_status_msg ON wabis_message_status_events(message_id, created_at DESC)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_wabis_human_locks_phone ON wabis_human_locks(customer_phone, created_at DESC)")
        connection.commit()


def normalize_wabis_outbound_payload(payload: dict[str, Any]) -> dict[str, Any]:
    haystack = _flatten_haystack(payload)
    phone = _first_phone(payload)
    conversation_id = _first_id(payload, ("conversation_id", "conversationId", "thread_id", "threadId", "chat_id", "subscriber_id"))
    message_id = _first_id(payload, ("message_id", "messageId", "wamid", "wa_message_id", "id"))
    delivery_id = _first_id(payload, ("delivery_id", "deliveryId", "event_id", "eventId", "webhook_id", "webhookId"))
    actor_id = _first_id(payload, ("agent_id", "agentId", "admin_id", "adminId", "team_member_id", "teamMemberId", "actor_id", "actorId"))
    message_text = _first_text(payload, ("message", "text", "body", "reply", "caption"))

    status = _first_status(payload)
    originator_type = _originator_from_payload(payload, haystack)

    event_type = "conversation.status"
    if any(token in haystack for token in ("pause", "bot_paused", "pause_bot", "bot replies paused")):
        event_type = "conversation.bot_paused"
    elif any(token in haystack for token in ("resume", "bot_resumed", "resume_bot", "bot replies resumed")):
        event_type = "conversation.bot_resumed"
    elif any(token in haystack for token in ("assign", "assigned_agent", "agent_assigned", "team_member")):
        event_type = "conversation.agent_assigned"
    elif "archive" in haystack:
        event_type = "conversation.archived"
    elif originator_type == "human" and any(token in haystack for token in ("outbound", "sent", "reply", "message", "admin_reply")):
        event_type = "conversation.admin_reply.sent"
    elif status:
        event_type = f"conversation.message.{status}"
    elif message_text and any(token in haystack for token in ("outbound", "business", "from_business")):
        event_type = "conversation.admin_reply.sent"
        originator_type = "human"
    elif event_type == "conversation.bot_resumed" and originator_type == "status":
        originator_type = "system"

    return {
        "event_type": event_type,
        "originator_type": originator_type,
        "customer_phone": phone,
        "conversation_id": conversation_id or phone,
        "message_id": message_id,
        "delivery_id": delivery_id,
        "actor_id": actor_id,
        "message_text": message_text,
        "delivery_status": status,
    }


def _cancel_pending_ai_jobs(phone: str, reason: str) -> int:
    if not phone:
        return 0
    now = _now()
    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE ai_reply_jobs
            SET status = 'cancelled',
                skipped_reason = ?,
                updated_at = ?
            WHERE customer_phone = ?
              AND status IN ('pending', 'learning', 'ready')
            """,
            (reason, now, phone),
        )
        connection.commit()
        return int(cursor.rowcount or 0)


def _project_human_event(normalized: dict[str, Any], raw_delivery_id: str) -> dict[str, Any]:
    event_type = normalized["event_type"]
    phone = normalized.get("customer_phone") or ""
    if not phone:
        return {"lock_applied": False, "cancelled_jobs": 0, "reason": "no_customer_phone"}

    cancelled = 0
    cancelled_followups = 0
    if event_type in CONTROL_EVENT_TYPES:
        cancelled = _cancel_pending_ai_jobs(phone, "cancelled_by_human_outbound_event")
        try:
            cancelled_followups = cancel_product_followups(phone, reason="cancelled_by_human_outbound_event")
        except Exception:
            cancelled_followups = 0
        delay_seconds = human_inactivity_delay_seconds()
        lock_until = (datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)).isoformat()
        set_conversation_state(
            phone,
            owner="human",
            owner_reason=event_type,
            flow_id="human_review",
            flow_step="human_replied" if event_type == "conversation.admin_reply.sent" else event_type.rsplit(".", 1)[-1],
            context={
                "human_outbound_observed": True,
                "wabis_event_type": event_type,
                "raw_delivery_id": raw_delivery_id,
                "message_id": normalized.get("message_id") or "",
                "actor_id": normalized.get("actor_id") or "",
                "last_human_message": normalized.get("message_text") or "",
                "human_lock_until": lock_until,
                "human_inactivity_seconds": delay_seconds,
                "followups_allowed": False,
                "journey_stage": "human_review",
            },
        )
        try:
            with get_db_connection() as connection:
                connection.execute(
                    """
                    INSERT INTO wabis_human_locks
                    (id, customer_phone, conversation_id, event_type, lock_reason,
                     lock_until, raw_delivery_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        phone,
                        normalized.get("conversation_id") or phone,
                        event_type,
                        "human_outbound_observed",
                        lock_until,
                        raw_delivery_id,
                        _now(),
                    ),
                )
                connection.commit()
        except Exception:
            pass
        log_audit_event(
            phone=phone,
            direction="outbound",
            source="human",
            message=normalized.get("message_text") or "",
            owner_after="human",
            active_flow="human_review",
            route_decision=event_type,
            reason="wabis_human_outbound_event",
            metadata={
                "normalized": normalized,
                "raw_delivery_id": raw_delivery_id,
                "cancelled_ai_jobs": cancelled,
                "cancelled_followups": cancelled_followups,
                "human_lock_until": lock_until,
            },
        )
        return {
            "lock_applied": True,
            "cancelled_jobs": cancelled,
            "cancelled_followups": cancelled_followups,
            "human_lock_until": lock_until,
        }
    elif event_type == "conversation.bot_resumed":
        reset_conversation_state(phone)
        log_audit_event(
            phone=phone,
            direction="system",
            source="wabis",
            message="Bot resumed",
            owner_after="ai",
            route_decision=event_type,
            reason="wabis_bot_resumed",
            metadata={"normalized": normalized, "raw_delivery_id": raw_delivery_id},
        )
        return {"lock_applied": False, "released": True, "cancelled_jobs": 0}
    return {"lock_applied": False, "cancelled_jobs": 0, "status_only": event_type.startswith("conversation.message.")}


def ingest_wabis_outbound_event(
    *,
    payload: dict[str, Any],
    headers: dict[str, Any] | None = None,
    auth_verified: bool = False,
) -> dict[str, Any]:
    ensure_wabis_outbound_tables()
    normalized = normalize_wabis_outbound_payload(payload)
    event_hash = _json_hash({"payload": payload, "source": "wabis_outbound"})
    now = _now()
    delivery_id = normalized.get("delivery_id") or event_hash
    raw_delivery_id = str(uuid.uuid4())

    with get_db_connection() as connection:
        try:
            connection.execute(
                """
                INSERT INTO wabis_webhook_deliveries
                (id, source_system, delivery_id, event_hash, event_type, customer_phone,
                 conversation_id, auth_verified, headers_json, raw_payload_json,
                 normalized_json, processing_status, created_at, updated_at)
                VALUES (?, 'wabis', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'processed', ?, ?)
                """,
                (
                    raw_delivery_id,
                    delivery_id,
                    event_hash,
                    normalized.get("event_type"),
                    normalized.get("customer_phone"),
                    normalized.get("conversation_id"),
                    1 if auth_verified else 0,
                    json.dumps(headers or {}, ensure_ascii=False, default=str),
                    json.dumps(payload or {}, ensure_ascii=False, default=str),
                    json.dumps(normalized, ensure_ascii=False, default=str),
                    now,
                    now,
                ),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                row = connection.execute(
                    "SELECT id, normalized_json FROM wabis_webhook_deliveries WHERE event_hash = ? LIMIT 1",
                    (event_hash,),
                ).fetchone()
                return {
                    "status": "duplicate",
                    "delivery_id": row["id"] if row else "",
                    "normalized": json.loads(row["normalized_json"]) if row and row["normalized_json"] else normalized,
                }
            raise

        if normalized.get("originator_type") == "human":
            connection.execute(
                """
                INSERT INTO wabis_outbound_messages
                (id, message_id, conversation_id, customer_phone, originator_type,
                 event_type, message_text, delivery_status, actor_id, raw_delivery_id,
                 metadata_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    normalized.get("message_id"),
                    normalized.get("conversation_id"),
                    normalized.get("customer_phone") or "",
                    normalized.get("originator_type") or "human",
                    normalized.get("event_type"),
                    normalized.get("message_text"),
                    normalized.get("delivery_status"),
                    normalized.get("actor_id"),
                    raw_delivery_id,
                    json.dumps(normalized, ensure_ascii=False),
                    now,
                    now,
                ),
            )
        if normalized.get("delivery_status"):
            connection.execute(
                """
                INSERT INTO wabis_message_status_events
                (id, message_id, customer_phone, conversation_id, delivery_status,
                 raw_delivery_id, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    normalized.get("message_id"),
                    normalized.get("customer_phone"),
                    normalized.get("conversation_id"),
                    normalized.get("delivery_status"),
                    raw_delivery_id,
                    json.dumps(normalized, ensure_ascii=False),
                    now,
                ),
            )
        connection.commit()

    projection = _project_human_event(normalized, raw_delivery_id)
    return {
        "status": "processed",
        "delivery_id": raw_delivery_id,
        "normalized": normalized,
        "projection": projection,
    }
