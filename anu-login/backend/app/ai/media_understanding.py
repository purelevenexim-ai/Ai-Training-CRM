from __future__ import annotations

import json
import re
from typing import Any


PAYMENT_MEDIA_KEYWORDS = (
    "paid",
    "payment",
    "google pay",
    "gpay",
    "phonepe",
    "paytm",
    "upi",
    "transaction",
    "screenshot",
    "receipt",
    "amount",
    "successful",
    "success",
    "credited",
    "debited",
    "utr",
    "rrn",
    "reference",
    "ref no",
    "txn",
    "rs",
    "₹",
)

PAYMENT_REFERENCE_PATTERN = re.compile(
    r"\b(?:utr|rrn|txn|transaction|ref(?:erence)?)\s*[:#-]?\s*[a-z0-9]{6,}\b",
    re.IGNORECASE,
)

PAYMENT_STAGE_NAMES = {"order_capture", "payment_pending", "payment_review"}
PAYMENT_MEDIA_TYPES = {"image", "photo", "media", "document", "pdf", "screenshot"}


def _normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def _message_is_media_marker(message: str) -> bool:
    text = (message or "").strip().lower()
    return text.startswith("[[media:") and text.endswith("]]")


def _media_type_from_message(message: str, message_meta: dict[str, Any]) -> str:
    if message_meta.get("media_type"):
        return str(message_meta.get("media_type") or "").strip().lower()
    if message_meta.get("message_type"):
        return str(message_meta.get("message_type") or "").strip().lower()
    text = (message or "").strip().lower()
    if _message_is_media_marker(text):
        return text.removeprefix("[[media:").removesuffix("]]").strip() or "media"
    return ""


def _collect_text_fragments(value: Any, fragments: list[str]) -> None:
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
                "transcript",
                "note",
                "message",
            }:
                _collect_text_fragments(item, fragments)
            elif isinstance(item, (dict, list)):
                _collect_text_fragments(item, fragments)
        return
    if isinstance(value, list):
        for item in value:
            _collect_text_fragments(item, fragments)
        return
    text = _normalize_text(value)
    if not text:
        return
    if text.startswith("http://") or text.startswith("https://"):
        return
    fragments.append(text)


def extract_media_text_hints(message_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    message_meta = message_meta or {}
    fragments: list[str] = []
    for key in (
        "media_text",
        "media_caption",
        "media_ocr_text",
        "media_analysis_text",
        "raw_message",
        "raw_payload",
    ):
        value = message_meta.get(key)
        if not value:
            continue
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                try:
                    parsed = json.loads(stripped)
                except Exception:
                    parsed = stripped
                _collect_text_fragments(parsed, fragments)
            else:
                _collect_text_fragments(stripped, fragments)
        else:
            _collect_text_fragments(value, fragments)

    unique: list[str] = []
    seen: set[str] = set()
    for fragment in fragments:
        lowered = fragment.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        unique.append(fragment)

    text_blob = " ".join(unique).strip()
    lowered_blob = text_blob.lower()
    matched_keywords = [keyword for keyword in PAYMENT_MEDIA_KEYWORDS if keyword in lowered_blob]
    has_reference = bool(PAYMENT_REFERENCE_PATTERN.search(text_blob))
    return {
        "text": text_blob,
        "keywords": matched_keywords,
        "has_reference": has_reference,
    }


def analyze_media_message(
    *,
    incoming_message: str,
    context: dict[str, Any] | None = None,
    message_meta: dict[str, Any] | None = None,
    detected_language: str = "english",
) -> dict[str, Any]:
    context = context or {}
    message_meta = message_meta or {}
    media_type = _media_type_from_message(incoming_message, message_meta)
    hints = extract_media_text_hints(message_meta)
    text_blob = str(hints.get("text") or "")
    matched_keywords = list(hints.get("keywords") or [])
    has_reference = bool(hints.get("has_reference"))
    lowered_blob = text_blob.lower()
    payment_context = bool(
        context.get("payment_claimed")
        or context.get("payment_screenshot_received")
        or context.get("address_received")
        or context.get("pincode_received")
        or str(context.get("latest_intent") or "").strip().lower() == "payment"
        or str(context.get("journey_stage") or "").strip().lower() in PAYMENT_STAGE_NAMES
    )
    screenshot_like = media_type in PAYMENT_MEDIA_TYPES or _message_is_media_marker(incoming_message)
    payment_signal = bool(matched_keywords or has_reference or ("₹" in lowered_blob))

    if screenshot_like and (payment_signal or payment_context):
        confidence = 0.93 if payment_signal or has_reference else 0.72
        return {
            "message_type": "image_or_screenshot",
            "media_type": media_type or "media",
            "detected_intent": "payment_proof",
            "intent": "payment_proof_shared",
            "confidence": confidence,
            "keywords": matched_keywords,
            "extracted_text": text_blob,
            "customer_stage": "payment_verification",
            "next_action": "verify_payment_proof",
            "payment_context": payment_context,
            "needs_amount_time": False,
            "reply_needed": True,
            "should_send": True,
            "language": detected_language,
            "analysis_type": "payment_proof_contextual" if payment_context and not payment_signal else "payment_proof_detected",
        }

    return {
        "message_type": "media",
        "media_type": media_type or "media",
        "detected_intent": "media_review",
        "intent": "media_review",
        "confidence": 0.2,
        "keywords": matched_keywords,
        "extracted_text": text_blob,
        "customer_stage": str(context.get("journey_stage") or "general"),
        "next_action": "wait_for_user",
        "payment_context": payment_context,
        "needs_amount_time": False,
        "reply_needed": False,
        "should_send": False,
        "language": detected_language,
        "analysis_type": "low_confidence_media_review",
    }
