from __future__ import annotations

import hashlib
import json
import socket
import ssl
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.ai.intent_registry import SUPPORTED_INTENTS
from app.ai.pricing_formatter import reload_product_catalog_from_file
from app.ai.product_knowledge import (
    dashboard_payload as canonical_dashboard_payload,
    detect_product as detect_canonical_product,
    get_product as get_canonical_product,
)
from app.config import settings
from app.services.product_media_service import (
    DEFAULT_PUBLIC_GOOGLE_DRIVE_FOLDER_URL,
    delete_product_image_file,
    delete_product_media_collection,
    list_public_google_drive_folder_entries,
    normalize_product_image_entries,
    save_product_image_from_url,
)
from app.services.prompt_registry_service import list_prompt_configs, save_prompt_config
from app.storage import _get_setting_value, _save_setting_value, get_db_connection, init_database

AI_CONTROL_KEY = "owner_dashboard_ai_control"
PRODUCT_IMAGE_DRIVE_FOLDER_URL = DEFAULT_PUBLIC_GOOGLE_DRIVE_FOLDER_URL
INTENT_KNOWLEDGE_FILENAME = "WHATSAPP_INTENT_KNOWLEDGE_BASE.json"
LEGACY_INTENT_ALIASES: dict[str, str] = {
    "product_availability": "availability",
    "availability": "availability",
    "price_check": "price",
    "price": "price",
    "purchase_guidance": "best_pack",
    "best_pack": "best_pack",
    "delivery_query": "delivery_time",
    "delivery": "delivery_time",
    "order_intent": "order_request",
    "order": "order_request",
    "combo_offer": "combo",
    "combo": "combo",
    "objection_price": "price_objection",
    "value_objection": "price_objection",
    "quality_inquiry": "quality",
    "quality": "quality",
    "product_negation": "negation",
    "negation": "negation",
    "usage_question": "usage",
    "how_to_use": "usage",
    "origin_question": "origin",
    "origin": "origin",
    "gift_query": "gift",
    "gift": "gift",
    "restock_query": "stock_check",
    "restock": "stock_check",
    "budget_query": "budget",
    "budget": "budget",
    "comparison_query": "comparison",
    "comparison": "comparison",
    "personal_order": "gift",
    "gift_personal": "gift",
    "followup_prompt": "followup",
    "followup": "followup",
    "clarification_needed": "fallback",
    "clarification": "fallback",
    "wholesale_inquiry": "wholesale",
    "complaint": "complaint",
}

DEFAULT_AI_CONTROL: dict[str, Any] = {
    "ai_running": True,
    "server_orchestration_enabled": True,
    "flow_break_detection_enabled": True,
    "structured_button_passthrough_enabled": True,
    "wabis_fallback_when_disabled": True,
    "wabis_priority_minutes": 5,
    "selected_model": "gemini_flash",
    "temperature": 0.25,
    "languages": ["english", "manglish", "malayalam"],
    "followup_send_enabled": bool(settings.ai_followup_send_enabled),
    "updated_at": "",
}

MODEL_OPTIONS: list[dict[str, str]] = [
    {
        "key": "gemini_flash",
        "label": "Gemini Flash",
        "provider": "gemini",
        "runtime_model": "gemini-2.5-flash",
    },
    {
        "key": "openai_mini",
        "label": "OpenAI Mini",
        "provider": "openrouter",
        "runtime_model": "openai/gpt-4o-mini",
    },
    {
        "key": "claude_haiku",
        "label": "Claude Haiku",
        "provider": "openrouter",
        "runtime_model": "anthropic/claude-3.5-haiku",
    },
    {
        "key": "openrouter_auto",
        "label": "OpenRouter Auto",
        "provider": "openrouter",
        "runtime_model": "openrouter/auto",
    },
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _backend_root_candidates() -> list[Path]:
    resolved = Path(__file__).resolve()
    candidates = [
        resolved.parents[2],
        resolved.parents[4] if len(resolved.parents) > 4 else resolved.parents[-1],
        Path.cwd(),
    ]
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _resolve_first_path(*relative_options: str) -> Path:
    for root in _backend_root_candidates():
        for relative in relative_options:
            candidate = root / relative
            if candidate.exists():
                return candidate
    return _backend_root_candidates()[0] / relative_options[0]


def legacy_knowledge_base_path() -> Path:
    return _resolve_first_path(
        "WHATSAPP_TOP_1000_QUESTIONS.json",
        "CHATBOT_TRAINING_DATA_CLEANED.json",
        "app/CHATBOT_TRAINING_DATA_CLEANED.json",
    )


def intent_knowledge_base_path() -> Path:
    path = _resolve_first_path(
        INTENT_KNOWLEDGE_FILENAME,
        f"app/{INTENT_KNOWLEDGE_FILENAME}",
    )
    if path.exists():
        return path

    preferred_root = Path.cwd()
    if preferred_root.exists():
        return preferred_root / INTENT_KNOWLEDGE_FILENAME
    return _backend_root_candidates()[-1] / INTENT_KNOWLEDGE_FILENAME


def knowledge_base_path() -> Path:
    intent_path = intent_knowledge_base_path()
    if intent_path.exists():
        return intent_path
    return legacy_knowledge_base_path()


def knowledge_base_write_path() -> Path:
    return intent_knowledge_base_path()


def product_catalog_path() -> Path:
    return _resolve_first_path(
        "app/ai/product_catalog.json",
        "anu-login/backend/app/ai/product_catalog.json",
    )


def _cert_candidates() -> list[tuple[str, Path]]:
    return [
        ("ai.pureleven.com", Path("/etc/letsencrypt/live/ai.pureleven.com/fullchain.pem")),
        ("ai.pureleven.com", Path("/etc/letsencrypt/live/ai.pureleven.com/cert.pem")),
    ]


def _decode_cert_dates(not_after_raw: str) -> datetime | None:
    if not not_after_raw:
        return None
    return datetime.strptime(not_after_raw, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)


def _remote_certificate_snapshot(domain: str) -> dict[str, Any]:
    context = ssl.create_default_context()
    with socket.create_connection((domain, 443), timeout=5) as sock:
        with context.wrap_socket(sock, server_hostname=domain) as tls_socket:
            decoded = tls_socket.getpeercert()

    not_after_raw = decoded.get("notAfter", "")
    expires_at = _decode_cert_dates(not_after_raw)
    now = datetime.now(timezone.utc)
    days_remaining = max((expires_at - now).days, 0) if expires_at else None
    return {
        "domain": domain,
        "dashboard_url": f"https://{domain}",
        "https_enabled": True,
        "certificate_found": True,
        "certificate_path": "remote_tls_handshake",
        "issuer": ", ".join(part[0][1] for part in decoded.get("issuer", []) if part),
        "subject": ", ".join(part[0][1] for part in decoded.get("subject", []) if part),
        "valid_from": decoded.get("notBefore", ""),
        "valid_until": not_after_raw,
        "expires_at": _format_datetime(expires_at),
        "days_remaining": days_remaining,
        "status": "healthy" if days_remaining is None or days_remaining > 14 else "expiring_soon",
    }


def _load_json_file(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_json_loads(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone(timezone.utc).isoformat()


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
    seen: set[str] = set()
    unique: list[str] = []
    for item in variants:
        if item in seen:
            continue
        seen.add(item)
        unique.append(item)
    return unique


def _entry_id(entry: dict[str, Any], fallback_index: int) -> str:
    if entry.get("id"):
        return str(entry["id"])
    seed = "||".join(
        [
            str(entry.get("product", "")),
            str(entry.get("intent", "") or entry.get("category", "")),
            str(entry.get("language", "")),
            str(entry.get("customer_input", "") or entry.get("question", "") or entry.get("answer_primary", "")),
            str(fallback_index),
        ]
    )
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()[:12]
    return f"kb-{digest}"


def _normalize_variations(value: Any) -> list[str]:
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = [segment.strip() for segment in value.replace("\n", ",").split(",")]
    else:
        items = []
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in items:
        text = str(item or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(text)
    return cleaned


def _normalize_tags(value: Any) -> list[str]:
    return _normalize_variations(value)


def _normalize_kb_product(value: Any) -> str:
    text = str(value or "").strip().lower()
    detected = detect_canonical_product(text.replace("_", " "))
    if detected:
        return detected
    cleaned = "".join(char if char.isalnum() else "_" for char in text)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "general"


def _default_kb_tone(language: str) -> str:
    return f"{language}_warm"


def _normalize_kb_language(value: Any, tone: str = "") -> str:
    language = str(value or "").strip().lower()
    if language in {"english", "manglish", "malayalam"}:
        return language
    return _language_from_tone(tone)


def _normalize_kb_intent(value: Any, category: Any = "") -> str:
    intent = str(value or category or "fallback").strip().lower().replace(" ", "_")
    intent = LEGACY_INTENT_ALIASES.get(intent, intent)
    if not intent:
        return "fallback"
    return intent


def _display_product_name(product_key: str, provided_name: str = "") -> str:
    canonical = get_canonical_product(product_key)
    if canonical and canonical.get("name"):
        return str(canonical.get("name"))
    if provided_name.strip():
        return provided_name.strip()
    if product_key == "general":
        return "General"
    return product_key.replace("_", " ").title()


def _normalize_trigger_examples(payload: dict[str, Any]) -> list[str]:
    collected: list[str] = []
    for key in ("trigger_examples", "examples"):
        value = payload.get(key)
        if isinstance(value, list):
            collected.extend(str(item or "").strip() for item in value)
        elif isinstance(value, str):
            collected.extend(segment.strip() for segment in value.splitlines())

    direct_example = str(payload.get("customer_input") or payload.get("question") or "").strip()
    if direct_example:
        collected.append(direct_example)

    collected.extend(_normalize_variations(payload.get("input_variations")))
    collected.extend(_normalize_variations(payload.get("alias_used")))

    seen: set[str] = set()
    normalized: list[str] = []
    for item in collected:
        text = str(item or "").strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(text)
    return normalized


def _build_intent_knowledge_entry(
    payload: dict[str, Any],
    *,
    entry_id: str | None = None,
    fallback_index: int = 0,
    source_kind: str = "intent_knowledge",
    source_entry_count: int | None = None,
) -> dict[str, Any]:
    tone = str(payload.get("tone") or "").strip()
    language = _normalize_kb_language(payload.get("language"), tone)
    intent = _normalize_kb_intent(payload.get("intent"), payload.get("category"))
    category = _normalize_kb_intent(payload.get("category"), intent)
    product = _normalize_kb_product(payload.get("product") or payload.get("product_key") or "general")
    product_name = _display_product_name(product, str(payload.get("product_name") or payload.get("display_name") or ""))
    trigger_examples = _normalize_trigger_examples(payload)
    answer_primary = str(payload.get("answer_primary") or payload.get("ideal_response") or payload.get("answer") or "").strip()
    answer_variants = _normalize_variations(payload.get("answer_variants"))
    follow_up = str(payload.get("follow_up") or "").strip()
    tags = _normalize_tags(payload.get("tags"))
    resolved_tone = tone or _default_kb_tone(language)

    if not trigger_examples:
        raise ValueError("At least one trigger example is required.")
    if not answer_primary:
        raise ValueError("Primary answer is required.")

    normalized = {
        "id": entry_id or str(payload.get("id") or ""),
        "category": category or intent,
        "intent": intent,
        "product": product,
        "product_name": product_name,
        "language": language,
        "tone": resolved_tone,
        "trigger_examples": trigger_examples,
        "examples": list(trigger_examples),
        "customer_input": trigger_examples[0],
        "input_variations": trigger_examples[1:],
        "example_count": len(trigger_examples),
        "answer_primary": answer_primary,
        "ideal_response": answer_primary,
        "answer_variants": [item for item in answer_variants if item.lower() != answer_primary.lower()],
        "follow_up": follow_up,
        "tags": tags,
        "needs_review": bool(payload.get("needs_review", False)),
        "review_reason": str(payload.get("review_reason") or "").strip(),
        "source_kind": source_kind,
        "source_entry_count": int(source_entry_count or payload.get("source_entry_count") or 1),
    }
    if not normalized["id"]:
        normalized["id"] = _entry_id(normalized, fallback_index)
    normalized["knowledge_key"] = f"{normalized['product']}::{normalized['intent']}::{normalized['language']}"
    normalized["display_title"] = f"{normalized['product_name']} • {normalized['intent'].replace('_', ' ')}"
    normalized["intent_supported"] = normalized["intent"] in SUPPORTED_INTENTS
    return normalized


def _knowledge_base_source_kind(path: Path) -> str:
    if path.name == INTENT_KNOWLEDGE_FILENAME:
        return "intent_knowledge"
    if path.name == "WHATSAPP_TOP_1000_QUESTIONS.json":
        return "top_1000_questions"
    return "cleaned_training_data"


def _language_from_tone(value: str) -> str:
    tone = str(value or "").strip().lower()
    if "malayalam" in tone:
        return "malayalam"
    if "manglish" in tone:
        return "manglish"
    return "english"


def _normalize_top_question_entry(raw_entry: dict[str, Any], fallback_index: int) -> dict[str, Any]:
    return _build_intent_knowledge_entry(
        {
            "id": str(raw_entry.get("id") or f"q{fallback_index:04d}"),
            "category": raw_entry.get("category") or raw_entry.get("intent") or "fallback",
            "intent": raw_entry.get("intent") or raw_entry.get("category") or "fallback",
            "product": raw_entry.get("product_key") or raw_entry.get("product") or "general",
            "product_name": raw_entry.get("product_name") or "",
            "customer_input": raw_entry.get("question") or raw_entry.get("customer_input") or "",
            "input_variations": raw_entry.get("input_variations") or [],
            "alias_used": raw_entry.get("alias_used") or "",
            "answer_primary": raw_entry.get("answer_primary") or raw_entry.get("ideal_response") or "",
            "answer_variants": raw_entry.get("answer_variants") or [],
            "language": raw_entry.get("language") or "",
            "tone": raw_entry.get("tone") or "",
            "follow_up": raw_entry.get("follow_up") or "",
            "tags": raw_entry.get("tags") or [],
            "needs_review": raw_entry.get("needs_review", False),
            "review_reason": raw_entry.get("review_reason") or "",
        },
        fallback_index=fallback_index,
        source_kind="top_1000_questions",
        source_entry_count=1,
    )


def _merge_intent_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for entry in entries:
        key = (
            str(entry.get("product") or "general"),
            str(entry.get("intent") or entry.get("category") or "fallback"),
            str(entry.get("language") or "english"),
        )
        if key not in grouped:
            grouped[key] = dict(entry)
            continue

        current = grouped[key]

        merged_examples = _normalize_variations(
            list(current.get("trigger_examples", [])) + list(entry.get("trigger_examples", []))
        )
        current["trigger_examples"] = merged_examples
        current["examples"] = list(merged_examples)
        current["customer_input"] = merged_examples[0] if merged_examples else current.get("customer_input", "")
        current["input_variations"] = merged_examples[1:] if len(merged_examples) > 1 else []
        current["example_count"] = len(merged_examples)

        answer_primary = str(current.get("answer_primary") or "").strip()
        incoming_answer = str(entry.get("answer_primary") or "").strip()
        merged_variants = _normalize_variations(
            list(current.get("answer_variants", []))
            + ([answer_primary] if answer_primary else [])
            + list(entry.get("answer_variants", []))
            + ([incoming_answer] if incoming_answer else [])
        )
        current["answer_primary"] = answer_primary or incoming_answer
        current["ideal_response"] = current["answer_primary"]
        current["answer_variants"] = [
            item for item in merged_variants if item.lower() != str(current["answer_primary"] or "").lower()
        ]

        current["tags"] = _normalize_tags(list(current.get("tags", [])) + list(entry.get("tags", [])))
        current["needs_review"] = bool(current.get("needs_review")) or bool(entry.get("needs_review"))

        review_reasons = _normalize_variations(
            [current.get("review_reason", ""), entry.get("review_reason", "")]
        )
        current["review_reason"] = " | ".join(review_reasons)

        current["follow_up"] = str(current.get("follow_up") or entry.get("follow_up") or "").strip()
        current["tone"] = str(current.get("tone") or entry.get("tone") or _default_kb_tone(current["language"])).strip()
        current["source_entry_count"] = int(current.get("source_entry_count") or 1) + int(entry.get("source_entry_count") or 1)
        current["source_kind"] = "aggregated_legacy_questions"

    return list(grouped.values())


def _serialize_knowledge_entry(entry: dict[str, Any], path: Path, next_index: int) -> dict[str, Any]:
    source_kind = _knowledge_base_source_kind(path)
    if source_kind == "intent_knowledge":
        return {
            "id": str(entry.get("id") or f"ikb-{next_index:04d}"),
            "product": str(entry.get("product") or "general").strip() or "general",
            "product_name": str(entry.get("product_name") or _display_product_name(str(entry.get("product") or "general"))),
            "category": str(entry.get("category") or entry.get("intent") or "fallback").strip() or "fallback",
            "intent": str(entry.get("intent") or entry.get("category") or "fallback").strip() or "fallback",
            "language": str(entry.get("language") or "english").strip() or "english",
            "tone": str(entry.get("tone") or _default_kb_tone(str(entry.get("language") or "english"))).strip(),
            "trigger_examples": list(entry.get("trigger_examples") or [entry.get("customer_input") or ""]),
            "answer_primary": str(entry.get("answer_primary") or entry.get("ideal_response") or "").strip(),
            "answer_variants": [str(item).strip() for item in entry.get("answer_variants", []) if str(item).strip()],
            "follow_up": str(entry.get("follow_up") or "").strip(),
            "tags": list(entry.get("tags") or []),
            "needs_review": bool(entry.get("needs_review", False)),
            "review_reason": str(entry.get("review_reason") or "").strip(),
            "source_entry_count": int(entry.get("source_entry_count") or 1),
        }

    if source_kind == "top_1000_questions":
        product_key = str(entry.get("product") or "general").strip().lower() or "general"
        product_name = str(entry.get("product_name") or entry.get("product") or "General").strip() or "General"
        tone_prefix = entry.get("language") or "english"
        tone = str(entry.get("tone") or f"{tone_prefix}_warm").strip()
        answer_variants = entry.get("answer_variants")
        if not isinstance(answer_variants, list):
            answer_variants = []
        trigger_examples = list(entry.get("trigger_examples") or [entry.get("customer_input") or ""])
        payload = {
            "id": str(entry.get("id") or f"q{next_index:04d}"),
            "product_key": product_key,
            "product_name": product_name,
            "alias_used": trigger_examples[0] if trigger_examples else "",
            "tone": tone,
            "category": entry["category"],
            "intent": str(entry.get("intent") or entry["category"]).strip() or entry["category"],
            "question": trigger_examples[0] if trigger_examples else "",
            "trigger_examples": trigger_examples,
            "answer_primary": entry.get("answer_primary") or entry["ideal_response"],
            "answer_variants": [str(item).strip() for item in answer_variants if str(item).strip()],
            "follow_up": str(entry.get("follow_up") or "").strip(),
            "tags": entry.get("tags") if isinstance(entry.get("tags"), list) else [product_key, entry["category"], tone_prefix],
            "input_variations": trigger_examples[1:],
            "needs_review": bool(entry.get("needs_review", False)),
            "review_reason": str(entry.get("review_reason") or "").strip(),
        }
        return payload

    payload = dict(entry)
    payload.pop("source_kind", None)
    payload.pop("display_title", None)
    payload.pop("knowledge_key", None)
    payload.pop("example_count", None)
    payload.pop("intent_supported", None)
    payload.pop("examples", None)
    payload.pop("product_name", None)
    payload.pop("answer_variants", None)
    payload.pop("follow_up", None)
    payload.pop("tone", None)
    payload.pop("intent", None)
    payload.pop("tags", None)
    return payload


def load_knowledge_base_entries(search: str = "", limit: int = 250) -> list[dict[str, Any]]:
    path = knowledge_base_path()
    payload = _load_json_file(path, [])
    source_kind = _knowledge_base_source_kind(path)
    entries: list[dict[str, Any]] = []
    for index, raw_entry in enumerate(payload, start=1):
        if not isinstance(raw_entry, dict):
            continue
        if source_kind == "top_1000_questions":
            entry = _normalize_top_question_entry(raw_entry, index)
        elif source_kind == "intent_knowledge":
            entry = _build_intent_knowledge_entry(
                raw_entry,
                entry_id=str(raw_entry.get("id") or ""),
                fallback_index=index,
                source_kind=source_kind,
            )
        else:
            entry = _build_intent_knowledge_entry(
                raw_entry,
                entry_id=str(raw_entry.get("id") or ""),
                fallback_index=index,
                source_kind=source_kind,
            )
        if search.strip():
            needle = search.strip().lower()
            haystack = " ".join(
                [
                    str(entry.get("product", "")),
                    str(entry.get("product_name", "")),
                    str(entry.get("intent", "")),
                    str(entry.get("category", "")),
                    str(entry.get("language", "")),
                    " ".join(entry.get("trigger_examples", [])),
                    str(entry.get("answer_primary", ""))[:200],
                    " ".join(entry.get("answer_variants", [])[:2]),
                    str(entry.get("follow_up", "")),
                    " ".join(entry.get("tags", [])),
                ]
            ).lower()
            if needle not in haystack:
                continue
        entries.append(entry)
    if source_kind == "top_1000_questions":
        entries = _merge_intent_entries(entries)
    entries.sort(
        key=lambda item: (
            str(item.get("product_name") or item.get("product") or "").lower(),
            str(item.get("intent") or item.get("category") or "").lower(),
            str(item.get("language") or "").lower(),
        )
    )
    return entries[:limit]


def save_knowledge_base_entry(payload: dict[str, Any], entry_id: str | None = None) -> dict[str, Any]:
    path = knowledge_base_write_path()
    existing = load_knowledge_base_entries(limit=5000)
    normalized = _build_intent_knowledge_entry(
        payload,
        entry_id=entry_id,
        source_kind="intent_knowledge",
    )

    updated = False
    for index, item in enumerate(existing):
        if item["id"] == normalized["id"]:
            existing[index] = normalized
            updated = True
            break

    if not updated:
        existing.insert(0, normalized)

    serialized = [
        _serialize_knowledge_entry(item, path, next_index=index)
        for index, item in enumerate(existing, start=1)
    ]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(serialized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    from app.ai.training_data_loader import reset_training_data_cache

    reset_training_data_cache()
    return normalized


def delete_knowledge_base_entry(entry_id: str) -> dict[str, Any]:
    path = knowledge_base_write_path()
    existing = load_knowledge_base_entries(limit=5000)
    remaining = [item for item in existing if item["id"] != entry_id]
    if len(remaining) == len(existing):
        raise ValueError("Knowledge base entry not found.")

    serialized = [
        _serialize_knowledge_entry(item, path, next_index=index)
        for index, item in enumerate(remaining, start=1)
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(serialized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    from app.ai.training_data_loader import reset_training_data_cache

    reset_training_data_cache()
    return {"ok": True, "deleted_id": entry_id}


def get_ai_control_settings() -> dict[str, Any]:
    raw_value = _get_setting_value(AI_CONTROL_KEY)
    payload = dict(DEFAULT_AI_CONTROL)
    if raw_value:
        try:
            parsed = json.loads(raw_value)
            if isinstance(parsed, dict):
                payload.update(parsed)
        except json.JSONDecodeError:
            pass

    model_keys = {option["key"] for option in MODEL_OPTIONS}
    if payload["selected_model"] not in model_keys:
        payload["selected_model"] = DEFAULT_AI_CONTROL["selected_model"]

    try:
        payload["temperature"] = max(0.0, min(1.0, float(payload.get("temperature", 0.25))))
    except (TypeError, ValueError):
        payload["temperature"] = DEFAULT_AI_CONTROL["temperature"]

    languages = payload.get("languages") or DEFAULT_AI_CONTROL["languages"]
    payload["languages"] = [str(item).strip().lower() for item in languages if str(item).strip()]
    if not payload["languages"]:
        payload["languages"] = list(DEFAULT_AI_CONTROL["languages"])

    payload["followup_send_enabled"] = bool(payload.get("followup_send_enabled", settings.ai_followup_send_enabled))
    payload["ai_running"] = bool(payload.get("ai_running", True))
    payload["server_orchestration_enabled"] = bool(
        payload.get("server_orchestration_enabled", DEFAULT_AI_CONTROL["server_orchestration_enabled"])
    )
    payload["flow_break_detection_enabled"] = bool(
        payload.get("flow_break_detection_enabled", DEFAULT_AI_CONTROL["flow_break_detection_enabled"])
    )
    payload["structured_button_passthrough_enabled"] = bool(
        payload.get(
            "structured_button_passthrough_enabled",
            DEFAULT_AI_CONTROL["structured_button_passthrough_enabled"],
        )
    )
    payload["wabis_fallback_when_disabled"] = bool(
        payload.get("wabis_fallback_when_disabled", DEFAULT_AI_CONTROL["wabis_fallback_when_disabled"])
    )
    try:
        payload["wabis_priority_minutes"] = max(
            1,
            min(30, int(payload.get("wabis_priority_minutes", DEFAULT_AI_CONTROL["wabis_priority_minutes"]))),
        )
    except (TypeError, ValueError):
        payload["wabis_priority_minutes"] = DEFAULT_AI_CONTROL["wabis_priority_minutes"]
    payload["available_models"] = [
        {
            **option,
            "available": bool(settings.gemini_api_key) if option["provider"] == "gemini" else bool(settings.openrouter_api_key),
        }
        for option in MODEL_OPTIONS
    ]
    return payload


def get_domain_certificate_status() -> dict[str, Any]:
    checked_paths: list[str] = []
    domain = _cert_candidates()[0][0]

    try:
        snapshot = _remote_certificate_snapshot(domain)
        snapshot["checked_paths"] = checked_paths
        return snapshot
    except Exception as exc:
        remote_error = str(exc)

    for domain, cert_path in _cert_candidates():
        checked_paths.append(str(cert_path))
        try:
            path_exists = cert_path.exists()
        except PermissionError:
            continue

        if not path_exists:
            continue
        try:
            decoded = ssl._ssl._test_decode_cert(str(cert_path))
            not_after_raw = decoded.get("notAfter", "")
            expires_at = _decode_cert_dates(not_after_raw)
            now = datetime.now(timezone.utc)
            days_remaining = max((expires_at - now).days, 0) if expires_at else None
            return {
                "domain": domain,
                "dashboard_url": f"https://{domain}",
                "https_enabled": True,
                "certificate_found": True,
                "certificate_path": str(cert_path),
                "issuer": ", ".join(part[0][1] for part in decoded.get("issuer", []) if part),
                "subject": ", ".join(part[0][1] for part in decoded.get("subject", []) if part),
                "valid_from": decoded.get("notBefore", ""),
                "valid_until": not_after_raw,
                "expires_at": _format_datetime(expires_at),
                "days_remaining": days_remaining,
                "status": "healthy" if days_remaining is None or days_remaining > 14 else "expiring_soon",
                "checked_paths": checked_paths,
            }
        except Exception as exc:
            return {
                "domain": domain,
                "dashboard_url": f"https://{domain}",
                "https_enabled": True,
                "certificate_found": True,
                "certificate_path": str(cert_path),
                "status": "error",
                "error": str(exc),
                "checked_paths": checked_paths,
            }

    return {
        "domain": "ai.pureleven.com",
        "dashboard_url": "https://ai.pureleven.com",
        "https_enabled": False,
        "certificate_found": False,
        "certificate_path": "",
        "status": "missing",
        "error": remote_error,
        "checked_paths": checked_paths,
    }


def save_ai_control_settings(payload: dict[str, Any]) -> dict[str, Any]:
    current = get_ai_control_settings()
    merged = {
        "ai_running": bool(payload.get("ai_running", current["ai_running"])),
        "server_orchestration_enabled": bool(
            payload.get("server_orchestration_enabled", current["server_orchestration_enabled"])
        ),
        "flow_break_detection_enabled": bool(
            payload.get("flow_break_detection_enabled", current["flow_break_detection_enabled"])
        ),
        "structured_button_passthrough_enabled": bool(
            payload.get(
                "structured_button_passthrough_enabled",
                current["structured_button_passthrough_enabled"],
            )
        ),
        "wabis_fallback_when_disabled": bool(
            payload.get("wabis_fallback_when_disabled", current["wabis_fallback_when_disabled"])
        ),
        "wabis_priority_minutes": payload.get("wabis_priority_minutes", current["wabis_priority_minutes"]),
        "selected_model": str(payload.get("selected_model", current["selected_model"])),
        "temperature": payload.get("temperature", current["temperature"]),
        "languages": payload.get("languages", current["languages"]),
        "followup_send_enabled": bool(payload.get("followup_send_enabled", current["followup_send_enabled"])),
        "updated_at": _now_iso(),
    }
    normalized = get_ai_control_settings()
    normalized.update(merged)
    _save_setting_value(
        AI_CONTROL_KEY,
        json.dumps(
            {
                "ai_running": normalized["ai_running"],
                "server_orchestration_enabled": normalized["server_orchestration_enabled"],
                "flow_break_detection_enabled": normalized["flow_break_detection_enabled"],
                "structured_button_passthrough_enabled": normalized["structured_button_passthrough_enabled"],
                "wabis_fallback_when_disabled": normalized["wabis_fallback_when_disabled"],
                "wabis_priority_minutes": normalized["wabis_priority_minutes"],
                "selected_model": normalized["selected_model"],
                "temperature": normalized["temperature"],
                "languages": normalized["languages"],
                "followup_send_enabled": normalized["followup_send_enabled"],
                "updated_at": normalized["updated_at"],
            },
            ensure_ascii=False,
        ),
    )
    return get_ai_control_settings()


def is_ai_running() -> bool:
    return bool(get_ai_control_settings().get("ai_running", True))


def is_server_orchestration_enabled() -> bool:
    """Return True when PureLeven backend should make instant WhatsApp routing decisions."""
    return bool(get_ai_control_settings().get("server_orchestration_enabled", True))


def _score_to_label(score: int, purchase_count: int = 0) -> str:
    if purchase_count > 0:
        return "purchased"
    if score >= 80:
        return "hot"
    if score >= 50:
        return "warm"
    return "cold"


def _label_badge(label: str) -> str:
    return {
        "hot": "hot",
        "warm": "warm",
        "cold": "cold",
        "purchased": "purchased",
    }.get((label or "").lower(), "cold")


def _safe_fetchone(connection, query: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    row = connection.execute(query, params).fetchone()
    return dict(row) if row else {}


def _build_recent_conversations(connection, today_iso: str, limit: int = 8) -> list[dict[str, Any]]:
    if not (_table_exists(connection, "conversation_sessions") and _table_exists(connection, "conversation_messages")):
        return []

    rows = connection.execute(
        """
        WITH ranked AS (
            SELECT
                cs.customer_phone AS phone,
                COALESCE(jc.name, cs.customer_phone, 'Unknown') AS customer_name,
                COALESCE(jc.engagement_score, 0) AS engagement_score,
                COALESCE(jc.purchase_count, 0) AS purchase_count,
                cm.customer_text AS asked,
                cm.created_at AS asked_at,
                ROW_NUMBER() OVER (PARTITION BY cs.customer_phone ORDER BY cm.created_at DESC) AS rn
            FROM conversation_sessions cs
            JOIN conversation_messages cm ON cm.session_id = cs.id
            LEFT JOIN journey_customers jc ON jc.id = cs.customer_id
            WHERE cm.actor = 'customer'
              AND substr(cm.created_at, 1, 10) = ?
        )
        SELECT phone, customer_name, engagement_score, purchase_count, asked, asked_at
        FROM ranked
        WHERE rn = 1
        ORDER BY asked_at DESC
        LIMIT ?
        """,
        (today_iso, limit),
    ).fetchall()

    conversations: list[dict[str, Any]] = []
    for row in rows:
        score = int(float(row["engagement_score"] or 0))
        purchase_count = int(row["purchase_count"] or 0)
        label = _score_to_label(score, purchase_count)
        conversations.append(
            {
                "phone": row["phone"],
                "customer_name": row["customer_name"] or "Unknown",
                "asked": row["asked"] or "New message",
                "asked_at": row["asked_at"],
                "score": score,
                "label": label,
                "badge": _label_badge(label),
            }
        )
    return conversations


def _build_counts(connection, today_iso: str) -> dict[str, int]:
    if _table_exists(connection, "customers"):
        row = _safe_fetchone(
            connection,
            """
            SELECT
                SUM(CASE WHEN LOWER(COALESCE(engagement_label, '')) = 'hot' THEN 1 ELSE 0 END) AS hot,
                SUM(CASE WHEN LOWER(COALESCE(engagement_label, '')) = 'warm' THEN 1 ELSE 0 END) AS warm,
                SUM(CASE WHEN LOWER(COALESCE(engagement_label, '')) = 'cold' THEN 1 ELSE 0 END) AS cold,
                SUM(CASE WHEN LOWER(COALESCE(purchase_status, '')) = 'purchased' THEN 1 ELSE 0 END) AS purchased,
                SUM(CASE WHEN LOWER(COALESCE(purchase_status, '')) = 'purchased' AND substr(COALESCE(last_order_date, created_at, ''), 1, 10) = ? THEN 1 ELSE 0 END) AS orders_today
            FROM customers
            WHERE deleted_at IS NULL
            """,
            (today_iso,),
        )
        return {
            "hot": int(row.get("hot") or 0),
            "warm": int(row.get("warm") or 0),
            "cold": int(row.get("cold") or 0),
            "purchased": int(row.get("purchased") or 0),
            "orders_today": int(row.get("orders_today") or 0),
        }

    if _table_exists(connection, "journey_customers"):
        row = _safe_fetchone(
            connection,
            """
            SELECT
                SUM(CASE WHEN COALESCE(purchase_count, 0) > 0 THEN 1 ELSE 0 END) AS purchased,
                SUM(CASE WHEN COALESCE(purchase_count, 0) = 0 AND COALESCE(engagement_score, 0) >= 80 THEN 1 ELSE 0 END) AS hot,
                SUM(CASE WHEN COALESCE(purchase_count, 0) = 0 AND COALESCE(engagement_score, 0) >= 50 AND COALESCE(engagement_score, 0) < 80 THEN 1 ELSE 0 END) AS warm,
                SUM(CASE WHEN COALESCE(purchase_count, 0) = 0 AND COALESCE(engagement_score, 0) < 50 THEN 1 ELSE 0 END) AS cold,
                SUM(CASE WHEN COALESCE(purchase_count, 0) > 0 AND substr(COALESCE(last_purchase_at, updated_at, ''), 1, 10) = ? THEN 1 ELSE 0 END) AS orders_today
            FROM journey_customers
            """,
            (today_iso,),
        )
        return {
            "hot": int(row.get("hot") or 0),
            "warm": int(row.get("warm") or 0),
            "cold": int(row.get("cold") or 0),
            "purchased": int(row.get("purchased") or 0),
            "orders_today": int(row.get("orders_today") or 0),
        }

    return {"hot": 0, "warm": 0, "cold": 0, "purchased": 0, "orders_today": 0}


def get_owner_dashboard_summary() -> dict[str, Any]:
    init_database()
    today_iso = datetime.now(timezone.utc).date().isoformat()
    seven_days_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    ai_control = get_ai_control_settings()
    kb_entries = load_knowledge_base_entries(limit=5000)

    with get_db_connection() as connection:
        counts = _build_counts(connection, today_iso)
        recent_conversations = _build_recent_conversations(connection, today_iso)

        chats_today = 0
        if _table_exists(connection, "conversation_messages") and _table_exists(connection, "conversation_sessions"):
            chat_row = _safe_fetchone(
                connection,
                """
                SELECT COUNT(DISTINCT cs.customer_phone) AS chats_today
                FROM conversation_sessions cs
                JOIN conversation_messages cm ON cm.session_id = cs.id
                WHERE cm.actor = 'customer' AND substr(cm.created_at, 1, 10) = ?
                """,
                (today_iso,),
            )
            chats_today = int(chat_row.get("chats_today") or 0)

        active_sessions = 0
        if _table_exists(connection, "conversation_sessions"):
            active_row = _safe_fetchone(
                connection,
                "SELECT COUNT(*) AS active_sessions FROM conversation_sessions WHERE is_active = 1",
            )
            active_sessions = int(active_row.get("active_sessions") or 0)

        ai_success_rate = 0
        ai_generated = 0
        if _table_exists(connection, "ai_outgoing_replies"):
            ai_row = _safe_fetchone(
                connection,
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN send_status IN ('sent', 'logged', 'pending') THEN 1 ELSE 0 END) AS successful
                FROM ai_outgoing_replies
                WHERE created_at >= ?
                """,
                (seven_days_ago,),
            )
            ai_generated = int(ai_row.get("total") or 0)
            successful = int(ai_row.get("successful") or 0)
            ai_success_rate = round((successful / ai_generated) * 100) if ai_generated else 0

        unresolved_gaps = 0
        if _table_exists(connection, "knowledge_gaps"):
            gap_row = _safe_fetchone(
                connection,
                "SELECT COUNT(*) AS unresolved FROM knowledge_gaps WHERE resolved_by IS NULL",
            )
            unresolved_gaps = int(gap_row.get("unresolved") or 0)

        needs_review = sum(1 for entry in kb_entries if entry.get("needs_review"))

    return {
        "ai_status": {
            "running": ai_control["ai_running"],
            "server_orchestration_enabled": ai_control["server_orchestration_enabled"],
            "flow_break_detection_enabled": ai_control["flow_break_detection_enabled"],
            "structured_button_passthrough_enabled": ai_control["structured_button_passthrough_enabled"],
            "wabis_fallback_when_disabled": ai_control["wabis_fallback_when_disabled"],
            "wabis_priority_minutes": ai_control["wabis_priority_minutes"],
            "selected_model": ai_control["selected_model"],
            "temperature": ai_control["temperature"],
            "languages": ai_control["languages"],
            "followup_send_enabled": ai_control["followup_send_enabled"],
            "available_models": ai_control["available_models"],
        },
        "metrics": {
            "today_chats": chats_today,
            "hot_leads": counts["hot"],
            "orders_generated": counts["orders_today"],
            "ai_success_rate": ai_success_rate,
            "warm_leads": counts["warm"],
            "cold_leads": counts["cold"],
            "purchased": counts["purchased"],
            "active_sessions": active_sessions,
            "trained_questions": len(kb_entries),
            "needs_fixing": unresolved_gaps + needs_review,
            "ai_generated_last_7d": ai_generated,
        },
        "recent_conversations": recent_conversations,
    }


def list_dashboard_customers(search: str = "", label: str = "all", limit: int = 100) -> list[dict[str, Any]]:
    init_database()
    with get_db_connection() as connection:
        items: list[dict[str, Any]] = []
        if _table_exists(connection, "customers"):
            rows = connection.execute(
                """
                SELECT id, name, phone, email, COALESCE(lead_score, 0) AS lead_score,
                       COALESCE(engagement_label, 'cold') AS engagement_label,
                       COALESCE(purchase_status, 'not_purchased') AS purchase_status,
                       COALESCE(last_order_date, last_engagement_at, created_at) AS updated_at
                FROM customers
                WHERE deleted_at IS NULL
                ORDER BY COALESCE(lead_score, 0) DESC, updated_at DESC
                LIMIT ?
                """,
                (limit * 3,),
            ).fetchall()
            for row in rows:
                item = dict(row)
                text_blob = " ".join([str(item.get("name", "")), str(item.get("phone", "")), str(item.get("email", ""))]).lower()
                current_label = "purchased" if item.get("purchase_status") == "purchased" else str(item.get("engagement_label") or "cold").lower()
                if search.strip() and search.strip().lower() not in text_blob:
                    continue
                if label != "all" and current_label != label:
                    continue
                items.append(
                    {
                        "id": str(item.get("id") or ""),
                        "phone": item.get("phone") or "",
                        "name": item.get("name") or "Unknown",
                        "email": item.get("email") or "",
                        "label": current_label,
                        "score": int(item.get("lead_score") or 0),
                        "stage": "Purchased" if current_label == "purchased" else current_label.title(),
                        "updated_at": item.get("updated_at") or "",
                    }
                )

        if _table_exists(connection, "journey_customers"):
            rows = connection.execute(
                """
                SELECT id, phone, name, email, journey_stage, engagement_score, purchase_count, updated_at
                FROM journey_customers
                ORDER BY COALESCE(engagement_score, 0) DESC, updated_at DESC
                LIMIT ?
                """,
                (limit * 3,),
            ).fetchall()
            for row in rows:
                item = dict(row)
                text_blob = " ".join([str(item.get("name", "")), str(item.get("phone", "")), str(item.get("email", ""))]).lower()
                score = int(float(item.get("engagement_score") or 0))
                purchase_count = int(item.get("purchase_count") or 0)
                current_label = _score_to_label(score, purchase_count)
                if search.strip() and search.strip().lower() not in text_blob:
                    continue
                if label != "all" and current_label != label:
                    continue
                items.append(
                    {
                        "id": str(item.get("id") or ""),
                        "phone": item.get("phone") or "",
                        "name": item.get("name") or "Unknown",
                        "email": item.get("email") or "",
                        "label": current_label,
                        "score": score,
                        "stage": item.get("journey_stage") or current_label.title(),
                        "updated_at": item.get("updated_at") or "",
                    }
                )

        runtime_by_phone: dict[str, dict[str, Any]] = {
            str(item.get("phone") or ""): item for item in items if item.get("phone")
        }

        def upsert_runtime_customer(phone: str, *, name: str = "", score: int = 0, stage: str = "", updated_at: str = "", label_hint: str = "") -> None:
            normalized_phone = str(phone or "").strip()
            if not normalized_phone:
                return
            existing = runtime_by_phone.get(normalized_phone, {})
            current_score = max(int(existing.get("score") or 0), int(score or 0))
            current_label = label_hint or existing.get("label") or _score_to_label(current_score)
            display_name = str(existing.get("name") or name or "Unknown").strip() or "Unknown"
            if display_name == "Unknown" and name:
                display_name = str(name).strip() or "Unknown"
            runtime_by_phone[normalized_phone] = {
                "id": existing.get("id") or normalized_phone,
                "phone": normalized_phone,
                "name": display_name,
                "email": existing.get("email") or "",
                "label": current_label,
                "score": current_score,
                "stage": stage or existing.get("stage") or current_label.title(),
                "updated_at": max(str(existing.get("updated_at") or ""), str(updated_at or "")),
            }

        if _table_exists(connection, "conversation_state"):
            rows = connection.execute(
                """
                SELECT phone, owner, flow_step, latest_intent, active_product,
                       journey_stage, last_activity, updated_at
                FROM conversation_state
                ORDER BY COALESCE(last_activity, updated_at, created_at) DESC
                LIMIT ?
                """,
                (limit * 5,),
            ).fetchall()
            for row in rows:
                state = dict(row)
                intent = str(state.get("latest_intent") or "").lower()
                score = 70 if intent in {"order_request", "payment", "price"} else 45
                stage = state.get("journey_stage") or state.get("flow_step") or state.get("owner") or "Runtime"
                updated = state.get("last_activity") or state.get("updated_at") or ""
                upsert_runtime_customer(state.get("phone"), score=score, stage=stage, updated_at=updated, label_hint=_score_to_label(score))

        if _table_exists(connection, "ai_incoming_messages"):
            for row in connection.execute(
                """
                SELECT customer_phone, MAX(created_at) AS updated_at, COUNT(*) AS message_count
                FROM ai_incoming_messages
                GROUP BY customer_phone
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit * 5,),
            ).fetchall():
                score = min(75, 25 + int(row["message_count"] or 0) * 8)
                upsert_runtime_customer(row["customer_phone"], score=score, stage="Customer Messages", updated_at=row["updated_at"], label_hint=_score_to_label(score))

        if _table_exists(connection, "ai_outgoing_replies"):
            for row in connection.execute(
                """
                SELECT customer_phone, MAX(created_at) AS updated_at, COUNT(*) AS reply_count
                FROM ai_outgoing_replies
                GROUP BY customer_phone
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit * 5,),
            ).fetchall():
                score = min(80, 30 + int(row["reply_count"] or 0) * 10)
                upsert_runtime_customer(row["customer_phone"], score=score, stage="AI Conversation", updated_at=row["updated_at"], label_hint=_score_to_label(score))

        if _table_exists(connection, "message_decisions"):
            for row in connection.execute(
                """
                SELECT customer_id, MAX(created_at) AS updated_at,
                       MAX(detected_intent) AS intent, MAX(selected_owner) AS owner, COUNT(*) AS decision_count
                FROM message_decisions
                GROUP BY customer_id
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (limit * 5,),
            ).fetchall():
                score = min(85, 35 + int(row["decision_count"] or 0) * 8)
                stage = " / ".join(part for part in (row["owner"], row["intent"]) if part)
                upsert_runtime_customer(row["customer_id"], score=score, stage=stage or "Message Decisions", updated_at=row["updated_at"], label_hint=_score_to_label(score))

        merged_items = list(runtime_by_phone.values())
        filtered: list[dict[str, Any]] = []
        for item in merged_items:
            text_blob = " ".join([str(item.get("name", "")), str(item.get("phone", "")), str(item.get("email", "")), str(item.get("stage", ""))]).lower()
            current_label = str(item.get("label") or "cold").lower()
            if search.strip() and search.strip().lower() not in text_blob:
                continue
            if label != "all" and current_label != label:
                continue
            filtered.append(item)
        filtered.sort(key=lambda item: (int(item.get("score") or 0), str(item.get("updated_at") or "")), reverse=True)
        return filtered[:limit]


def get_customer_timeline(customer_ref: str) -> dict[str, Any]:
    init_database()
    with get_db_connection() as connection:
        customer: dict[str, Any] | None = None
        if _table_exists(connection, "journey_customers"):
            row = connection.execute(
                "SELECT * FROM journey_customers WHERE id = ? OR phone = ? LIMIT 1",
                (customer_ref, customer_ref),
            ).fetchone()
            if row:
                customer = dict(row)

        phone = customer.get("phone") if customer else customer_ref
        customer_id = customer.get("id") if customer else None

        timeline: list[dict[str, Any]] = []

        if _table_exists(connection, "conversation_sessions") and _table_exists(connection, "conversation_messages"):
            if customer_id:
                message_rows = connection.execute(
                    """
                    SELECT cm.created_at, cm.actor, cm.customer_text, cm.message_rendered, cm.message_type, cm.delivery_status
                    FROM conversation_sessions cs
                    JOIN conversation_messages cm ON cm.session_id = cs.id
                    WHERE cs.customer_id = ? OR cs.customer_phone = ?
                    ORDER BY cm.created_at DESC
                    LIMIT 200
                    """,
                    (customer_id, phone),
                ).fetchall()
            else:
                message_rows = connection.execute(
                    """
                    SELECT cm.created_at, cm.actor, cm.customer_text, cm.message_rendered, cm.message_type, cm.delivery_status
                    FROM conversation_sessions cs
                    JOIN conversation_messages cm ON cm.session_id = cs.id
                    WHERE cs.customer_phone = ?
                    ORDER BY cm.created_at DESC
                    LIMIT 200
                    """,
                    (phone,),
                ).fetchall()
            for row in message_rows:
                timeline.append(
                    {
                        "at": row["created_at"],
                        "type": "customer_message" if row["actor"] == "customer" else "assistant_message",
                        "text": row["customer_text"] or row["message_rendered"] or row["message_type"] or "",
                        "status": row["delivery_status"] or "",
                    }
                )

        if _table_exists(connection, "ai_outgoing_replies"):
            for row in connection.execute(
                """
                SELECT created_at, reply_text, intent, send_status
                FROM ai_outgoing_replies
                WHERE customer_phone = ?
                ORDER BY created_at DESC
                LIMIT 100
                """,
                (phone,),
            ).fetchall():
                timeline.append(
                    {
                        "at": row["created_at"],
                        "type": "ai_reply",
                        "text": row["reply_text"],
                        "status": row["send_status"],
                        "intent": row["intent"],
                    }
                )

        if _table_exists(connection, "ai_incoming_messages"):
            for row in connection.execute(
                """
                SELECT created_at, body, message_type, conversation_id
                FROM ai_incoming_messages
                WHERE customer_phone = ?
                ORDER BY created_at DESC
                LIMIT 100
                """,
                (phone,),
            ).fetchall():
                timeline.append(
                    {
                        "at": row["created_at"],
                        "type": "customer_message",
                        "text": row["body"] or row["message_type"] or "",
                        "status": row["conversation_id"] or "",
                    }
                )

        if _table_exists(connection, "message_decisions"):
            for row in connection.execute(
                """
                SELECT created_at, incoming_message, detected_type, detected_intent,
                       selected_owner, decision_reason, skipped_ai, score
                FROM message_decisions
                WHERE customer_id = ?
                ORDER BY created_at DESC
                LIMIT 100
                """,
                (phone,),
            ).fetchall():
                timeline.append(
                    {
                        "at": row["created_at"],
                        "type": "message_decision",
                        "text": row["incoming_message"] or row["detected_type"] or "",
                        "status": f"{row['selected_owner'] or ''} • {'AI skipped' if row['skipped_ai'] else 'AI allowed'}",
                        "intent": " / ".join(part for part in (row["detected_intent"], row["decision_reason"], f"score {row['score']}" if row["score"] else "") if part),
                    }
                )

        if _table_exists(connection, "routing_log"):
            for row in connection.execute(
                """
                SELECT timestamp, message, route_taken, context
                FROM routing_log
                WHERE phone = ?
                ORDER BY timestamp DESC
                LIMIT 100
                """,
                (phone,),
            ).fetchall():
                timeline.append(
                    {
                        "at": row["timestamp"],
                        "type": "routing_decision",
                        "text": row["message"] or "",
                        "status": row["route_taken"] or "",
                        "intent": row["context"] or "",
                    }
                )

        if _table_exists(connection, "ai_reply_jobs"):
            for row in connection.execute(
                """
                SELECT created_at, updated_at, status, delay_type, source_message,
                       skipped_reason, result_json
                FROM ai_reply_jobs
                WHERE customer_phone = ?
                ORDER BY created_at DESC
                LIMIT 100
                """,
                (phone,),
            ).fetchall():
                timeline.append(
                    {
                        "at": row["updated_at"] or row["created_at"],
                        "type": "ai_queue_job",
                        "text": row["source_message"] or row["delay_type"] or "",
                        "status": " ".join(
                            part
                            for part in (row["status"], row["skipped_reason"])
                            if part
                        ),
                        "intent": row["delay_type"] or "",
                    }
                )

        if _table_exists(connection, "ai_decision_logs"):
            for row in connection.execute(
                """
                SELECT created_at, incoming_message, detected_product, detected_intent,
                       matched_template, generated_response, final_route_owner
                FROM ai_decision_logs
                WHERE customer_phone = ?
                ORDER BY created_at DESC
                LIMIT 100
                """,
                (phone,),
            ).fetchall():
                product_intent = " / ".join(
                    part
                    for part in (row["detected_product"], row["detected_intent"])
                    if part
                )
                timeline.append(
                    {
                        "at": row["created_at"],
                        "type": "ai_decision",
                        "text": row["generated_response"] or row["incoming_message"] or "",
                        "status": row["final_route_owner"] or row["matched_template"] or "",
                        "intent": product_intent,
                    }
                )

        if _table_exists(connection, "product_journey_followups"):
            for row in connection.execute(
                """
                SELECT scheduled_at, sent_at, followup_stage, reply_text, send_status
                FROM product_journey_followups
                WHERE phone = ?
                ORDER BY scheduled_at DESC
                LIMIT 50
                """,
                (phone,),
            ).fetchall():
                timeline.append(
                    {
                        "at": row["sent_at"] or row["scheduled_at"],
                        "type": "followup",
                        "text": row["reply_text"] or row["followup_stage"],
                        "status": row["send_status"],
                    }
                )

        if _table_exists(connection, "customer_journey_logs"):
            for row in connection.execute(
                """
                SELECT created_at, event_type, product_key, message_text, metadata_json
                FROM customer_journey_logs
                WHERE customer_phone = ?
                ORDER BY created_at DESC
                LIMIT 100
                """,
                (phone,),
            ).fetchall():
                timeline.append(
                    {
                        "at": row["created_at"],
                        "type": "journey_event",
                        "text": row["message_text"] or row["product_key"] or "",
                        "status": row["event_type"] or "",
                        "intent": row["product_key"] or "",
                    }
                )

        if _table_exists(connection, "knowledge_gaps"):
            for row in connection.execute(
                """
                SELECT created_at, original_query, detected_intent, resolved_by
                FROM knowledge_gaps
                WHERE phone = ?
                ORDER BY created_at DESC
                LIMIT 30
                """,
                (phone,),
            ).fetchall():
                timeline.append(
                    {
                        "at": row["created_at"],
                        "type": "knowledge_gap",
                        "text": row["original_query"],
                        "status": row["resolved_by"] or "open",
                        "intent": row["detected_intent"] or "",
                    }
                )

        state_summary: dict[str, Any] | None = None
        if _table_exists(connection, "conversation_state"):
            state_row = connection.execute(
                """
                SELECT owner, owner_reason, flow_id, flow_step, expected_responses,
                       started_at, expires_at, last_activity, context_json, updated_at
                FROM conversation_state
                WHERE phone = ?
                LIMIT 1
                """,
                (phone,),
            ).fetchone()
            if state_row:
                context = json.loads(state_row["context_json"] or "{}") if state_row["context_json"] else {}
                latent = context.get("latent_handoff") if isinstance(context, dict) else None
                state_summary = {
                    "owner": state_row["owner"],
                    "owner_reason": state_row["owner_reason"] or "",
                    "flow_id": state_row["flow_id"] or "",
                    "flow_step": state_row["flow_step"] or "",
                    "expected_responses": state_row["expected_responses"] or "",
                    "started_at": state_row["started_at"] or "",
                    "expires_at": state_row["expires_at"] or "",
                    "last_activity": state_row["last_activity"] or "",
                    "updated_at": state_row["updated_at"] or "",
                    "context": context,
                    "latent_handoff": latent if isinstance(latent, dict) else None,
                }

        queued_followups: list[dict[str, Any]] = []
        if _table_exists(connection, "product_journey_followups"):
            for row in connection.execute(
                """
                SELECT followup_stage, scheduled_at, send_status, product_key
                FROM product_journey_followups
                WHERE phone = ? AND sent = 0 AND send_status = 'queued'
                ORDER BY scheduled_at ASC
                LIMIT 20
                """,
                (phone,),
            ).fetchall():
                queued_followups.append(dict(row))

    timeline.sort(key=lambda item: item.get("at") or "", reverse=True)
    return {
        "customer": customer
        or {
            "id": "",
            "phone": phone,
            "name": "Unknown",
            "email": "",
        },
        "timeline": timeline[:200],
        "current_state": state_summary,
        "queued_followups": queued_followups,
    }


def get_training_gaps(limit: int = 30) -> dict[str, list[dict[str, Any]]]:
    init_database()
    with get_db_connection() as connection:
        gaps: list[dict[str, Any]] = []
        if _table_exists(connection, "knowledge_gaps"):
            for row in connection.execute(
                """
                SELECT id, phone, original_query, detected_intent, detected_product,
                       confidence, reason, status, admin_label, correct_response, created_at, updated_at
                FROM knowledge_gaps
                WHERE resolved_by IS NULL
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall():
                gaps.append(dict(row))

        missing_products: list[dict[str, Any]] = []
        if _table_exists(connection, "missing_products"):
            for row in connection.execute(
                """
                SELECT product_name, search_count, last_searched, added_to_catalog
                FROM missing_products
                ORDER BY search_count DESC, last_searched DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall():
                missing_products.append(dict(row))

    return {
        "knowledge_gaps": gaps,
        "missing_products": missing_products,
    }


def get_product_catalog_payload() -> dict[str, Any]:
    payload = canonical_dashboard_payload()
    return {
        "products": payload.get("products", []),
        "combos": payload.get("combos", []),
        "media_sync": {
            "default_drive_folder_url": PRODUCT_IMAGE_DRIVE_FOLDER_URL,
        },
    }


def _slugify_product_key(value: str) -> str:
    text = str(value or "").strip().lower()
    cleaned = "".join(char if char.isalnum() else "_" for char in text)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "product"


def _normalize_product_aliases(value: Any, display_name: str) -> list[str]:
    aliases = _normalize_variations(value)
    base = display_name.strip()
    if base and base.lower() not in {item.lower() for item in aliases}:
        aliases.insert(0, base)
    return aliases


def _normalize_product_lookup_key(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else " " for char in str(value or "").strip())
    return " ".join(cleaned.split())


def _catalog_lookup_aliases(product: dict[str, Any]) -> set[str]:
    aliases: set[str] = set()
    product_key = str(product.get("product_key") or product.get("id") or "").strip()
    display_name = str(product.get("display_name") or product.get("name") or "").strip()
    if product_key:
        aliases.add(_normalize_product_lookup_key(product_key))
        aliases.add(_normalize_product_lookup_key(product_key.replace("_", " ")))
    if display_name:
        aliases.add(_normalize_product_lookup_key(display_name))
    for alias in product.get("aliases", []) or []:
        aliases.add(_normalize_product_lookup_key(str(alias)))
    return {alias for alias in aliases if alias}


def _normalize_recommendation_block(value: Any) -> dict[str, str]:
    payload = value if isinstance(value, dict) else {}
    return {
        "english": str(payload.get("english") or "").strip(),
        "manglish": str(payload.get("manglish") or "").strip(),
        "malayalam": str(payload.get("malayalam") or "").strip(),
    }


def _normalize_product_variants(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    items: list[dict[str, Any]] = []
    for variant in value:
        if not isinstance(variant, dict):
            continue
        size = str(variant.get("size") or "").strip()
        if not size:
            continue
        try:
            price = int(float(variant.get("price") or 0))
        except (TypeError, ValueError):
            price = 0
        items.append(
            {
                "size": size,
                "price": price,
                "delivery": str(variant.get("delivery") or "").strip(),
            }
        )
    return items


def _normalize_product_entry(payload: dict[str, Any], existing_key: str | None = None) -> dict[str, Any]:
    display_name = str(payload.get("display_name") or payload.get("name") or "").strip()
    if not display_name:
        raise ValueError("Product name is required.")
    product_key = _slugify_product_key(existing_key or payload.get("product_key") or payload.get("id") or display_name)
    variants = _normalize_product_variants(payload.get("variants"))
    if not variants:
        raise ValueError("At least one product variant is required.")
    return {
        "id": product_key,
        "name": display_name,
        "aliases": _normalize_product_aliases(payload.get("aliases"), display_name),
        "origin": str(payload.get("origin") or "").strip(),
        "story": str(payload.get("story") or payload.get("description") or "").strip(),
        "quality": str(payload.get("quality") or "").strip(),
        "use_cases": _normalize_variations(payload.get("use_cases")),
        "recommended_pack": str(payload.get("recommended_pack") or "").strip(),
        "sizes": [{"size": item["size"], "price": item["price"]} for item in variants],
        "media_links": normalize_product_image_entries(payload.get("images") or payload.get("media_links", [])),
    }


def save_product_catalog_entry(payload: dict[str, Any], product_key: str | None = None) -> dict[str, Any]:
    path = product_catalog_path()
    catalog = _load_json_file(path, {"products": [], "combos": []})
    products = [item for item in catalog.get("products", []) if isinstance(item, dict)]
    existing_product: dict[str, Any] | None = None
    if product_key:
        existing_product = next(
            (
                item
                for item in products
                if str(item.get("id") or item.get("product_key") or "") == product_key
            ),
            None,
        )
    if existing_product and not payload.get("images") and not payload.get("media_links"):
        payload = dict(payload)
        payload["images"] = existing_product.get("media_links") or existing_product.get("images", [])
    normalized = _normalize_product_entry(payload, existing_key=product_key)

    updated = False
    for index, item in enumerate(products):
        item_key = str(item.get("id") or item.get("product_key") or "")
        if item_key == normalized["id"]:
            products[index] = normalized
            updated = True
            break
        if product_key and item_key == product_key:
            products[index] = normalized
            updated = True
            break

    if not updated:
        products.append(normalized)

    products.sort(key=lambda item: str(item.get("name") or item.get("display_name") or "").lower())
    catalog["products"] = products
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    reload_product_catalog_from_file()
    return normalized


def delete_product_catalog_entry(product_key: str) -> dict[str, Any]:
    path = product_catalog_path()
    catalog = _load_json_file(path, {"products": [], "combos": []})
    products = [item for item in catalog.get("products", []) if isinstance(item, dict)]
    remaining = [
        item
        for item in products
        if str(item.get("id") or item.get("product_key") or "") != product_key
    ]
    if len(remaining) == len(products):
        raise ValueError("Product not found.")
    delete_product_media_collection(product_key)
    catalog["products"] = remaining
    path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    reload_product_catalog_from_file()
    return {"ok": True, "deleted_product_key": product_key}


def add_product_catalog_image(product_key: str, image_entry: dict[str, Any]) -> dict[str, Any]:
    """Attach an image entry to a product and persist the catalog."""
    path = product_catalog_path()
    catalog = _load_json_file(path, {"products": [], "combos": []})
    products = [item for item in catalog.get("products", []) if isinstance(item, dict)]
    for index, item in enumerate(products):
        if str(item.get("id") or item.get("product_key") or "") != product_key:
            continue
        images = normalize_product_image_entries(item.get("media_links") or item.get("images", []))
        normalized_image = normalize_product_image_entries([image_entry])[0]

        duplicate = next(
            (
                entry
                for entry in images
                if (
                    normalized_image.get("source_url")
                    and entry.get("source_url") == normalized_image.get("source_url")
                )
                or (
                    normalized_image.get("url")
                    and entry.get("url") == normalized_image.get("url")
                )
                or (
                    normalized_image.get("filename")
                    and entry.get("filename") == normalized_image.get("filename")
                )
            ),
            None,
        )
        if duplicate:
            return item

        updated_images = [entry for entry in images if entry.get("id") != normalized_image["id"]]
        if normalized_image.get("is_primary") or not updated_images:
            normalized_image["is_primary"] = True
            updated_images = [
                {**entry, "is_primary": False}
                for entry in updated_images
            ]
        elif not any(entry.get("is_primary") for entry in updated_images):
            updated_images[0]["is_primary"] = True

        updated_images.append(normalized_image)
        updated_images = normalize_product_image_entries(updated_images)
        item["media_links"] = updated_images
        products[index] = item

        catalog["products"] = products
        path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        reload_product_catalog_from_file()
        return item

    raise ValueError("Product not found.")


def remove_product_catalog_image(product_key: str, image_id: str) -> dict[str, Any]:
    """Remove an image from a product and delete the local file if present."""
    path = product_catalog_path()
    catalog = _load_json_file(path, {"products": [], "combos": []})
    products = [item for item in catalog.get("products", []) if isinstance(item, dict)]

    for index, item in enumerate(products):
        if str(item.get("id") or item.get("product_key") or "") != product_key:
            continue
        images = normalize_product_image_entries(item.get("media_links") or item.get("images", []))
        target = next((entry for entry in images if entry.get("id") == image_id), None)
        if not target:
            raise ValueError("Image not found.")
        delete_product_image_file(target)

        remaining = [entry for entry in images if entry.get("id") != image_id]
        if remaining and not any(entry.get("is_primary") for entry in remaining):
            remaining[0]["is_primary"] = True
        item["media_links"] = normalize_product_image_entries(remaining)
        products[index] = item
        catalog["products"] = products
        path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        reload_product_catalog_from_file()
        return item

    raise ValueError("Product not found.")


def mark_product_catalog_image_primary(product_key: str, image_id: str) -> dict[str, Any]:
    """Set one catalog image as the primary image for a product."""
    path = product_catalog_path()
    catalog = _load_json_file(path, {"products": [], "combos": []})
    products = [item for item in catalog.get("products", []) if isinstance(item, dict)]

    for index, item in enumerate(products):
        if str(item.get("id") or item.get("product_key") or "") != product_key:
            continue
        images = normalize_product_image_entries(item.get("media_links") or item.get("images", []))
        if not images:
            raise ValueError("No images found for this product.")
        found = False
        for entry in images:
            entry["is_primary"] = entry.get("id") == image_id
            if entry["is_primary"]:
                found = True
        if not found:
            raise ValueError("Image not found.")
        item["media_links"] = normalize_product_image_entries(images)
        products[index] = item
        catalog["products"] = products
        path.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        reload_product_catalog_from_file()
        return item

    raise ValueError("Product not found.")


def import_product_images_from_drive_folder(folder_url: str = PRODUCT_IMAGE_DRIVE_FOLDER_URL) -> dict[str, Any]:
    """Sync public Google Drive product folders into the live product catalog."""
    payload = get_product_catalog_payload()
    catalog_products = payload.get("products", [])
    if not catalog_products:
        raise ValueError("No catalog products found. Add products before importing images.")

    alias_map: dict[str, str] = {}
    product_index: dict[str, dict[str, Any]] = {}
    for product in catalog_products:
        product_key = str(product.get("product_key") or "").strip()
        if not product_key:
            continue
        product_index[product_key] = product
        for alias in _catalog_lookup_aliases(product):
            alias_map[alias] = product_key

    root_entries = list_public_google_drive_folder_entries(folder_url)
    imported_count = 0
    products_updated: list[dict[str, Any]] = []
    unmatched_folders: list[str] = []
    skipped_files: list[dict[str, str]] = []

    for folder_entry in root_entries:
        if not folder_entry.get("is_folder"):
            continue

        folder_name = str(folder_entry.get("name") or "").strip()
        product_key = alias_map.get(_normalize_product_lookup_key(folder_name))
        if not product_key:
            unmatched_folders.append(folder_name)
            continue

        product = product_index.get(product_key) or {}
        image_files = [
            entry
            for entry in list_public_google_drive_folder_entries(folder_entry["id"])
            if str(entry.get("mime_type") or "").startswith("image/")
        ]
        if not image_files:
            skipped_files.append(
                {
                    "product_key": product_key,
                    "folder_name": folder_name,
                    "reason": "no_images",
                }
            )
            continue

        existing_images = normalize_product_image_entries(product.get("images", []))
        existing_sources = {str(item.get("source_url") or "") for item in existing_images if item.get("source_url")}
        updated_product: dict[str, Any] | None = None

        for image_index, image_file in enumerate(image_files):
            download_url = str(image_file.get("download_url") or "").strip()
            if not download_url:
                skipped_files.append(
                    {
                        "product_key": product_key,
                        "file_name": str(image_file.get("name") or ""),
                        "reason": "missing_download_url",
                    }
                )
                continue
            if download_url in existing_sources:
                skipped_files.append(
                    {
                        "product_key": product_key,
                        "file_name": str(image_file.get("name") or ""),
                        "reason": "duplicate",
                    }
                )
                continue

            caption = f"{product.get('display_name') or folder_name} - {image_file.get('name', '')}".strip(" -")
            image_entry = save_product_image_from_url(
                product_key=product_key,
                image_url=download_url,
                caption=caption,
                source="google_drive",
                is_primary=not existing_images and image_index == 0,
                sort_order=len(existing_images) + image_index,
            )
            updated_product = add_product_catalog_image(product_key, image_entry)
            existing_sources.add(download_url)
            imported_count += 1

        if updated_product:
            product_index[product_key] = updated_product
            products_updated.append(
                {
                    "product_key": product_key,
                    "display_name": str(updated_product.get("display_name") or folder_name),
                    "image_count": len(normalize_product_image_entries(updated_product.get("images", []))),
                }
            )

    return {
        "ok": True,
        "folder_url": folder_url,
        "imported_count": imported_count,
        "products_updated": products_updated,
        "unmatched_folders": unmatched_folders,
        "skipped_files": skipped_files,
    }


def get_prompt_registry_payload() -> dict[str, Any]:
    items = list_prompt_configs()
    return {
        "items": items,
        "count": len(items),
    }


def save_prompt_registry_entry(prompt_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    item = save_prompt_config(prompt_id, payload)
    return {
        "ok": True,
        "item": item,
    }


def get_prompt_observatory_payload(limit: int = 50, phone: str = "") -> dict[str, Any]:
    init_database()
    with get_db_connection() as connection:
        if not _table_exists(connection, "conversation_audit_log"):
            return {"items": [], "count": 0}

        params: list[Any] = []
        phone_filter = ""
        if phone.strip():
            variants = _phone_variants(phone.strip())
            placeholders = ",".join("?" for _ in variants)
            phone_filter = f"AND phone IN ({placeholders})"
            params.extend(variants)

        params.extend([limit])
        rows = connection.execute(
            f"""
            SELECT created_at, phone, message, detected_intent, active_flow, metadata_json
            FROM conversation_audit_log
            WHERE direction = 'outbound'
              AND source = 'ai'
              {phone_filter}
            ORDER BY created_at DESC
            LIMIT ?
            """,
            tuple(params),
        ).fetchall()

        items: list[dict[str, Any]] = []
        for index, row in enumerate(rows, start=1):
            metadata = _safe_json_loads(row["metadata_json"])
            understanding = metadata.get("message_understanding") or {}
            prompt_trace = metadata.get("prompt_trace") or {}
            product_key = str(metadata.get("active_product") or understanding.get("product") or "").strip()
            product = get_canonical_product(product_key) if product_key else None
            state_row = _safe_fetchone(
                connection,
                "SELECT language, active_product, latest_intent, journey_stage FROM conversation_state WHERE customer_id = ?",
                (row["phone"],),
            ) if _table_exists(connection, "conversation_state") else {}
            customer = _safe_fetchone(
                connection,
                """
                SELECT COALESCE(name, first_name, phone, email, '') AS customer_name
                FROM customers
                WHERE REPLACE(COALESCE(phone, ''), '+', '') = REPLACE(?, '+', '')
                LIMIT 1
                """,
                (row["phone"],),
            ) if _table_exists(connection, "customers") else {}

            retrieved_knowledge = {}
            if product:
                retrieved_knowledge = {
                    "product": product.get("name"),
                    "origin": product.get("origin"),
                    "recommended_pack": product.get("recommended_pack"),
                    "prices": [
                        f"{variant.get('size')} ₹{variant.get('price')}"
                        for variant in list(product.get("sizes") or [])[:5]
                    ],
                }

            items.append(
                {
                    "id": f"obs-{index}",
                    "created_at": row["created_at"],
                    "phone": row["phone"],
                    "customer_name": customer.get("customer_name") or row["phone"],
                    "customer_message": metadata.get("inbound_message") or "",
                    "ai_reply": row["message"] or "",
                    "detected_language": understanding.get("detected_language") or understanding.get("language") or state_row.get("language") or "",
                    "detected_intent": row["detected_intent"] or understanding.get("detected_intent") or understanding.get("intent") or "",
                    "journey_stage": metadata.get("journey_stage") or understanding.get("journey_stage") or state_row.get("journey_stage") or "",
                    "active_product": product_key or state_row.get("active_product") or "",
                    "retrieved_knowledge": retrieved_knowledge,
                    "customer_context": {
                        "language": state_row.get("language") or "",
                        "active_product": state_row.get("active_product") or "",
                        "latest_intent": state_row.get("latest_intent") or "",
                        "journey_stage": state_row.get("journey_stage") or "",
                    },
                    "prompt_id": prompt_trace.get("prompt_id") or "",
                    "prompt_version": prompt_trace.get("prompt_version") or "",
                    "final_prompt": prompt_trace.get("final_prompt") or "",
                    "llm_response": prompt_trace.get("llm_response") or metadata.get("generated_response") or "",
                    "guard_action": metadata.get("guard_action") or "",
                    "issues_found": metadata.get("issues_found") or [],
                    "route": metadata.get("route") or "",
                }
            )

    return {
        "items": items,
        "count": len(items),
    }
