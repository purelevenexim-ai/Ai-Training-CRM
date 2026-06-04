from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from app.ai.gemini_client import gemini_client
from app.services.prompt_registry_service import get_prompt_config, get_prompt_text

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
    feedback_terms = ("feedback", "review", "opinion", "abhiprayam", "review parayam")

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
            "prompt_trace": {
                "prompt_id": "message_understanding_prompt",
                "prompt_version": int(get_prompt_config("message_understanding_prompt").get("version") or 1),
                "final_prompt": "",
                "llm_response": "",
            },
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
            "prompt_trace": {
                "prompt_id": "message_understanding_prompt",
                "prompt_version": int(get_prompt_config("message_understanding_prompt").get("version") or 1),
                "final_prompt": "",
                "llm_response": "",
            },
        }

    if any(term in text for term in feedback_terms) and str(context.get("journey_stage") or "").lower() == "post_delivery":
        return {
            "intent": "post_delivery_feedback",
            "sub_intent": "customer_shared_feedback_request",
            "sentiment": "positive",
            "language": detected_language,
            "journey_stage": "post_delivery",
            "customer_meaning": "Customer is discussing feedback after receiving the product.",
            "product_mentions": [],
            "needs_product_info": False,
            "reply_needed": True,
            "should_escalate": False,
            "should_sell": False,
            "should_ask_clarification": False,
            "confidence": 0.72,
            "recommended_action": "thank_customer_acknowledge_feedback",
            "source": "semantic_rules",
            "prompt_trace": {
                "prompt_id": "message_understanding_prompt",
                "prompt_version": int(get_prompt_config("message_understanding_prompt").get("version") or 1),
                "final_prompt": "",
                "llm_response": "",
            },
        }

    if not product_detected and rule_intent == "fallback":
        ai_understanding = _understand_with_gemini(
            message=message,
            context=context,
            detected_language=detected_language,
        )
        if ai_understanding:
            return ai_understanding

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
        "prompt_trace": {
            "prompt_id": "message_understanding_prompt",
            "prompt_version": int(get_prompt_config("message_understanding_prompt").get("version") or 1),
            "final_prompt": "",
            "llm_response": "",
        },
    }


def _understand_with_gemini(
    *,
    message: str,
    context: dict[str, Any],
    detected_language: str,
) -> dict[str, Any] | None:
    prompt_config = get_prompt_config("message_understanding_prompt")
    prompt_text = get_prompt_text("message_understanding_prompt")
    conversation_context = {
        "journey_stage": context.get("journey_stage") or context.get("current_stage") or "",
        "active_product": context.get("product_key") or "",
        "recent_messages": context.get("recent_messages") or [],
        "order_state": context.get("order_state") or {},
    }
    final_prompt = (
        f"{prompt_text}\n\n"
        "Return JSON only with keys:\n"
        "intent, sentiment, journey_stage, customer_meaning, reply_needed, should_escalate, confidence.\n\n"
        f"Customer message:\n{message}\n\n"
        f"Detected language:\n{detected_language}\n\n"
        f"Known context:\n{conversation_context}"
    )
    schema = {
        "type": "object",
        "properties": {
            "intent": {"type": "string"},
            "sentiment": {"type": "string"},
            "journey_stage": {"type": "string"},
            "customer_meaning": {"type": "string"},
            "reply_needed": {"type": "boolean"},
            "should_escalate": {"type": "boolean"},
            "confidence": {"type": "number"},
        },
        "required": [
            "intent",
            "sentiment",
            "journey_stage",
            "customer_meaning",
            "reply_needed",
            "should_escalate",
            "confidence",
        ],
    }
    result = gemini_client._call(final_prompt, response_schema=schema, temperature=0.15)
    if not result:
        return None

    intent = str(result.get("intent") or "").strip().lower()
    if intent in {"delivery_received_confirmation", "parcel_received", "customer_received_order"}:
        recommended_action = "thank_customer_ask_feedback"
        normalized_intent = "delivery_received_confirmation"
    elif intent in {"gratitude_positive", "thank_you", "thanks"}:
        recommended_action = "acknowledge_gratitude"
        normalized_intent = "gratitude_positive"
    else:
        recommended_action = "use_rule_intent"
        normalized_intent = intent or "unclear"

    return {
        "intent": normalized_intent,
        "sub_intent": None,
        "sentiment": str(result.get("sentiment") or "neutral").strip().lower() or "neutral",
        "language": detected_language,
        "journey_stage": str(result.get("journey_stage") or context.get("journey_stage") or "general").strip() or "general",
        "customer_meaning": str(result.get("customer_meaning") or "AI semantic understanding used.").strip(),
        "product_mentions": [],
        "needs_product_info": False,
        "reply_needed": bool(result.get("reply_needed", True)),
        "should_escalate": bool(result.get("should_escalate", False)),
        "should_sell": False,
        "should_ask_clarification": normalized_intent in {"unclear", "fallback"},
        "confidence": float(result.get("confidence", 0.6) or 0.6),
        "recommended_action": recommended_action,
        "source": "gemini_semantic",
        "prompt_trace": {
            "prompt_id": "message_understanding_prompt",
            "prompt_version": int(prompt_config.get("version") or 1),
            "final_prompt": final_prompt,
            "llm_response": json_safe(result),
        },
    }


def json_safe(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)
