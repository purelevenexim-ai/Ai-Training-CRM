from __future__ import annotations

import logging
from typing import Any, Optional

from app.ai.gemini_client import gemini_client
from app.ai.intent_registry import detect_intent, detect_language, intent_metadata
from app.ai.pricing_formatter import PricingFormatter
from app.ai.product_knowledge import detect_product, detect_products, get_product

logger = logging.getLogger(__name__)


INTENT_TO_SCENARIO = {
    "availability": "availability",
    "stock_check": "availability",
    "price": "price",
    "details": "details",
    "quality": "quality",
    "origin": "origin",
    "processing": "processing",
    "usage": "usage",
    "benefits": "benefits",
    "best_pack": "best_pack",
    "budget": "budget",
    "combo": "combo",
    "comparison": "comparison",
    "price_objection": "price_objection",
    "delivery_charge": "delivery_charge",
    "delivery_time": "delivery_time",
    "free_delivery": "free_delivery",
    "order_request": "order_request",
    "order_confirm": "order_confirm",
    "gift": "details",
    "followup": "details",
    "fallback": "fallback",
}


def _bridge_lines(
    *,
    scenario: str,
    style: str,
    customer_message: str,
    customer_name: str,
    product: dict[str, Any] | None = None,
) -> dict[str, str]:
    facts = {
        "product_name": (product or {}).get("name", ""),
        "origin": (product or {}).get("origin", ""),
        "story": (product or {}).get("story", ""),
        "quality": (product or {}).get("quality", ""),
        "use_cases": (product or {}).get("use_cases", []),
        "recommended_pack": (product or {}).get("recommended_pack", ""),
        "scenario": scenario,
    }
    instruction_map = {
        "availability": "Open like a warm Kerala spice seller. Keep it short and natural.",
        "price": "Introduce the size list warmly. Do not sound corporate.",
        "details": "Give a warm opening and a gentle invitation to continue.",
        "delivery_time": "Answer only the delivery timing question in a short human tone.",
        "delivery_charge": "Answer only the delivery charge question clearly and briefly.",
        "order_request": "Move naturally toward order capture without sounding pushy.",
        "comparison": "Acknowledge the comparison and keep it grounded in source, quality, and use case.",
        "fallback": "Ask the customer whether they mean price, delivery, or order help.",
    }
    try:
        lines = gemini_client.generate_whatsapp_reply_lines(
            scenario=scenario,
            customer_message=customer_message,
            customer_name=customer_name,
            style=style,
            product_name=str((product or {}).get("name") or ""),
            facts=facts,
            instruction=instruction_map.get(scenario, "Write a short, natural WhatsApp opening and closing using only the facts."),
        )
    except Exception as exc:
        logger.warning("Gemini bridge-line generation failed: %s", exc)
        lines = {"opening_line": "", "closing_line": ""}

    banned_fragments = (
        "yes, we have",
        "i’ll share the price details below",
        "i'll share the price details below",
        "how much are you looking for",
        "let me know if you would like to order",
        "how can we assist",
        "how can i assist",
        "what details",
        "which details",
        "what information",
        "details ayakkamo",
        "details ayacholu",
        "details അയക്ക",
    )
    opening = str(lines.get("opening_line") or "").strip()
    closing = str(lines.get("closing_line") or "").strip()
    if any(fragment in opening.lower() for fragment in banned_fragments):
        opening = ""
    if any(fragment in closing.lower() for fragment in banned_fragments):
        closing = ""
    return {
        "opening_line": opening,
        "closing_line": closing,
    }


def _follow_up_plan(scenario: str) -> list[dict[str, Any]]:
    if scenario in {"order_request", "order_confirm", "order_intent"}:
        return [
            {"after_minutes": 5, "stage": "gentle_reminder"},
            {"after_minutes": 30, "stage": "combo_offer"},
            {"after_minutes": 240, "stage": "image_only"},
            {"after_minutes": 360, "stage": "soft_nudge"},
            {"after_minutes": 1380, "stage": "final_followup"},
        ]
    return []


def _customer_product_reference(product: dict[str, Any], message: str) -> str:
    lower = (message or "").lower()
    best = ""
    for alias in product.get("aliases", []):
        alias_text = str(alias or "").strip()
        if alias_text and alias_text.lower() in lower and len(alias_text) > len(best):
                best = alias_text
    return best or str(product.get("name") or "")


def _display_product_reference(product: dict[str, Any], customer_reference: str, reply_style: str) -> str:
    """Use the customer's wording in Manglish/Malayalam, but keep English typo aliases tidy."""
    product_name = str(product.get("name") or "").strip()
    reference = str(customer_reference or "").strip()
    if not reference:
        return product_name
    if reply_style == "english":
        normalized_ref = "".join(ch for ch in reference.lower() if ch.isalnum())
        normalized_name = "".join(ch for ch in product_name.lower() if ch.isalnum())
        if normalized_ref == normalized_name or " " not in reference:
            return product_name
    return reference


def _non_product_reply(intent: str, style: str) -> dict[str, Any]:
    style_key = PricingFormatter._style_key(style)
    copy = PricingFormatter.REPLY_STYLE_COPY[style_key] if hasattr(PricingFormatter, "REPLY_STYLE_COPY") else None
    # Access module-level copy without exposing it publicly.
    from app.ai import pricing_formatter as pricing_module

    copy = pricing_module.REPLY_STYLE_COPY[style_key]
    if intent == "wholesale":
        return {
            "reply_text": PricingFormatter.build_wholesale_reply(style=style_key),
            "intent": "wholesale",
            "should_escalate": True,
            "escalation_reason": "wholesale_inquiry",
            "suggested_action": "escalate",
        }
    if intent in {"complaint", "return_refund"}:
        return {
            "reply_text": copy["complaint"],
            "intent": intent,
            "should_escalate": True,
            "escalation_reason": intent,
            "suggested_action": "escalate",
        }
    if intent == "payment":
        return {
            "reply_text": copy["payment"],
            "intent": "payment",
            "should_escalate": False,
            "escalation_reason": None,
            "suggested_action": "send_reply",
        }
    if intent == "followup":
        return {
            "reply_text": copy["defer_decision"],
            "intent": "followup",
            "should_escalate": False,
            "escalation_reason": None,
            "suggested_action": "send_reply",
        }
    if intent == "negation":
        return {
            "reply_text": copy["no_interest"],
            "intent": "negation",
            "should_escalate": False,
            "escalation_reason": None,
            "suggested_action": "send_reply",
        }
    if intent == "combo":
        return {
            "reply_text": PricingFormatter.build_combo_reply(style=style_key),
            "intent": "combo",
            "should_escalate": False,
            "escalation_reason": None,
            "suggested_action": "send_reply",
        }
    if intent in {"delivery_time", "delivery_charge", "free_delivery"}:
        return {
            "reply_text": copy["delivery_time"] if intent == "delivery_time" else copy["delivery_charge"],
            "intent": intent,
            "should_escalate": False,
            "escalation_reason": None,
            "suggested_action": "send_reply",
        }
    if intent == "business_info":
        return {
            "reply_text": copy["business_info"],
            "intent": "business_info",
            "should_escalate": False,
            "escalation_reason": None,
            "suggested_action": "send_reply",
        }
    if intent == "human_handoff":
        return {
            "reply_text": copy["human_handoff"],
            "intent": "human_handoff",
            "should_escalate": True,
            "escalation_reason": "human_handoff_requested",
            "suggested_action": "escalate",
        }
    return {
        "reply_text": copy["fallback"],
        "intent": "fallback",
        "should_escalate": False,
        "escalation_reason": None,
        "suggested_action": "send_reply",
    }


def generate_dynamic_reply(
    *,
    incoming_message: str,
    customer_name: str,
    context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    context = context or {}
    detected_language = detect_language(incoming_message)
    context_style = str(context.get("reply_style") or "").strip().lower()
    reply_style = context_style if context_style and detected_language == "english" else detected_language

    explicit_products = detect_products(incoming_message)
    explicit_product = explicit_products[0] if explicit_products else None
    raw_context_product = str(context.get("product_key") or "").strip() or None
    context_product = raw_context_product if get_product(raw_context_product) else detect_product(raw_context_product or "")
    product_id = explicit_product or context_product
    product = get_product(product_id) if product_id else None
    intent = detect_intent(incoming_message, product_detected=bool(product))
    metadata = intent_metadata(incoming_message, product_detected=bool(product))

    if not product:
        reply = _non_product_reply(intent, reply_style)
        reply["message_understanding"] = {
            **metadata,
            "product": None,
            "product_mentions": [],
            "reply_style": reply_style,
            "customer_reference": None,
        }
        return reply

    if intent in {"complaint", "return_refund", "human_handoff", "payment", "wholesale", "followup", "negation"}:
        reply = _non_product_reply(intent, reply_style)
        reply["message_understanding"] = {
            **metadata,
            "product": product["id"],
            "product_mentions": explicit_products or [product["id"]],
            "reply_style": reply_style,
            "scenario": intent,
            "customer_reference": _customer_product_reference(product, incoming_message),
        }
        return reply

    if len(explicit_products) > 1 and intent in {"availability", "price"}:
        product_cards: list[dict[str, Any]] = []
        image_urls: list[str] = []
        for product_key in explicit_products:
            definition = PricingFormatter.get_core_product_definition(product_key, style=reply_style)
            if definition:
                product_cards.append(definition)
            image_url = PricingFormatter.get_primary_product_image_url(product_key)
            if image_url and image_url not in image_urls:
                image_urls.append(image_url)
        return {
            "reply_text": PricingFormatter.format_catalog_response(product_cards),
            "intent": "details",
            "should_escalate": False,
            "escalation_reason": None,
            "suggested_action": "send_reply",
            "image_urls": image_urls,
            "primary_image_url": image_urls[0] if image_urls else "",
            "media_mode": "image" if image_urls else "text",
            "customer_reference": None,
            "message_understanding": {
                **metadata,
                "product": product_id,
                "product_mentions": explicit_products,
                "reply_style": reply_style,
                "scenario": "details",
                "customer_reference": None,
            },
        }

    scenario = INTENT_TO_SCENARIO.get(intent, "fallback")
    bridge = _bridge_lines(
        scenario=scenario,
        style=reply_style,
        customer_message=incoming_message,
        customer_name=customer_name,
        product=product,
    )
    explicit_reference = _customer_product_reference(product, incoming_message) if explicit_product else ""
    raw_customer_reference = str(explicit_reference or context.get("customer_reference") or product.get("name") or "")
    resolved_customer_reference = _display_product_reference(product, raw_customer_reference, reply_style)
    payload = PricingFormatter.build_product_journey_reply_payload(
        product_key=product["id"],
        style=reply_style,
        scenario=scenario,
        customer_reference=resolved_customer_reference,
        opening_line=None if scenario in {"availability", "stock_check", "delivery_time", "delivery_charge", "free_delivery"} else bridge.get("opening_line") or None,
        closing_line=bridge.get("closing_line") or None,
    )
    if not payload:
        fallback = _non_product_reply("fallback", reply_style)
        fallback["message_understanding"] = {
            **metadata,
            "product": product_id,
            "product_mentions": explicit_products or ([product_id] if product_id else []),
            "reply_style": reply_style,
            "customer_reference": resolved_customer_reference,
        }
        return fallback

    payload.update(
        {
            "reply_text": payload.get("reply_text", ""),
            "intent": intent,
            "should_escalate": intent in {"complaint", "return_refund", "wholesale", "human_handoff"},
            "escalation_reason": intent if intent in {"complaint", "return_refund", "wholesale", "human_handoff"} else None,
            "suggested_action": "escalate" if intent in {"complaint", "return_refund", "wholesale", "human_handoff"} else "send_reply",
            "follow_up_plan": _follow_up_plan(scenario),
            "customer_reference": resolved_customer_reference,
            "message_understanding": {
                **metadata,
                "product": product["id"],
                "product_mentions": explicit_products or [product["id"]],
                "reply_style": reply_style,
                "scenario": scenario,
                "customer_reference": resolved_customer_reference,
            },
        }
    )
    return payload
