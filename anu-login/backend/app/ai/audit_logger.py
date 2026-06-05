"""Audit Logger - Comprehensive conversation history

Logs every message, routing decision, and state change.
Used for debugging, compliance, and daily reports.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def _table_exists(connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _phone_variants(phone: str) -> list[str]:
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    variants: list[str] = []

    if digits:
        variants.append(digits)
        if len(digits) == 10:
            variants.extend([f"91{digits}", f"+91{digits}"])
        elif len(digits) == 12 and digits.startswith("91"):
            local = digits[2:]
            variants.extend([local, f"+91{local}"])

    if phone and phone not in variants:
        variants.append(phone)

    # Preserve order but drop duplicates.
    seen: set[str] = set()
    unique: list[str] = []
    for variant in variants:
        if variant in seen:
            continue
        seen.add(variant)
        unique.append(variant)
    return unique


def _safe_json_loads(raw: Optional[str]) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _append_event(
    events: list[dict[str, Any]],
    *,
    timestamp: Optional[str],
    direction: str,
    source: str,
    message: Optional[str] = None,
    owner_before: Optional[str] = None,
    owner_after: Optional[str] = None,
    active_flow: Optional[str] = None,
    detected_intent: Optional[str] = None,
    route_decision: Optional[str] = None,
    reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    events.append(
        {
            "timestamp": timestamp,
            "direction": direction,
            "source": source,
            "message": message,
            "owner_before": owner_before,
            "owner_after": owner_after,
            "active_flow": active_flow,
            "detected_intent": detected_intent,
            "route_decision": route_decision,
            "reason": reason,
            "metadata": metadata or {},
        }
    )


def log_audit_event(
    phone: str,
    direction: str,  # "inbound" or "outbound"
    source: str,     # "customer" | "wabis" | "ai" | "system" | "human" | "campaign"
    message: Optional[str] = None,
    owner_before: Optional[str] = None,
    owner_after: Optional[str] = None,
    active_flow: Optional[str] = None,
    detected_intent: Optional[str] = None,
    route_decision: Optional[str] = None,
    reason: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Log a conversation event.
    
    Args:
        phone: Customer phone number
        direction: "inbound" (from customer/wabis) or "outbound" (to customer/wabis)
        source: Who sent the message
        message: The actual message content
        owner_before: Who owned conversation before this event
        owner_after: Who owns conversation after this event
        active_flow: Which flow is active
        detected_intent: What intent was detected
        route_decision: Where message was routed
        reason: Why the decision was made
        metadata: Additional context (dict)
    
    Returns:
        Event ID
    """
    from app.storage import get_db_connection
    
    try:
        conn = get_db_connection()
        event_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        conn.execute(
            """
            INSERT INTO conversation_audit_log
            (id, created_at, phone, direction, source, message, owner_before, owner_after,
             active_flow, detected_intent, route_decision, reason, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event_id,
                now,
                phone,
                direction,
                source,
                message,
                owner_before,
                owner_after,
                active_flow,
                detected_intent,
                route_decision,
                reason,
                metadata_json,
            ),
        )
        conn.commit()
        
        logger.debug(f"[AUDIT] {event_id}: {phone} | {direction} | {source} | {route_decision or reason}")
        return event_id
        
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")
        return ""


def log_customer_message(
    phone: str,
    message: str,
    owner: Optional[str] = None,
    active_flow: Optional[str] = None,
    detected_intent: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Log incoming message from customer"""
    return log_audit_event(
        phone=phone,
        direction="inbound",
        source="customer",
        message=message,
        owner_before=owner,
        active_flow=active_flow,
        detected_intent=detected_intent,
        metadata=metadata,
    )


def log_routing_decision(
    phone: str,
    owner_before: str,
    owner_after: str,
    route_decision: str,
    reason: str,
    active_flow: Optional[str] = None,
    detected_intent: Optional[str] = None,
    message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Log a routing decision (where message goes)"""
    return log_audit_event(
        phone=phone,
        direction="inbound",
        source="system",
        message=message,
        owner_before=owner_before,
        owner_after=owner_after,
        active_flow=active_flow,
        detected_intent=detected_intent,
        route_decision=route_decision,
        reason=reason,
        metadata=metadata,
    )


def log_ai_response(
    phone: str,
    response_message: str,
    owner: str,
    active_flow: Optional[str] = None,
    detected_intent: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    customer_id: Optional[str] = None,
    inbound_message: Optional[str] = None,
    generated_reply: Optional[str] = None,
    final_reply: Optional[str] = None,
    guard_action: Optional[str] = None,
    issues_found: Optional[list[str]] = None,
    active_product: Optional[str] = None,
    journey_stage: Optional[str] = None,
) -> str:
    """Log AI-generated response sent to customer"""
    return log_audit_event(
        phone=phone,
        direction="outbound",
        source="ai",
        message=response_message,
        owner_after=owner,
        active_flow=active_flow,
        detected_intent=detected_intent,
        reason="ai_response",
        metadata={
            **(metadata or {}),
            "customer_id": customer_id or phone,
            "inbound_message": inbound_message,
            "generated_reply": generated_reply or response_message,
            "final_reply": final_reply or response_message,
            "guard_action": guard_action,
            "issues_found": issues_found or [],
            "active_product": active_product,
            "journey_stage": journey_stage,
        },
    )


def reserve_ai_outgoing_reply(
    *,
    conversation_id: str,
    customer_phone: str,
    reply_text: str,
    intent: str,
    escalated: bool = False,
    message_mode: str = "text",
    media_urls: Optional[list[str]] = None,
    send_status: str = "pending",
) -> str:
    """Create an AI reply row before sending so the audit survives send-time failures."""
    from app.storage import get_db_connection

    try:
        reply_id = str(uuid.uuid4())
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
                int(bool(escalated)),
                send_status,
                message_mode,
                json.dumps({"image_urls": media_urls or []}, ensure_ascii=False),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return reply_id
    except Exception as exc:
        logger.warning("Failed to reserve AI outgoing reply for %s: %s", customer_phone, exc)
        return ""


def update_ai_outgoing_reply_status(
    reply_id: str,
    *,
    send_status: str,
) -> None:
    """Update a reserved AI reply row after the Wabis send attempt completes."""
    if not reply_id:
        return
    from app.storage import get_db_connection

    try:
        conn = get_db_connection()
        conn.execute(
            """
            UPDATE ai_outgoing_replies
            SET send_status = ?
            WHERE id = ?
            """,
            (send_status, reply_id),
        )
        conn.commit()
    except Exception as exc:
        logger.warning("Failed to update AI outgoing reply %s status to %s: %s", reply_id, send_status, exc)


def log_flow_transition(
    phone: str,
    owner_before: str,
    owner_after: str,
    flow_before: Optional[str] = None,
    flow_after: Optional[str] = None,
    reason: str = "flow_transition",
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Log a flow state change"""
    return log_audit_event(
        phone=phone,
        direction="inbound",
        source="system",
        owner_before=owner_before,
        owner_after=owner_after,
        active_flow=flow_after,
        route_decision="flow_transition",
        reason=reason,
        metadata={
            **(metadata or {}),
            "flow_before": flow_before,
            "flow_after": flow_after,
        },
    )


def log_wabis_response(
    phone: str,
    message: str,
    flow: Optional[str] = None,
    step: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Log Wabis bot response sent to customer"""
    return log_audit_event(
        phone=phone,
        direction="outbound",
        source="wabis",
        message=message,
        owner_after="wabis",
        active_flow=flow,
        reason="wabis_response",
        metadata={
            **(metadata or {}),
            "flow_step": step,
        },
    )


def get_conversation_history(
    phone: str,
    limit: int = 100,
) -> list[Dict[str, Any]]:
    """
    Get conversation history for a phone number.
    
    Returns events in chronological order (oldest first).
    """
    from app.storage import get_db_connection
    
    try:
        conn = get_db_connection()
        events: list[dict[str, Any]] = []
        variants = _phone_variants(phone)
        like_patterns = [f"%{variant}%" for variant in variants] or [f"%{phone}%"]

        def _where_like(column: str) -> tuple[str, tuple[str, ...]]:
            clause = " OR ".join([f"COALESCE({column}, '') LIKE ?" for _ in like_patterns])
            return clause, tuple(like_patterns)

        def _add_query_rows(
            query: str,
            params: tuple[Any, ...],
            *,
            default_source: str,
            default_direction: str,
            source_table: str,
            row_to_event,
        ) -> None:
            rows = conn.execute(query, params).fetchall()
            for row in rows:
                event = row_to_event(dict(row))
                if not event:
                    continue
                event.setdefault("source", default_source)
                event.setdefault("direction", default_direction)
                event.setdefault("metadata", {})
                event["metadata"] = {
                    **event["metadata"],
                    "source_table": source_table,
                }
                _append_event(events, **event)

        audit_rows = []
        if _table_exists(conn, "conversation_audit_log"):
            audit_rows = conn.execute(
                """
                SELECT
                    created_at, direction, source, message, owner_before, owner_after,
                    active_flow, detected_intent, route_decision, reason, metadata_json
                FROM conversation_audit_log
                WHERE """ + " OR ".join(["COALESCE(phone, '') LIKE ?" for _ in like_patterns]) + """
                ORDER BY created_at ASC
                LIMIT ?
                """,
                (*like_patterns, limit),
            ).fetchall()

        if audit_rows:
            for row in audit_rows:
                metadata = _safe_json_loads(row["metadata_json"])
                _append_event(
                    events,
                    timestamp=row["created_at"],
                    direction=row["direction"],
                    source=row["source"],
                    message=row["message"],
                    owner_before=row["owner_before"],
                    owner_after=row["owner_after"],
                    active_flow=row["active_flow"],
                    detected_intent=row["detected_intent"],
                    route_decision=row["route_decision"],
                    reason=row["reason"],
                    metadata={
                        **metadata,
                        "source_table": "conversation_audit_log",
                    },
                )
        else:
            # Legacy / fallback timeline for deployments that only persist into
            # the older tables.
            if _table_exists(conn, "ai_incoming_messages"):
                clause, params = _where_like("customer_phone")
                _add_query_rows(
                    f"""
                    SELECT
                        created_at, conversation_id, customer_phone, message_type, body
                    FROM ai_incoming_messages
                    WHERE {clause}
                    ORDER BY created_at ASC
                    LIMIT ?
                    """,
                    (*params, limit),
                    default_source="customer",
                    default_direction="inbound",
                    source_table="ai_incoming_messages",
                    row_to_event=lambda row: {
                        "timestamp": row["created_at"],
                        "source": "customer",
                        "direction": "inbound",
                        "message": row["body"],
                        "metadata": {
                            "conversation_id": row["conversation_id"],
                            "message_type": row["message_type"],
                        },
                    },
                )

            if _table_exists(conn, "ai_outgoing_replies"):
                clause, params = _where_like("customer_phone")
                _add_query_rows(
                    f"""
                    SELECT
                        created_at, conversation_id, customer_phone, reply_text, intent, escalated, send_status
                    FROM ai_outgoing_replies
                    WHERE {clause}
                    ORDER BY created_at ASC
                    LIMIT ?
                    """,
                    (*params, limit),
                    default_source="ai",
                    default_direction="outbound",
                    source_table="ai_outgoing_replies",
                    row_to_event=lambda row: {
                        "timestamp": row["created_at"],
                        "source": "ai",
                        "direction": "outbound",
                        "message": row["reply_text"],
                        "active_flow": "product_journey" if str(row["conversation_id"]).startswith("product_followup:") else None,
                        "detected_intent": row["intent"],
                        "route_decision": row["send_status"],
                        "metadata": {
                            "conversation_id": row["conversation_id"],
                            "escalated": bool(row["escalated"]),
                        },
                    },
                )

            if _table_exists(conn, "flow_audit"):
                clause, params = _where_like("phone")
                _add_query_rows(
                    f"""
                    SELECT
                        timestamp, flow_name, abandonment_reason, expected_options,
                        received_message, final_route
                    FROM flow_audit
                    WHERE {clause}
                    ORDER BY timestamp ASC
                    LIMIT ?
                    """,
                    (*params, limit),
                    default_source="system",
                    default_direction="inbound",
                    source_table="flow_audit",
                    row_to_event=lambda row: {
                        "timestamp": row["timestamp"],
                        "source": "system",
                        "direction": "inbound",
                        "message": row["received_message"],
                        "active_flow": row["flow_name"],
                        "route_decision": row["final_route"],
                        "reason": row["abandonment_reason"],
                        "metadata": {
                            "expected_options": row["expected_options"],
                        },
                    },
                )

            if _table_exists(conn, "routing_log"):
                clause, params = _where_like("phone")
                _add_query_rows(
                    f"""
                    SELECT
                        timestamp, phone, message, owner_before, route_taken, context
                    FROM routing_log
                    WHERE {clause}
                    ORDER BY timestamp ASC
                    LIMIT ?
                    """,
                    (*params, limit),
                    default_source="system",
                    default_direction="inbound",
                    source_table="routing_log",
                    row_to_event=lambda row: {
                        "timestamp": row["timestamp"],
                        "source": "system",
                        "direction": "inbound",
                        "message": row["message"],
                        "owner_before": row["owner_before"],
                        "route_decision": row["route_taken"],
                        "metadata": {
                            "context": _safe_json_loads(row["context"]),
                        },
                    },
                )

            if _table_exists(conn, "product_journey_followups"):
                clause, params = _where_like("phone")
                _add_query_rows(
                    f"""
                    SELECT
                        scheduled_at, sent_at, phone, product_key, scenario, reply_style,
                        customer_reference, followup_stage, sent, send_status, reply_text, context_json
                    FROM product_journey_followups
                    WHERE {clause}
                    ORDER BY scheduled_at ASC
                    LIMIT ?
                    """,
                    (*params, limit),
                    default_source="ai",
                    default_direction="outbound",
                    source_table="product_journey_followups",
                    row_to_event=lambda row: {
                        "timestamp": row["sent_at"] or row["scheduled_at"],
                        "source": "ai",
                        "direction": "outbound",
                        "message": row["reply_text"] or f"followup:{row['followup_stage']}",
                        "active_flow": "product_journey",
                        "detected_intent": f"product_followup_{row['followup_stage']}",
                        "route_decision": row["send_status"],
                        "reason": row["scenario"],
                        "metadata": {
                            "product_key": row["product_key"],
                            "reply_style": row["reply_style"],
                            "customer_reference": row["customer_reference"],
                            "followup_stage": row["followup_stage"],
                            "sent": bool(row["sent"]),
                            "context": _safe_json_loads(row["context_json"]),
                        },
                    },
                )

            if _table_exists(conn, "whatsapp_message_status_events"):
                clause, params = _where_like("recipient_phone")
                _add_query_rows(
                    f"""
                    SELECT
                        created_at, message_id, recipient_phone, status, template_name,
                        error_code, error_title, error_detail, raw_payload_json
                    FROM whatsapp_message_status_events
                    WHERE {clause}
                    ORDER BY created_at ASC
                    LIMIT ?
                    """,
                    (*params, limit),
                    default_source="system",
                    default_direction="system",
                    source_table="whatsapp_message_status_events",
                    row_to_event=lambda row: {
                        "timestamp": row["created_at"],
                        "source": "system",
                        "direction": "system",
                        "message": f"WhatsApp status: {row['status']}" if row["status"] else "WhatsApp status update",
                        "route_decision": row["status"],
                        "reason": row["template_name"],
                        "metadata": {
                            "message_id": row["message_id"],
                            "error_code": row["error_code"],
                            "error_title": row["error_title"],
                            "error_detail": row["error_detail"],
                            "raw_payload": _safe_json_loads(row["raw_payload_json"]),
                        },
                    },
                )

            if _table_exists(conn, "conversation_messages") and _table_exists(conn, "conversation_sessions"):
                _add_query_rows(
                    f"""
                    SELECT
                        cm.created_at, cm.turn_number, cm.actor, cm.customer_text, cm.ai_decision_json,
                        cm.message_rendered, cm.message_type, cm.delivery_status, cm.session_id,
                        cs.customer_phone
                    FROM conversation_messages cm
                    JOIN conversation_sessions cs ON cs.id = cm.session_id
                    WHERE """ + " OR ".join(["COALESCE(cs.customer_phone, '') LIKE ?" for _ in like_patterns]) + """
                    ORDER BY cm.created_at ASC
                    LIMIT ?
                    """,
                    (*like_patterns, limit),
                    default_source="system",
                    default_direction="system",
                    source_table="conversation_messages",
                    row_to_event=lambda row: {
                        "timestamp": row["created_at"],
                        "source": row["actor"] or "system",
                        "direction": "inbound" if (row["actor"] or "").lower() == "customer" else "outbound" if (row["actor"] or "").lower() in {"ai", "wabis"} else "system",
                        "message": row["customer_text"] or row["message_rendered"],
                        "active_flow": None,
                        "detected_intent": _safe_json_loads(row["ai_decision_json"]).get("intent"),
                        "route_decision": row["message_type"],
                        "reason": row["delivery_status"],
                        "metadata": {
                            "turn_number": row["turn_number"],
                            "session_id": row["session_id"],
                            "ai_decision": _safe_json_loads(row["ai_decision_json"]),
                        },
                    },
                )

            if _table_exists(conn, "journey_messages") and _table_exists(conn, "journey_customers"):
                _add_query_rows(
                    f"""
                    SELECT
                        jm.created_at, jm.template_name, jm.journey_stage, jm.wabis_message_id,
                        jm.delivery_status, jm.variables_json, jm.sent_at, jm.channel, jc.phone
                    FROM journey_messages jm
                    JOIN journey_customers jc ON jc.id = jm.customer_id
                    WHERE """ + " OR ".join(["COALESCE(jc.phone, '') LIKE ?" for _ in like_patterns]) + """
                    ORDER BY jm.created_at ASC
                    LIMIT ?
                    """,
                    (*like_patterns, limit),
                    default_source="wabis",
                    default_direction="outbound",
                    source_table="journey_messages",
                    row_to_event=lambda row: {
                        "timestamp": row["sent_at"] or row["created_at"],
                        "source": "wabis",
                        "direction": "outbound",
                        "message": row["template_name"],
                        "active_flow": row["journey_stage"],
                        "route_decision": row["delivery_status"],
                        "reason": row["channel"],
                        "metadata": {
                            "wabis_message_id": row["wabis_message_id"],
                            "variables": _safe_json_loads(row["variables_json"]),
                        },
                    },
                )

        if _table_exists(conn, "conversation_state"):
            clause, params = _where_like("phone")
            state_rows = conn.execute(
                f"""
                SELECT
                    phone, owner, owner_reason, flow_id, flow_step, expected_responses,
                    started_at, expires_at, last_activity, context_json, created_at, updated_at
                FROM conversation_state
                WHERE {clause}
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                params,
            ).fetchall()
            for row in state_rows:
                _append_event(
                    events,
                    timestamp=row["updated_at"] or row["created_at"],
                    direction="system",
                    source="system",
                    message=(
                        f"state owner={row['owner']} flow={row['flow_id'] or 'none'} "
                        f"step={row['flow_step'] or 'none'}"
                    ),
                    owner_after=row["owner"],
                    active_flow=row["flow_id"],
                    reason=row["owner_reason"],
                    metadata={
                        "expected_responses": row["expected_responses"],
                        "started_at": row["started_at"],
                        "expires_at": row["expires_at"],
                        "last_activity": row["last_activity"],
                        "context": _safe_json_loads(row["context_json"]),
                        "source_table": "conversation_state",
                    },
                )

        events.sort(key=lambda item: item["timestamp"] or "")
        if limit > 0:
            events = events[:limit]
        return events
    except Exception as e:
        logger.error(f"Failed to get conversation history: {e}")
        return []
