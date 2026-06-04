from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.storage import _get_setting_value, _save_setting_value, init_database

PROMPT_REGISTRY_KEY = "owner_dashboard_prompt_registry_v1"

DEFAULT_PROMPTS: list[dict[str, Any]] = [
    {
        "id": "master_ai_prompt",
        "name": "Master AI Prompt",
        "category": "system",
        "status": "active",
        "version": 1,
        "description": "Overall WhatsApp sales behavior and tone.",
        "template_text": (
            "You are PureLeven AI assistant.\n"
            "Speak naturally like a Kerala salesperson.\n"
            "Never sound like a chatbot.\n"
            "Keep messages short.\n"
            "Avoid repeating information.\n"
            "Do not invent prices, stock, delivery, or offers.\n"
            "Match the customer's language and tone."
        ),
    },
    {
        "id": "message_understanding_prompt",
        "name": "Message Understanding",
        "category": "classification",
        "status": "active",
        "version": 1,
        "description": "Semantic message classification before reply generation.",
        "template_text": (
            "Classify the customer's WhatsApp message for PureLeven.\n"
            "Return JSON only with: intent, sentiment, journey_stage, customer_meaning, "
            "reply_needed, should_escalate, confidence."
        ),
    },
    {
        "id": "product_inquiry_prompt",
        "name": "Product Inquiry",
        "category": "reply_generation",
        "status": "active",
        "version": 1,
        "description": "Short human product reply framing.",
        "template_text": (
            "Write a short natural WhatsApp reply.\n"
            "Keep it human and brief.\n"
            "Do not sound corporate.\n"
            "Do not repeat facts already shown in the message body."
        ),
    },
    {
        "id": "order_taking_prompt",
        "name": "Order Taking",
        "category": "reply_generation",
        "status": "active",
        "version": 1,
        "description": "Collect order details without asking twice.",
        "template_text": (
            "Customer wants to order.\n"
            "Collect only missing details: name, address, pincode, phone.\n"
            "Do not ask again for details already present."
        ),
    },
    {
        "id": "follow_up_prompt",
        "name": "Follow Up",
        "category": "journey",
        "status": "active",
        "version": 1,
        "description": "Follow-up guidance after buying intent.",
        "template_text": (
            "Follow up only when the customer has shown buying intent.\n"
            "Do not pressure.\n"
            "Do not repeat previous price tables.\n"
            "Do not use generic check-in wording."
        ),
    },
    {
        "id": "screenshot_analysis_prompt",
        "name": "Screenshot Analysis",
        "category": "classification",
        "status": "active",
        "version": 1,
        "description": "Payment screenshot/media handling prompt.",
        "template_text": (
            "If the customer has shared a payment screenshot or proof, acknowledge it.\n"
            "Do not ask for screenshot or reference again if already present."
        ),
    },
    {
        "id": "upsell_combo_prompt",
        "name": "Upsell & Combo",
        "category": "journey",
        "status": "active",
        "version": 1,
        "description": "Combo/upsell rules.",
        "template_text": (
            "Only mention combos after clear buying intent or when the customer asks.\n"
            "Never push combo on first product inquiry."
        ),
    },
    {
        "id": "language_detection_prompt",
        "name": "Language Detection",
        "category": "classification",
        "status": "active",
        "version": 1,
        "description": "Language matching guidance.",
        "template_text": (
            "Detect whether the customer is using English, Manglish, Malayalam, or mixed style.\n"
            "Reply in the same style."
        ),
    },
    {
        "id": "customer_journey_prompt",
        "name": "Customer Journey",
        "category": "journey",
        "status": "active",
        "version": 1,
        "description": "Customer journey stage handling.",
        "template_text": (
            "Respect customer journey stage.\n"
            "Do not sell after parcel-received or thank-you messages.\n"
            "Use post-delivery acknowledgements instead."
        ),
    },
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_prompt_entry(item: dict[str, Any], fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    seed = fallback or {}
    return {
        "id": str(item.get("id") or seed.get("id") or "").strip(),
        "name": str(item.get("name") or seed.get("name") or "").strip(),
        "category": str(item.get("category") or seed.get("category") or "general").strip(),
        "status": str(item.get("status") or seed.get("status") or "active").strip(),
        "version": int(item.get("version") or seed.get("version") or 1),
        "description": str(item.get("description") or seed.get("description") or "").strip(),
        "template_text": str(item.get("template_text") or seed.get("template_text") or "").strip(),
        "updated_at": str(item.get("updated_at") or seed.get("updated_at") or _now_iso()).strip(),
    }


def _load_registry() -> list[dict[str, Any]]:
    init_database()
    raw = _get_setting_value(PROMPT_REGISTRY_KEY)
    stored: list[dict[str, Any]] = []
    if raw:
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                stored = [dict(item) for item in parsed if isinstance(item, dict)]
        except json.JSONDecodeError:
            stored = []

    merged: list[dict[str, Any]] = []
    by_id = {str(item.get("id") or "").strip(): item for item in stored}
    for default_item in DEFAULT_PROMPTS:
        existing = by_id.pop(default_item["id"], None)
        merged.append(_normalize_prompt_entry(existing or default_item, default_item))
    for extra in by_id.values():
        normalized = _normalize_prompt_entry(extra)
        if normalized["id"]:
            merged.append(normalized)
    return merged


def _save_registry(items: list[dict[str, Any]]) -> None:
    init_database()
    payload = [_normalize_prompt_entry(item) for item in items if str(item.get("id") or "").strip()]
    _save_setting_value(PROMPT_REGISTRY_KEY, json.dumps(payload, ensure_ascii=False))


def list_prompt_configs() -> list[dict[str, Any]]:
    return _load_registry()


def get_prompt_config(prompt_id: str) -> dict[str, Any]:
    prompt_id = str(prompt_id or "").strip()
    for item in _load_registry():
        if item["id"] == prompt_id:
            return item
    for default_item in DEFAULT_PROMPTS:
        if default_item["id"] == prompt_id:
            return _normalize_prompt_entry(default_item)
    return _normalize_prompt_entry({"id": prompt_id, "name": prompt_id.replace("_", " ").title()})


def get_prompt_text(prompt_id: str) -> str:
    return str(get_prompt_config(prompt_id).get("template_text") or "")


def save_prompt_config(prompt_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    prompt_id = str(prompt_id or payload.get("id") or "").strip()
    if not prompt_id:
        raise ValueError("Prompt id is required.")

    current_items = _load_registry()
    current = next((item for item in current_items if item["id"] == prompt_id), None)
    base = current or get_prompt_config(prompt_id)

    next_item = _normalize_prompt_entry(
        {
            **base,
            **payload,
            "id": prompt_id,
            "updated_at": _now_iso(),
        },
        base,
    )

    if current and str(current.get("template_text") or "").strip() != next_item["template_text"]:
        next_item["version"] = int(current.get("version") or 1) + 1

    replaced = False
    updated_items: list[dict[str, Any]] = []
    for item in current_items:
        if item["id"] == prompt_id:
            updated_items.append(next_item)
            replaced = True
        else:
            updated_items.append(item)
    if not replaced:
        updated_items.append(next_item)

    _save_registry(updated_items)
    return next_item
