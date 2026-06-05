from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.ai.conversation_state_manager import get_conversation_state, reset_conversation_state, set_conversation_state
from app.runtime_db import ensure_runtime_tables, get_db_connection
from app.storage import _get_setting_value, _save_setting_value, init_database

HUMAN_LOOP_SETTINGS_KEY = "owner_dashboard_human_loop_rules"

DEFAULT_HUMAN_LOOP_SETTINGS: dict[str, Any] = {
    "unclear_to_human_enabled": True,
    "human_inactivity_resume_enabled": True,
    "human_inactivity_minutes": 5,
    "continuous_learning_enabled": True,
    "allow_customer_clarification_messages": False,
    "unknown_media_to_human_enabled": True,
    "min_ai_confidence": 0.65,
    "updated_at": "",
}

RULES: list[dict[str, Any]] = [
    {
        "key": "unclear_to_human_enabled",
        "title": "Unclear means human takeover",
        "description": "If product/intent is not clear, AI must not send a customer reply. Create a human-review item instead.",
        "critical": True,
    },
    {
        "key": "human_inactivity_resume_enabled",
        "title": "AI resumes after human inactivity",
        "description": "When human owns a pending customer turn, AI may retry after the configured inactivity window.",
        "critical": True,
    },
    {
        "key": "continuous_learning_enabled",
        "title": "Capture learning gaps",
        "description": "Unclear turns are saved as learning items for review before being added back to rules/catalog.",
        "critical": True,
    },
    {
        "key": "allow_customer_clarification_messages",
        "title": "Allow AI clarification messages",
        "description": "Keep this off for production. If off, AI never asks unclear fallback questions to customers.",
        "critical": True,
    },
]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _load_settings() -> dict[str, Any]:
    try:
        init_database()
        raw = _get_setting_value(HUMAN_LOOP_SETTINGS_KEY)
    except Exception:
        raw = None
    if not raw:
        return dict(DEFAULT_HUMAN_LOOP_SETTINGS)
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {**DEFAULT_HUMAN_LOOP_SETTINGS, **parsed}
    except json.JSONDecodeError:
        pass
    return dict(DEFAULT_HUMAN_LOOP_SETTINGS)


def get_human_loop_settings() -> dict[str, Any]:
    settings = _load_settings()
    try:
        settings["human_inactivity_minutes"] = max(1, min(60, int(settings.get("human_inactivity_minutes") or 5)))
    except (TypeError, ValueError):
        settings["human_inactivity_minutes"] = 5
    try:
        settings["min_ai_confidence"] = max(0.0, min(1.0, float(settings.get("min_ai_confidence") or 0.65)))
    except (TypeError, ValueError):
        settings["min_ai_confidence"] = 0.65
    return settings


def save_human_loop_settings(payload: dict[str, Any]) -> dict[str, Any]:
    current = get_human_loop_settings()
    allowed = set(DEFAULT_HUMAN_LOOP_SETTINGS)
    merged = {**current, **{key: value for key, value in (payload or {}).items() if key in allowed}}
    for key in (
        "unclear_to_human_enabled",
        "human_inactivity_resume_enabled",
        "continuous_learning_enabled",
        "allow_customer_clarification_messages",
        "unknown_media_to_human_enabled",
    ):
        merged[key] = bool(merged.get(key))
    merged["human_inactivity_minutes"] = max(1, min(60, int(merged.get("human_inactivity_minutes") or 5)))
    merged["min_ai_confidence"] = max(0.0, min(1.0, float(merged.get("min_ai_confidence") or 0.65)))
    merged["updated_at"] = _now()
    init_database()
    _save_setting_value(HUMAN_LOOP_SETTINGS_KEY, json.dumps(merged, ensure_ascii=False, sort_keys=True))
    return get_human_loop_settings()


def human_inactivity_delay_seconds() -> int:
    return int(get_human_loop_settings().get("human_inactivity_minutes") or 5) * 60


def _recent_learning_items(limit: int = 40) -> list[dict[str, Any]]:
    ensure_runtime_tables()
    items: list[dict[str, Any]] = []
    with get_db_connection() as connection:
        try:
            rows = connection.execute(
                """
                SELECT id, phone, original_query, detected_intent, detected_product,
                       confidence, reason, status, created_at, updated_at
                FROM knowledge_gaps
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
            items.extend(dict(row) for row in rows)
        except sqlite3.OperationalError:
            pass
        try:
            rows = connection.execute(
                """
                SELECT id, customer_id AS phone, incoming_message AS original_query,
                       detected_intent, '' AS detected_product, confidence,
                       decision_reason AS reason, route AS status, created_at, updated_at
                FROM message_decisions
                WHERE selected_owner = 'admin'
                   OR route IN ('human_only', 'clarification', 'silent_wait')
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
            items.extend(dict(row) for row in rows)
        except sqlite3.OperationalError:
            pass
    return sorted(items, key=lambda item: str(item.get("created_at") or ""), reverse=True)[:limit]


def get_human_loop_dashboard_payload() -> dict[str, Any]:
    settings = get_human_loop_settings()
    return {
        "settings": settings,
        "rules": [
            {
                **rule,
                "enabled": bool(settings.get(rule["key"])),
                "value": settings.get(rule["key"]),
            }
            for rule in RULES
        ],
        "learning_items": _recent_learning_items(),
        "summary": {
            "human_inactivity_minutes": settings["human_inactivity_minutes"],
            "critical_rules_enabled": sum(1 for rule in RULES if rule["critical"] and settings.get(rule["key"])),
            "critical_rules_total": sum(1 for rule in RULES if rule["critical"]),
            "learning_items": len(_recent_learning_items(20)),
        },
    }


def human_lock_status(phone: str, state: dict[str, Any] | None = None) -> dict[str, Any]:
    state = state or get_conversation_state(phone) or {}
    context = dict(state.get("context") or {})
    lock_until = _parse_dt(str(context.get("human_lock_until") or ""))
    now = datetime.now(timezone.utc)
    if state.get("owner") != "human":
        return {"active": False, "expired": False, "lock_until": "", "context": context}
    if not lock_until:
        return {"active": True, "expired": False, "lock_until": "", "context": context}
    return {
        "active": lock_until > now,
        "expired": lock_until <= now,
        "lock_until": lock_until.isoformat(),
        "context": context,
    }


def release_expired_human_lock_if_needed(phone: str) -> bool:
    status = human_lock_status(phone)
    if not status.get("expired"):
        return False
    reset_conversation_state(phone)
    return True


def route_to_human_review(
    *,
    phone: str,
    conversation_id: str,
    incoming_message: str,
    reason: str,
    decision: dict[str, Any] | None = None,
    gap_id: str = "",
    incoming_message_id: str = "",
) -> dict[str, Any]:
    settings = get_human_loop_settings()
    delay_minutes = int(settings.get("human_inactivity_minutes") or 5)
    lock_until = (datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)).isoformat()
    understanding = (decision or {}).get("message_understanding") or {}
    context = {
        "human_loop": True,
        "human_lock_until": lock_until,
        "human_inactivity_minutes": delay_minutes,
        "pending_customer_turn": incoming_message,
        "pending_conversation_id": conversation_id,
        "pending_incoming_message_id": incoming_message_id,
        "gap_id": gap_id,
        "review_reason": reason,
        "detected_intent": str((decision or {}).get("intent") or understanding.get("detected_intent") or ""),
        "detected_product": str(understanding.get("detected_product") or (decision or {}).get("resolved_product_key") or ""),
        "confidence": float(understanding.get("confidence") or 0.0),
        "followups_allowed": False,
        "journey_stage": "human_review",
    }
    set_conversation_state(
        phone,
        owner="human",
        owner_reason="unclear_requires_human",
        flow_id="human_review",
        flow_step="awaiting_human",
        context=context,
    )
    try:
        with get_db_connection() as connection:
            connection.execute(
                """
                INSERT INTO escalation_queue (id, customer_phone, reason, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    phone,
                    f"Human review: {reason}. Message: {incoming_message[:180]}",
                    _now(),
                ),
            )
            connection.commit()
    except Exception:
        pass
    return {
        "status": "skipped",
        "reason": "human_review_required",
        "route": "human_only",
        "gap_id": gap_id,
        "human_lock_until": lock_until,
        "human_inactivity_minutes": delay_minutes,
    }
