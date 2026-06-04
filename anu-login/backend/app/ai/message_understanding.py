from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


def _normalise_text(message: str) -> str:
    return re.sub(r"\s+", " ", (message or "").strip().lower())


def understand_customer_message(
    *,
    message: str,
    context: Optional[dict[str, Any]] = None,
    product_detected: bool = False,
    rule_intent: str = "fallback",
    detected_language: str = "english",
) -> dict[str, Any]:
    """Broad semantic understanding before reply generation.

    This is intentionally category-based, not exact sentence training. It catches
    customer journey meaning such as post-delivery confirmation and gratitude so
    they do not fall into the generic clarification fallback.
    """
    text = _normalise_text(message)
    context = context or {}

    received_terms = ("kitti", "kitty", "got", "received", "recieved", "ലഭിച്ചു", "കിട്ടി")
    parcel_terms = ("parcel", "parsal", "order", "product", "item", "package", "delivery", "courier", "പാഴ്സൽ", "ഓർഡർ", "സാധനം")
    thanks_terms = ("thank", "thanks", "thanku", "thank u", "tnx", "നന്ദി")

    if any(received in text for received in received_terms) and any(parcel in text for parcel in parcel_terms):
        return {
            "intent": "delivery_received_confirmation",
            "sub_intent": "customer_confirmed_parcel_received",
            "sentiment": "positive" if any(term in text for term in thanks_terms) else "neutral",
            "language": detected_language,
            "journey_stage": "post_delivery",
            "customer_meaning": "Customer is confirming that the parcel/order was received.",
            "product_mentions": [],
            "needs_product_info": False,
            "reply_needed": True,
            "should_escalate": False,
            "should_sell": False,
            "should_ask_clarification": False,
            "confidence": 0.86,
            "recommended_action": "thank_customer_ask_feedback",
            "source": "semantic_rules",
        }

    if any(term in text for term in thanks_terms) and len(text.split()) <= 8:
        return {
            "intent": "gratitude_positive",
            "sub_intent": "customer_thanked_us",
            "sentiment": "positive",
            "language": detected_language,
            "journey_stage": str(context.get("journey_stage") or context.get("current_stage") or "general"),
            "customer_meaning": "Customer is thanking us or acknowledging the conversation positively.",
            "product_mentions": [],
            "needs_product_info": False,
            "reply_needed": True,
            "should_escalate": False,
            "should_sell": False,
            "should_ask_clarification": False,
            "confidence": 0.76,
            "recommended_action": "acknowledge_gratitude",
            "source": "semantic_rules",
        }

    return {
        "intent": rule_intent if rule_intent != "fallback" else "unclear",
        "sub_intent": None,
        "sentiment": "neutral",
        "language": detected_language,
        "journey_stage": "product_interest" if product_detected else "general",
        "customer_meaning": "Rule-based classifier result used.",
        "product_mentions": [],
        "needs_product_info": product_detected,
        "reply_needed": True,
        "should_escalate": rule_intent in {"complaint", "return_refund", "human_handoff", "wholesale"},
        "should_sell": product_detected,
        "should_ask_clarification": rule_intent == "fallback",
        "confidence": 0.5 if rule_intent == "fallback" else 0.65,
        "recommended_action": "use_rule_intent",
        "source": "rule_fallback",
    }
