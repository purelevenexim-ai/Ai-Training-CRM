from __future__ import annotations

import hashlib
import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

from app.ai.intent_registry import detect_intent, detect_language, normalize_message
from app.ai.product_knowledge import detect_product
from app.runtime_db import ensure_runtime_tables, get_db_connection

logger = logging.getLogger(__name__)


CUSTOMER_STATE_COLUMNS: dict[str, str] = {
    "customer_id": "TEXT",
    "language": "TEXT",
    "active_product": "TEXT",
    "latest_intent": "TEXT",
    "price_shared": "INTEGER NOT NULL DEFAULT 0",
    "quantity_selected": "TEXT",
    "address_received": "INTEGER NOT NULL DEFAULT 0",
    "pincode_received": "TEXT",
    "payment_claimed": "INTEGER NOT NULL DEFAULT 0",
    "payment_screenshot_received": "INTEGER NOT NULL DEFAULT 0",
    "defer_intent": "TEXT",
    "followups_allowed": "INTEGER NOT NULL DEFAULT 1",
    "journey_stage": "TEXT",
    "last_ai_reply_hash": "TEXT",
    "last_ai_reply_at": "TEXT",
}


def _table_exists(connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def _table_columns(connection, table_name: str) -> set[str]:
    if not _table_exists(connection, table_name):
        return set()
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()}


def ensure_customer_state_schema() -> None:
    ensure_runtime_tables()
    with get_db_connection() as conn:
        columns = _table_columns(conn, "conversation_state")
        if not columns:
            return
        for column_name, definition in CUSTOMER_STATE_COLUMNS.items():
            if column_name in columns:
                continue
            try:
                conn.execute(f"ALTER TABLE conversation_state ADD COLUMN {column_name} {definition}")
            except Exception as exc:
                logger.warning("Failed to add customer state column %s: %s", column_name, exc)
        conn.commit()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize_context(context: dict[str, Any] | None) -> str | None:
    if not context:
        return None
    return json.dumps(context, ensure_ascii=False)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_bool(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return 1 if value else 0
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return 1
    if text in {"0", "false", "no", "n", "off"}:
        return 0
    return default


def reply_hash(reply_text: str) -> str:
    normalized = " ".join(normalize_message(reply_text).split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _address_like(message: str) -> bool:
    text = normalize_message(message)
    if not text:
        return False
    keywords = (
        "house",
        "h",
        "street",
        "road",
        "lane",
        "near",
        "p.o",
        "po ",
        "post",
        "district",
        "dist",
        "village",
        "town",
        "place",
        "building",
        "flat",
        "apt",
        "apartment",
        "state",
        "location",
        "address",
    )
    if any(keyword in text for keyword in keywords):
        return True
    if len(text.split()) >= 4 and re.search(r"\d", text):
        return True
    return False


def _extract_pincode(message: str) -> str:
    match = re.search(r"\b(\d{6})\b", message or "")
    return match.group(1) if match else ""


def _extract_quantity(message: str) -> str:
    text = normalize_message(message)
    if not text:
        return ""
    patterns = (
        r"\b\d+\s?(?:kg|g|gram|grams|pack|packs)\b",
        r"\b\d+\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).replace("  ", " ").strip()
    return ""


def _detect_payment_claim(message: str) -> bool:
    text = normalize_message(message)
    if not text:
        return False
    return any(
        keyword in text
        for keyword in (
            "paid",
            "payment done",
            "cash paid",
            "transfered",
            "transferred",
            "gpay",
            "upi",
            "transaction",
            "sent money",
            "sent payment",
            "payment sent",
            "net banking",
        )
    )


def _detect_screenshot(message: str, message_type: str | None = None) -> bool:
    text = normalize_message(message)
    if message_type and message_type.lower() in {"image", "photo", "media", "document"}:
        return True
    return any(keyword in text for keyword in ("screenshot", "receipt", "proof", "payment screenshot"))


def _current_row(customer_id: str) -> dict[str, Any]:
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM conversation_state WHERE phone = ?",
            (customer_id,),
        ).fetchone()
        return dict(row) if row else {}


def get_customer_state(customer_id: str) -> dict[str, Any]:
    ensure_customer_state_schema()
    row = _current_row(customer_id)
    if not row:
        return {}
    context = {}
    if row.get("context_json"):
        try:
            parsed = json.loads(str(row["context_json"]))
            if isinstance(parsed, dict):
                context = parsed
        except Exception:
            context = {}

    result = {
        "customer_id": customer_id,
        "language": row.get("language") or "",
        "active_product": row.get("active_product") or context.get("product_key") or "",
        "latest_intent": row.get("latest_intent") or context.get("scenario") or "",
        "price_shared": bool(row.get("price_shared")),
        "quantity_selected": row.get("quantity_selected") or "",
        "address_received": bool(row.get("address_received")),
        "pincode_received": row.get("pincode_received") or "",
        "payment_claimed": bool(row.get("payment_claimed")),
        "payment_screenshot_received": bool(row.get("payment_screenshot_received")),
        "defer_intent": row.get("defer_intent") or "",
        "followups_allowed": bool(row.get("followups_allowed", 1)),
        "journey_stage": row.get("journey_stage") or row.get("flow_step") or "",
        "last_ai_reply_hash": row.get("last_ai_reply_hash") or "",
        "last_ai_reply_at": row.get("last_ai_reply_at") or "",
        "owner": row.get("owner") or "ai",
        "owner_reason": row.get("owner_reason") or "",
        "flow_id": row.get("flow_id") or "",
        "flow_step": row.get("flow_step") or "",
        "context": context,
    }
    return result


def _merge_context(base: dict[str, Any], updates: dict[str, Any] | None) -> dict[str, Any]:
    merged = dict(base or {})
    if updates:
        merged.update(updates)
    return merged


def update_customer_state(
    customer_id: str,
    *,
    inbound_message: str = "",
    message_type: str = "text",
    language: str | None = None,
    product_key: str | None = None,
    active_product: str | None = None,
    latest_intent: str | None = None,
    journey_stage: str | None = None,
    price_shared: bool | None = None,
    quantity_selected: str | None = None,
    address_received: bool | None = None,
    pincode_received: str | None = None,
    payment_claimed: bool | None = None,
    payment_screenshot_received: bool | None = None,
    defer_intent: str | None = None,
    followups_allowed: bool | None = None,
    last_ai_reply_hash: str | None = None,
    last_ai_reply_at: str | None = None,
    context_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ensure_customer_state_schema()
    if not customer_id:
        return {}

    existing = _current_row(customer_id)
    existing_context: dict[str, Any] = {}
    if existing.get("context_json"):
        try:
            parsed = json.loads(str(existing["context_json"]))
            if isinstance(parsed, dict):
                existing_context = parsed
        except Exception:
            existing_context = {}

    detected_language = language or detect_language(inbound_message or "")
    detected_product = active_product or product_key or detect_product(inbound_message or "")
    detected_intent = latest_intent or detect_intent(inbound_message or "", product_detected=bool(detected_product))
    detected_price_shared = _normalize_bool(price_shared, default=_normalize_bool(existing.get("price_shared"), 0))
    detected_quantity = quantity_selected or _extract_quantity(inbound_message or "")
    detected_address = _normalize_bool(address_received, default=_normalize_bool(existing.get("address_received"), 0))
    detected_pincode = pincode_received or _extract_pincode(inbound_message or "")
    detected_payment_claimed = _normalize_bool(payment_claimed, default=_normalize_bool(existing.get("payment_claimed"), 0))
    detected_payment_screenshot = _normalize_bool(
        payment_screenshot_received,
        default=_normalize_bool(existing.get("payment_screenshot_received"), 0),
    )
    detected_followups_allowed = _normalize_bool(
        followups_allowed,
        default=_normalize_bool(existing.get("followups_allowed"), 1),
    )

    if not detected_address and _address_like(inbound_message or ""):
        detected_address = 1
    if not detected_payment_claimed and _detect_payment_claim(inbound_message or ""):
        detected_payment_claimed = 1
    if not detected_payment_screenshot and _detect_screenshot(inbound_message or "", message_type=message_type):
        detected_payment_screenshot = 1

    if defer_intent is None and detected_intent in {"followup", "negation"}:
        defer_intent = detected_intent
    if followups_allowed is None:
        if detected_intent in {"order_request", "order_confirm", "order_intent"}:
            detected_followups_allowed = 1
        elif detected_intent in {"followup", "negation"}:
            detected_followups_allowed = 0
        elif detected_intent in {"availability", "price", "stock_check", "details", "quality", "origin", "processing", "usage", "benefits", "comparison", "budget", "best_pack"}:
            detected_followups_allowed = 0

    if journey_stage is None:
        if detected_intent in {"followup", "negation"}:
            journey_stage = "deferred"
        elif detected_intent in {"order_request", "order_confirm"}:
            journey_stage = "order_capture"
        elif detected_intent in {"price", "availability", "stock_check"} and detected_product:
            journey_stage = "product_interest"

    context = _merge_context(
        existing_context,
        {
            "customer_id": customer_id,
            "language": detected_language,
            "product_key": detected_product or existing_context.get("product_key"),
            "latest_intent": detected_intent,
            "journey_stage": journey_stage or existing.get("journey_stage") or existing.get("flow_step"),
            "price_shared": bool(detected_price_shared),
            "quantity_selected": detected_quantity,
            "address_received": bool(detected_address),
            "pincode_received": detected_pincode,
            "payment_claimed": bool(detected_payment_claimed),
            "payment_screenshot_received": bool(detected_payment_screenshot),
            "defer_intent": defer_intent or existing.get("defer_intent") or "",
            "followups_allowed": bool(detected_followups_allowed),
        },
    )
    context = _merge_context(context, context_updates)

    now = _now()
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO conversation_state (
                phone, owner, owner_reason, flow_id, flow_step, expected_responses,
                started_at, expires_at, last_activity, context_json, created_at, updated_at,
                customer_id, language, active_product, latest_intent, price_shared,
                quantity_selected, address_received, pincode_received, payment_claimed,
                payment_screenshot_received, defer_intent, followups_allowed, journey_stage,
                last_ai_reply_hash, last_ai_reply_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(phone) DO UPDATE SET
                owner = COALESCE(excluded.owner, conversation_state.owner),
                owner_reason = COALESCE(excluded.owner_reason, conversation_state.owner_reason),
                flow_id = COALESCE(excluded.flow_id, conversation_state.flow_id),
                flow_step = COALESCE(excluded.flow_step, conversation_state.flow_step),
                expected_responses = COALESCE(excluded.expected_responses, conversation_state.expected_responses),
                started_at = COALESCE(excluded.started_at, conversation_state.started_at),
                expires_at = COALESCE(excluded.expires_at, conversation_state.expires_at),
                last_activity = COALESCE(excluded.last_activity, conversation_state.last_activity),
                context_json = COALESCE(excluded.context_json, conversation_state.context_json),
                updated_at = excluded.updated_at,
                customer_id = COALESCE(excluded.customer_id, conversation_state.customer_id),
                language = COALESCE(excluded.language, conversation_state.language),
                active_product = COALESCE(excluded.active_product, conversation_state.active_product),
                latest_intent = COALESCE(excluded.latest_intent, conversation_state.latest_intent),
                price_shared = COALESCE(excluded.price_shared, conversation_state.price_shared),
                quantity_selected = COALESCE(excluded.quantity_selected, conversation_state.quantity_selected),
                address_received = COALESCE(excluded.address_received, conversation_state.address_received),
                pincode_received = COALESCE(excluded.pincode_received, conversation_state.pincode_received),
                payment_claimed = COALESCE(excluded.payment_claimed, conversation_state.payment_claimed),
                payment_screenshot_received = COALESCE(excluded.payment_screenshot_received, conversation_state.payment_screenshot_received),
                defer_intent = COALESCE(excluded.defer_intent, conversation_state.defer_intent),
                followups_allowed = COALESCE(excluded.followups_allowed, conversation_state.followups_allowed),
                journey_stage = COALESCE(excluded.journey_stage, conversation_state.journey_stage),
                last_ai_reply_hash = COALESCE(excluded.last_ai_reply_hash, conversation_state.last_ai_reply_hash),
                last_ai_reply_at = COALESCE(excluded.last_ai_reply_at, conversation_state.last_ai_reply_at)
            """,
            (
                existing.get("phone") or customer_id,
                existing.get("owner") or "ai",
                existing.get("owner_reason") or "customer_state_update",
                existing.get("flow_id"),
                existing.get("flow_step"),
                existing.get("expected_responses"),
                existing.get("started_at") or now,
                existing.get("expires_at"),
                now,
                _serialize_context(context),
                existing.get("created_at") or now,
                now,
                customer_id,
                detected_language,
                detected_product or existing.get("active_product"),
                detected_intent,
                detected_price_shared,
                detected_quantity,
                detected_address,
                detected_pincode,
                detected_payment_claimed,
                detected_payment_screenshot,
                defer_intent or existing.get("defer_intent"),
                detected_followups_allowed,
                journey_stage or existing.get("journey_stage") or existing.get("flow_step"),
                last_ai_reply_hash or existing.get("last_ai_reply_hash"),
                last_ai_reply_at or existing.get("last_ai_reply_at"),
            ),
        )
        conn.commit()
    return get_customer_state(customer_id)


def sync_customer_state_from_inbound(
    *,
    customer_id: str,
    inbound_message: str,
    message_type: str = "text",
    product_key: str | None = None,
    intent: str | None = None,
    language: str | None = None,
    journey_stage: str | None = None,
    followups_allowed: bool | None = None,
    context_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return update_customer_state(
        customer_id,
        inbound_message=inbound_message,
        message_type=message_type,
        product_key=product_key,
        latest_intent=intent,
        language=language,
        journey_stage=journey_stage,
        followups_allowed=followups_allowed,
        context_updates=context_updates,
    )


def record_ai_reply(
    *,
    customer_id: str,
    inbound_message: str = "",
    generated_reply: str,
    final_reply: str,
    reply_result: dict[str, Any] | None = None,
    guard_action: str = "sent",
    issues_found: list[str] | None = None,
    detected_intent: str | None = None,
    active_product: str | None = None,
    journey_stage: str | None = None,
) -> dict[str, Any]:
    reply_result = reply_result or {}
    state = get_customer_state(customer_id)
    if not state:
        state = {}

    product_key = active_product or str(reply_result.get("product_key") or state.get("active_product") or "").strip()
    intent = detected_intent or str(reply_result.get("intent") or state.get("latest_intent") or "").strip()
    final_hash = reply_hash(final_reply) if final_reply else ""
    updates = update_customer_state(
        customer_id,
        inbound_message=inbound_message,
        product_key=product_key or None,
        latest_intent=intent or None,
        journey_stage=journey_stage or state.get("journey_stage") or None,
        price_shared=state.get("price_shared"),
        quantity_selected=state.get("quantity_selected"),
        address_received=state.get("address_received"),
        pincode_received=state.get("pincode_received") or None,
        payment_claimed=state.get("payment_claimed"),
        payment_screenshot_received=state.get("payment_screenshot_received"),
        defer_intent=state.get("defer_intent") or None,
        followups_allowed=state.get("followups_allowed"),
        last_ai_reply_hash=final_hash or None,
        last_ai_reply_at=_now() if final_reply else state.get("last_ai_reply_at"),
        context_updates={
            "last_ai_reply_hash": final_hash,
            "last_ai_reply_at": _now() if final_reply else state.get("last_ai_reply_at"),
            "generated_reply": generated_reply,
            "final_reply": final_reply,
            "guard_action": guard_action,
            "issues_found": issues_found or [],
            "reply_intent": intent,
            "active_product": product_key,
        },
    )
    return updates
