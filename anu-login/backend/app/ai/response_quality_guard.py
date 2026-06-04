from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from app.ai.customer_state_engine import get_customer_state, reply_hash
from app.ai.intent_registry import detect_language
from app.ai.pricing_formatter import PricingFormatter

logger = logging.getLogger(__name__)


BANNED_PHRASES = (
    "yes, we have",
    "i’ll share the price details below",
    "i'll share the price details below",
    "customers usually use this",
    "spice-growing belt",
    "unique qualities",
    "absolutely",
    "just checking in",
    "best pack and order it today",
    "are you referring to the price, delivery, or help with your order",
    "athu kurach clear aakki parayamo",
    "i can help with products, delivery, payment, or orders",
)

CATALOG_PATTERNS = (
    r"\*\s*size\s*\|\s*price",
    r"\*\s*size\s*\|\s*price\s*\|\s*delivery",
    r"size\s*\|\s*price",
    r"size\s*\|\s*price\s*\|\s*delivery",
    r"^250g\s*\|",
    r"^100g\s*\|",
    r"^500g\s*\|",
    r"^1kg\s*\|",
)


@dataclass
class GuardResult:
    action: str
    final_reply: str
    issues_found: list[str] = field(default_factory=list)
    rewritten: bool = False
    blocked_reason: str = ""


def _word_count(text: str) -> int:
    return len([token for token in re.split(r"\s+", (text or "").strip()) if token])


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _contains_catalog_style(text: str) -> bool:
    lowered = text.lower()
    if any(re.search(pattern, lowered, re.IGNORECASE | re.MULTILINE) for pattern in CATALOG_PATTERNS):
        return True
    return lowered.count("|") >= 2 and ("₹" in lowered or "delivery" in lowered)


def _remove_banned_phrases(text: str) -> tuple[str, list[str]]:
    issues: list[str] = []
    cleaned = text
    for phrase in BANNED_PHRASES:
        if phrase.lower() in cleaned.lower():
            issues.append("banned_phrase")
            cleaned = re.sub(re.escape(phrase), "", cleaned, flags=re.IGNORECASE)
    return _normalize(cleaned), issues


def _remove_question_lines(text: str, markers: tuple[str, ...], issue_tag: str) -> tuple[str, list[str]]:
    issues: list[str] = []
    lines = []
    for line in (text or "").splitlines():
        lowered = line.lower()
        if any(marker in lowered for marker in markers):
            issues.append(issue_tag)
            continue
        lines.append(line)
    return _normalize("\n".join(lines)), issues


def _shorten_reply(text: str, max_words: int = 55) -> str:
    words = (text or "").split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip(" ,;:-") + "…"


def _simple_product_reply(
    *,
    state: dict[str, Any],
    reply_result: dict[str, Any] | None,
) -> str:
    reply_result = reply_result or {}
    product_key = str(reply_result.get("product_key") or state.get("active_product") or "").strip()
    if not product_key:
        return ""
    product = PricingFormatter.get_product_catalog_entry(product_key) or {}
    sizes = list(product.get("sizes") or [])
    if not sizes:
        return ""

    language = str(state.get("language") or "").strip().lower() or detect_language(product.get("name") or product_key)
    opening = {
        "english": "Yes, available 😊",
        "manglish": "Undu 😊",
        "malayalam": "ഉണ്ട് 😊",
    }.get(language, "Yes, available 😊")
    price_lines = [f"{item.get('size')} ₹{int(item.get('price') or 0)}" for item in sizes if item.get("size")]
    return "\n\n".join([opening, "\n".join(price_lines)]).strip()


def _should_allow_long_reply(intent: str, state: dict[str, Any], reply_result: dict[str, Any]) -> bool:
    if intent in {"details", "quality", "origin", "processing", "usage", "benefits", "comparison"}:
        return True
    if str(reply_result.get("scenario") or "").strip() in {"details", "quality", "origin", "processing", "usage", "benefits", "comparison"}:
        return True
    return False


def guard_whatsapp_reply(
    *,
    customer_id: str,
    inbound_message: str,
    generated_reply: str,
    reply_result: dict[str, Any] | None = None,
    final_reply: str | None = None,
    allow_empty: bool = False,
) -> GuardResult:
    reply_result = reply_result or {}
    state = get_customer_state(customer_id) if customer_id else {}
    intent = str(reply_result.get("intent") or state.get("latest_intent") or "").strip().lower()
    reply_text = _normalize(final_reply if final_reply is not None else generated_reply)
    issues: list[str] = []

    if not reply_text:
        if allow_empty:
            return GuardResult(action="sent", final_reply="", issues_found=[])
        return GuardResult(action="blocked", final_reply="", issues_found=["empty_reply"], blocked_reason="empty_reply")

    if state:
        last_hash = str(state.get("last_ai_reply_hash") or "").strip()
        current_hash = reply_hash(reply_text)
        if last_hash and last_hash == current_hash:
            return GuardResult(
                action="blocked",
                final_reply="",
                issues_found=["duplicate_reply"],
                blocked_reason="duplicate_reply",
            )
        if state.get("last_ai_reply_at") and state.get("last_ai_reply_hash"):
            last_reply = str((state.get("context") or {}).get("final_reply") or "").strip()
            if last_reply and reply_text and last_reply.lower() == reply_text.lower():
                return GuardResult(
                    action="blocked",
                    final_reply="",
                    issues_found=["duplicate_reply"],
                    blocked_reason="duplicate_reply",
                )

    reply_text, phrase_issues = _remove_banned_phrases(reply_text)
    issues.extend(phrase_issues)

    if state.get("payment_screenshot_received") or state.get("payment_claimed"):
        reply_text, new_issues = _remove_question_lines(
            reply_text,
            ("screenshot", "receipt", "transaction reference", "payment proof", "proof"),
            "screenshot_already_received",
        )
        issues.extend(new_issues)
    if state.get("address_received"):
        reply_text, new_issues = _remove_question_lines(
            reply_text,
            ("address", "full address", "deliver", "delivery location"),
            "address_already_received",
        )
        issues.extend(new_issues)
    if state.get("pincode_received"):
        reply_text, new_issues = _remove_question_lines(
            reply_text,
            ("pincode", "pin code"),
            "pincode_already_received",
        )
        issues.extend(new_issues)

    if _contains_catalog_style(reply_text):
        issues.append("catalog_style")
        if intent in {"availability", "price", "stock_check"} or str(reply_result.get("scenario") or "") in {"availability", "price", "stock_check"}:
            product_reply = _simple_product_reply(state=state, reply_result=reply_result)
            if product_reply:
                reply_text = product_reply
            else:
                reply_text = _shorten_reply(reply_text, 40)
        else:
            reply_text = _shorten_reply(reply_text, 55)

    words = _word_count(reply_text)
    if words > 55 and not _should_allow_long_reply(intent, state, reply_result):
        issues.append("too_long")
        reply_text = _shorten_reply(reply_text, 55)

    if any(marker in reply_text.lower() for marker in ("combo pack", "combo offer", "bundle", "special offer")):
        if intent not in {"combo", "best_pack", "budget", "order_request", "order_confirm"}:
            issues.append("premature_upsell")
            reply_text = "\n".join(
                line for line in reply_text.splitlines() if not re.search(r"combo|bundle|special offer|save", line, re.IGNORECASE)
            ).strip()

    if intent in {"availability", "price", "stock_check"}:
        simple_reply = _simple_product_reply(state=state, reply_result=reply_result)
        if simple_reply and len(simple_reply.split()) <= 55:
            reply_text = simple_reply

    reply_text = _normalize(reply_text)
    if not reply_text:
        return GuardResult(
            action="blocked",
            final_reply="",
            issues_found=issues or ["empty_after_guard"],
            blocked_reason="empty_after_guard",
        )

    if reply_text != _normalize(final_reply if final_reply is not None else generated_reply):
        return GuardResult(action="rewrite", final_reply=reply_text, issues_found=issues, rewritten=True)

    return GuardResult(action="sent", final_reply=reply_text, issues_found=issues, rewritten=False)
