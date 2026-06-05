from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.ai.intent_registry import detect_language, normalize_message
from app.ai.product_knowledge import detect_product
from app.runtime_db import ensure_runtime_tables, get_db_connection


OWNER_BY_ROUTE = {
    "wabis": "automation",
    "campaign": "automation",
    "human_only": "admin",
    "escalation": "admin",
    "payment_handler": "payment_handler",
    "button_handler": "button_handler",
    "order_handler": "order_handler",
    "catalog": "product_handler",
    "sales": "order_handler",
    "faq": "ai",
    "clarification": "ai",
    "ai": "ai",
    "silent_wait": "ai",
}

BANNED_REPLY_PHRASES = (
    "athu kurach clear aakki parayamo",
    "could you clarify",
    "i can help with products, delivery, payment, or orders",
    "what specific information would you like to know",
    "absolutely, happy to share more details",
    "why customers pick this",
    "i'll keep this open for now",
    "i’ll keep this open for now",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _table_exists(connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def selected_owner_for_route(route: str) -> str:
    return OWNER_BY_ROUTE.get(str(route or "").strip(), "ai")


def _message_type(raw: str, metadata: dict[str, Any] | None = None) -> str:
    metadata = metadata or {}
    lowered = (raw or "").strip().lower()
    explicit = str(metadata.get("message_type") or "").strip().lower()
    if lowered.startswith("#button reply#") or explicit == "postback" or metadata.get("structured_button_click"):
        return "button_reply"
    if "[[media:audio]]" in lowered or explicit == "audio":
        return "media_audio"
    if "[[media:image]]" in lowered or explicit in {"image", "photo"}:
        return "media_image"
    return "text"


def _confidence(intent: str, route: str, product_detected: bool) -> float:
    if route in {"payment_handler", "button_handler", "order_handler"}:
        return 0.96
    if product_detected:
        return 0.9
    if intent and intent != "fallback":
        return 0.78
    return 0.35


def log_message_decision(
    *,
    customer_id: str,
    incoming_message_id: str,
    incoming_message: str,
    decision: dict[str, Any],
    selected_owner: str | None = None,
    reply_message_id: str = "",
    score: float = 0,
    metadata: dict[str, Any] | None = None,
) -> None:
    ensure_runtime_tables()
    understanding = decision.get("message_understanding") or {}
    route = str(decision.get("route") or "")
    owner = selected_owner or selected_owner_for_route(route)
    normalized = normalize_message(incoming_message)
    detected_intent = str(decision.get("intent") or understanding.get("detected_intent") or "fallback")
    detected_type = _message_type(incoming_message, metadata)
    product_detected = bool(understanding.get("detected_product") or decision.get("resolved_product_key") or detect_product(incoming_message))
    now = _now()
    row_id = str(uuid.uuid4())
    payload = {
        "route": route,
        "reason": decision.get("reason"),
        "message_understanding": understanding,
        **(metadata or {}),
    }
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO message_decisions
            (id, customer_id, incoming_message_id, incoming_message, normalized_text,
             detected_type, detected_intent, confidence, selected_owner, decision_reason,
             skipped_ai, prompt_used_id, reply_message_id, route, score, metadata_json,
             created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(customer_id, incoming_message_id) DO UPDATE SET
                incoming_message = excluded.incoming_message,
                normalized_text = excluded.normalized_text,
                detected_type = excluded.detected_type,
                detected_intent = excluded.detected_intent,
                confidence = excluded.confidence,
                selected_owner = excluded.selected_owner,
                decision_reason = excluded.decision_reason,
                skipped_ai = excluded.skipped_ai,
                reply_message_id = COALESCE(NULLIF(excluded.reply_message_id, ''), message_decisions.reply_message_id),
                route = excluded.route,
                score = CASE WHEN excluded.score > 0 THEN excluded.score ELSE message_decisions.score END,
                metadata_json = excluded.metadata_json,
                updated_at = excluded.updated_at
            """,
            (
                row_id,
                str(customer_id or ""),
                str(incoming_message_id or row_id),
                incoming_message[:1200],
                normalized,
                detected_type,
                detected_intent,
                _confidence(detected_intent, route, product_detected),
                owner,
                str(decision.get("reason") or "")[:500],
                0 if owner == "ai" else 1,
                str((metadata or {}).get("prompt_used_id") or ""),
                reply_message_id,
                route,
                float(score or 0),
                json.dumps(payload, ensure_ascii=False),
                now,
                now,
            ),
        )
        connection.commit()


def upsert_customer_journey_state(
    *,
    customer_id: str,
    current_stage: str = "",
    active_product: str = "",
    active_language: str = "",
    last_intent: str = "",
    last_customer_message_id: str = "",
    last_ai_reply_id: str = "",
    waiting_for: str = "",
    payment_status: str = "",
    order_status: str = "",
    followup_stage: str = "",
    context: dict[str, Any] | None = None,
) -> None:
    ensure_runtime_tables()
    now = _now()
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO customer_journey_state
            (customer_id, current_stage, active_product, active_language, last_intent,
             last_customer_message_id, last_ai_reply_id, waiting_for, payment_status,
             order_status, followup_stage, last_interaction_at, context_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(customer_id) DO UPDATE SET
                current_stage = COALESCE(NULLIF(excluded.current_stage, ''), customer_journey_state.current_stage),
                active_product = COALESCE(NULLIF(excluded.active_product, ''), customer_journey_state.active_product),
                active_language = COALESCE(NULLIF(excluded.active_language, ''), customer_journey_state.active_language),
                last_intent = COALESCE(NULLIF(excluded.last_intent, ''), customer_journey_state.last_intent),
                last_customer_message_id = COALESCE(NULLIF(excluded.last_customer_message_id, ''), customer_journey_state.last_customer_message_id),
                last_ai_reply_id = COALESCE(NULLIF(excluded.last_ai_reply_id, ''), customer_journey_state.last_ai_reply_id),
                waiting_for = COALESCE(NULLIF(excluded.waiting_for, ''), customer_journey_state.waiting_for),
                payment_status = COALESCE(NULLIF(excluded.payment_status, ''), customer_journey_state.payment_status),
                order_status = COALESCE(NULLIF(excluded.order_status, ''), customer_journey_state.order_status),
                followup_stage = COALESCE(NULLIF(excluded.followup_stage, ''), customer_journey_state.followup_stage),
                last_interaction_at = excluded.last_interaction_at,
                context_json = excluded.context_json,
                updated_at = excluded.updated_at
            """,
            (
                str(customer_id or ""),
                current_stage,
                active_product,
                active_language or detect_language(active_product or ""),
                last_intent,
                last_customer_message_id,
                last_ai_reply_id,
                waiting_for,
                payment_status,
                order_status,
                followup_stage,
                now,
                json.dumps(context or {}, ensure_ascii=False),
                now,
                now,
            ),
        )
        connection.commit()


def audit_reply_quality(
    *,
    customer_id: str,
    incoming_message_id: str,
    reply_message_id: str,
    reply_text: str,
    intent: str = "",
    journey_stage: str = "",
) -> dict[str, Any]:
    ensure_runtime_tables()
    text = reply_text or ""
    lower = text.lower()
    words = len(re.findall(r"\S+", text))
    issues: list[str] = []
    if words > 55:
        issues.append("too_long")
    if any(phrase in lower for phrase in BANNED_REPLY_PHRASES):
        issues.append("banned_or_robotic_phrase")
    if text.count("\n\n") > 4:
        issues.append("catalog_style")
    length_score = 10 if words <= 35 else 8 if words <= 55 else 4
    tone_score = 5 if "banned_or_robotic_phrase" in issues else 8
    journey_score = 8 if journey_stage else 6
    intent_score = 8 if intent else 5
    duplicate_score = 8
    overall = round((length_score + tone_score + journey_score + intent_score + duplicate_score) / 5, 2)
    audit_id = str(uuid.uuid4())
    with get_db_connection() as connection:
        connection.execute(
            """
            INSERT INTO ai_reply_audit
            (id, customer_id, incoming_message_id, reply_message_id, intent_match_score,
             tone_score, length_score, journey_score, duplicate_risk_score, overall_score,
             issues_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_id,
                str(customer_id or ""),
                str(incoming_message_id or ""),
                str(reply_message_id or ""),
                intent_score,
                tone_score,
                length_score,
                journey_score,
                duplicate_score,
                overall,
                json.dumps(issues, ensure_ascii=False),
                _now(),
            ),
        )
        connection.commit()
    return {"audit_id": audit_id, "score": overall, "issues": issues}


def get_message_control_payload(*, hours: int = 4, limit: int = 100) -> dict[str, Any]:
    ensure_runtime_tables()
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=int(hours))).isoformat(timespec="seconds")
    with get_db_connection() as connection:
        decisions = [
            dict(row)
            for row in connection.execute(
                """
                SELECT *
                FROM message_decisions
                WHERE created_at >= ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (cutoff, int(limit)),
            ).fetchall()
        ]
        if not decisions and _table_exists(connection, "routing_log"):
            decisions.extend(
                [
                    {
                        "id": row["id"],
                        "customer_id": row["phone"],
                        "incoming_message_id": row["id"],
                        "incoming_message": row["message"] or "",
                        "normalized_text": normalize_message(row["message"] or ""),
                        "detected_type": "text",
                        "detected_intent": "",
                        "confidence": 0.65,
                        "selected_owner": selected_owner_for_route(row["route_taken"]),
                        "decision_reason": "routing_log_fallback",
                        "skipped_ai": 1 if selected_owner_for_route(row["route_taken"]) != "ai" else 0,
                        "prompt_used_id": "",
                        "reply_message_id": "",
                        "route": row["route_taken"],
                        "score": 6,
                        "metadata_json": row["context"] or "{}",
                        "created_at": row["timestamp"],
                        "updated_at": row["timestamp"],
                    }
                    for row in connection.execute(
                        """
                        SELECT id, phone, message, route_taken, context, timestamp
                        FROM routing_log
                        WHERE timestamp >= ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                        """,
                        (cutoff, int(limit)),
                    ).fetchall()
                ]
            )
        if not decisions and _table_exists(connection, "ai_incoming_messages"):
            decisions.extend(
                [
                    {
                        "id": row["id"],
                        "customer_id": row["customer_phone"],
                        "incoming_message_id": row["id"],
                        "incoming_message": row["body"] or "",
                        "normalized_text": normalize_message(row["body"] or ""),
                        "detected_type": row["message_type"] or "text",
                        "detected_intent": "",
                        "confidence": 0.45,
                        "selected_owner": "unclassified",
                        "decision_reason": "incoming_message_without_decision",
                        "skipped_ai": 0,
                        "prompt_used_id": "",
                        "reply_message_id": "",
                        "route": "",
                        "score": 0,
                        "metadata_json": json.dumps({"conversation_id": row["conversation_id"]}, ensure_ascii=False),
                        "created_at": row["created_at"],
                        "updated_at": row["created_at"],
                    }
                    for row in connection.execute(
                        """
                        SELECT id, conversation_id, customer_phone, message_type, body, created_at
                        FROM ai_incoming_messages
                        WHERE created_at >= ?
                        ORDER BY created_at DESC
                        LIMIT ?
                        """,
                        (cutoff, int(limit)),
                    ).fetchall()
                ]
            )
        if not decisions and _table_exists(connection, "conversation_state"):
            decisions.extend(
                [
                    {
                        "id": f"state:{row['phone']}",
                        "customer_id": row["phone"],
                        "incoming_message_id": "",
                        "incoming_message": row["owner_reason"] or row["flow_step"] or row["journey_stage"] or "",
                        "normalized_text": normalize_message(row["owner_reason"] or row["flow_step"] or row["journey_stage"] or ""),
                        "detected_type": "state_snapshot",
                        "detected_intent": row["latest_intent"] or "",
                        "confidence": 0.35,
                        "selected_owner": row["owner"] or "unknown",
                        "decision_reason": "conversation_state_fallback",
                        "skipped_ai": 1 if (row["owner"] or "") not in {"", "ai"} else 0,
                        "prompt_used_id": "",
                        "reply_message_id": "",
                        "route": row["owner"] or "",
                        "score": 0,
                        "metadata_json": json.dumps(
                            {
                                "active_product": row["active_product"],
                                "language": row["language"],
                                "journey_stage": row["journey_stage"],
                                "flow_id": row["flow_id"],
                                "flow_step": row["flow_step"],
                                "next_best_action": row["owner_reason"] or "Review current customer state",
                            },
                            ensure_ascii=False,
                        ),
                        "created_at": row["last_activity"] or row["updated_at"] or "",
                        "updated_at": row["updated_at"] or row["last_activity"] or "",
                    }
                    for row in connection.execute(
                        """
                        SELECT phone, owner, owner_reason, flow_id, flow_step, active_product,
                               latest_intent, language, journey_stage, last_activity, updated_at
                        FROM conversation_state
                        ORDER BY COALESCE(last_activity, updated_at, created_at) DESC
                        LIMIT ?
                        """,
                        (int(limit),),
                    ).fetchall()
                ]
            )
        duplicate_rows = [
            dict(row)
            for row in connection.execute(
                """
                SELECT customer_id, incoming_message_id, COUNT(*) AS lock_count,
                       MIN(created_at) AS first_seen, MAX(updated_at) AS last_seen
                FROM message_processing_locks
                WHERE created_at >= ?
                GROUP BY customer_id, incoming_message_id
                HAVING COUNT(*) > 1
                ORDER BY last_seen DESC
                LIMIT ?
                """,
                (cutoff, int(limit)),
            ).fetchall()
        ]
        audits = [
            dict(row)
            for row in connection.execute(
                """
                SELECT *
                FROM ai_reply_audit
                WHERE created_at >= ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (cutoff, int(limit)),
            ).fetchall()
        ]
    for item in decisions:
        item["metadata"] = json.loads(item.pop("metadata_json") or "{}")
    for item in audits:
        item["issues"] = json.loads(item.pop("issues_json") or "[]")
    owner_counts: dict[str, int] = {}
    for item in decisions:
        owner = item.get("selected_owner") or "unknown"
        owner_counts[owner] = owner_counts.get(owner, 0) + 1
    return {
        "decisions": decisions,
        "audits": audits,
        "duplicate_locks": duplicate_rows,
        "owner_breakdown": [{"owner": key, "count": value} for key, value in sorted(owner_counts.items())],
        "metrics": {
            "decisions": len(decisions),
            "ai_skipped": sum(1 for item in decisions if item.get("skipped_ai")),
            "audited_replies": len(audits),
            "duplicate_lock_groups": len(duplicate_rows),
        },
    }
