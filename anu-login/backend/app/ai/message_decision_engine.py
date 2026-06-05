from __future__ import annotations

import re
from typing import Any

from app.ai.intent_registry import detect_language, normalize_message
from app.ai.pricing_formatter import PricingFormatter
from app.url_config import URLConfig


ACK_TERMS = {
    "ok",
    "okay",
    "okk",
    "yes",
    "fine",
    "sure",
    "noted",
    "ശരി",
}

PLANT_TERMS = (
    "plant",
    "plants",
    "plont",
    "plonts",
    "seedling",
    "seedlings",
    "nalyani",
    "green gold",
)

LOCATION_TERMS = (
    "location",
    "where is",
    "shop evide",
    "place evide",
    "evide aanu",
    "address evide",
    "shop location",
)

ADDRESS_CONFIRM_TERMS = (
    "saved",
    "yes saved",
    "address saved",
    "save cheythu",
    "ayachu",
    "sent address",
)


def _button_label(message: str, context: dict[str, Any] | None = None) -> str:
    context = context or {}
    meta = context.get("message_meta") if isinstance(context.get("message_meta"), dict) else {}
    for key in ("button_text", "postback_id", "provider_postback_id", "reply_message_id"):
        value = str(meta.get(key) or context.get(key) or "").strip()
        if value:
            return value
    raw = str(message or "").strip()
    if raw.lower().startswith("#button reply#"):
        marker = "#Button Reply#" if "#Button Reply#" in raw else "#button reply#"
        return raw.split(marker, 1)[-1].strip()
    return raw


def _style(message: str, context: dict[str, Any] | None = None) -> str:
    context = context or {}
    existing = str(context.get("language") or context.get("reply_style") or "").strip().lower()
    if existing in {"english", "manglish", "malayalam"}:
        return existing
    return detect_language(message)


def _copy(style: str, key: str) -> str:
    return PricingFormatter.get_static_copy(key, style)


def _payment_reply(style: str, proof_received: bool = False) -> str:
    if proof_received:
        return _copy(style, "payment_received")
    return {
        "english": "Payment message received 👍 Please share screenshot or transaction ID if available. We’ll verify and confirm.",
        "manglish": "Payment message kitti 👍 Screenshot allenkil transaction ID undenkil ayacholu. Verify cheythu confirm cheyyam.",
        "malayalam": "Payment message കിട്ടി 👍 Screenshot അല്ലെങ്കിൽ transaction ID ഉണ്ടെങ്കിൽ അയച്ചോളൂ. Verify ചെയ്ത് confirm ചെയ്യാം.",
    }.get(style, "Payment message kitti 👍 Screenshot allenkil transaction ID undenkil ayacholu. Verify cheythu confirm cheyyam.")


def _ack_reply(style: str, context: dict[str, Any]) -> str:
    stage = str(context.get("journey_stage") or context.get("latest_intent") or "").lower()
    if "payment" in stage:
        return {
            "english": "Okay 👍 We’ll verify and confirm.",
            "manglish": "Okay 👍 Verify cheythu confirm cheyyam.",
            "malayalam": "ശരി 👍 Verify ചെയ്ത് confirm ചെയ്യാം.",
        }.get(style, "Okay 👍 Verify cheythu confirm cheyyam.")
    if "price" in stage or "product_interest" in stage:
        return {
            "english": "Order venel name, address, phone number, pincode ayacholu.",
            "manglish": "Order venel name, address, phone number, pincode ayacholu.",
            "malayalam": "Order വേണമെങ്കിൽ name, address, phone number, pincode അയച്ചോളൂ.",
        }.get(style, "Order venel name, address, phone number, pincode ayacholu.")
    if context.get("address_received") or "address" in stage or "order" in stage:
        return {
            "english": "Okay 👍 Address details received.",
            "manglish": "Okay 👍 Address details kitti.",
            "malayalam": "ശരി 👍 Address details കിട്ടി.",
        }.get(style, "Okay 👍 Address details kitti.")
    return {
        "english": "Okay 👍 Which product are you looking for?",
        "manglish": "Okay 👍 Eth product aanu nokkunnath?",
        "malayalam": "ശരി 👍 ഏത് product ആണ് നോക്കുന്നത്?",
    }.get(style, "Okay 👍 Eth product aanu nokkunnath?")


def _address_reply(style: str) -> str:
    return {
        "english": "Address details received 👍 I’ll use this for the order.",
        "manglish": "Address details kitti 👍 Orderinu ithu use cheyyam.",
        "malayalam": "Address details കിട്ടി 👍 Order-ന് ഇത് use ചെയ്യാം.",
    }.get(style, "Address details kitti 👍 Orderinu ithu use cheyyam.")


def _plant_reply(style: str) -> str:
    return {
        "english": "Plants/seedlings are not listed for sale right now. Spices are available 😊 If you meant pepper/cardamom/clove, tell me the product name.",
        "manglish": "Plants/seedlings ippol sale list-il illa. Spices available aanu 😊 Pepper/cardamom/clove aanu nokkunnathengil product name parayu.",
        "malayalam": "Plants/seedlings ഇപ്പോൾ sale list-ൽ ഇല്ല. Spices available ആണ് 😊 Pepper/cardamom/clove ആണെങ്കിൽ product name പറയൂ.",
    }.get(style, "Plants/seedlings ippol sale list-il illa. Spices available aanu 😊 Product name parayu.")


def _location_reply(style: str) -> str:
    contact_link = URLConfig.get_contact_link()
    return {
        "english": f"PureLeven is a Kerala/Idukki-side spice brand. We mainly take orders online and deliver by courier.\n\nContact page: {contact_link}",
        "manglish": f"PureLeven Kerala/Idukki-side spice brand aanu. Orders mainly online aanu, courier delivery undu.\n\nContact page: {contact_link}",
        "malayalam": f"PureLeven Kerala/Idukki-side spice brand ആണ്. Orders mainly online ആണ്, courier delivery ഉണ്ട്.\n\nContact page: {contact_link}",
    }.get(style, f"PureLeven Kerala/Idukki-side spice brand aanu. Contact: {contact_link}")


def _button_reply(style: str, label: str) -> dict[str, Any]:
    normalized = normalize_message(label)
    if "മലയാള" in label or "malayalam" in normalized:
        return {
            "reply_text": "ശരി 👍 ഇനി മലയാളത്തിൽ സംസാരിക്കാം.\nഏത് product ആണ് നോക്കുന്നത്?",
            "intent": "button_reply",
            "journey_stage": "language_selected",
            "active_language": "malayalam",
            "waiting_for": "product",
        }
    if "english" in normalized:
        return {
            "reply_text": "Sure 👍 We can continue in English.\nWhich product are you looking for?",
            "intent": "button_reply",
            "journey_stage": "language_selected",
            "active_language": "english",
            "waiting_for": "product",
        }
    if "buy now" in normalized or "order" in normalized:
        return {
            "reply_text": {
                "english": "To order, send name, address, phone number, pincode, product and quantity.",
                "manglish": "Order cheyyan name, address, phone number, pincode, product, quantity ayacholu.",
                "malayalam": "Order ചെയ്യാൻ name, address, phone number, pincode, product, quantity അയച്ചോളൂ.",
            }.get(style, "Order cheyyan name, address, phone number, pincode, product, quantity ayacholu."),
            "intent": "order_request",
            "journey_stage": "waiting_for_address",
            "waiting_for": "address",
        }
    if "വിലാസ" in label or "address" in normalized:
        return {
            "reply_text": "Ith format-il ayacholu:\n\nName:\nPhone:\nAddress:\nPincode:\nProduct:\nQuantity:",
            "intent": "address_shared",
            "journey_stage": "waiting_for_address",
            "waiting_for": "address",
        }
    if "വില" in label or "price" in normalized or "spices" in normalized:
        return {
            "reply_text": {
                "english": "Spices price list ayakkam 👍\nBlack pepper, cardamom, clove, turmeric, cinnamon available aanu.\n\nWhich product price do you need?",
                "manglish": "Spices price list ayakkam 👍\nBlack pepper, cardamom, clove, turmeric, cinnamon available aanu.\n\nEth product vila aanu vendath?",
                "malayalam": "Spices price list അയക്കാം 👍\nBlack pepper, cardamom, clove, turmeric, cinnamon available ആണ്.\n\nഏത് product വില ആണ് വേണ്ടത്?",
            }.get(style, "Spices price list ayakkam 👍 Eth product vila aanu vendath?"),
            "intent": "price",
            "journey_stage": "product_interest",
            "waiting_for": "product",
        }
    return {
        "reply_text": {
            "english": "Button response received 👍 Which product are you looking for?",
            "manglish": "Button response kitti 👍 Eth product aanu nokkunnath?",
            "malayalam": "Button response കിട്ടി 👍 ഏത് product ആണ് നോക്കുന്നത്?",
        }.get(style, "Button response kitti 👍 Eth product aanu nokkunnath?"),
        "intent": "button_reply",
        "journey_stage": "product_interest",
        "waiting_for": "product",
    }


def deterministic_reply_for_message(
    *,
    incoming_message: str,
    context: dict[str, Any] | None = None,
    semantic_intent: str = "",
    product_detected: bool = False,
) -> dict[str, Any] | None:
    """Handle obvious journey messages before generic AI generation.

    This keeps high-frequency commerce turns short, stateful, and auditable.
    """
    context = context or {}
    normalized = normalize_message(incoming_message)
    style = _style(incoming_message, context)

    meta = context.get("message_meta") if isinstance(context.get("message_meta"), dict) else {}
    if normalized.startswith("#button reply#") or meta.get("structured_button_click") or str(meta.get("message_type") or "").lower() == "postback":
        mapped = _button_reply(style, _button_label(incoming_message, context))
        return {
            **mapped,
            "suggested_action": "send_reply",
            "should_escalate": False,
            "message_understanding": {
                "detected_intent": mapped.get("intent") or "button_reply",
                "detected_language": mapped.get("active_language") or style,
                "scenario": "button_handler",
            },
        }

    if semantic_intent == "payment_proof_shared" or ("[[media:image]]" in normalized and any(token in normalized for token in ("payment", "screenshot", "paid", "gpay", "upi"))):
        return {
            "reply_text": _payment_reply(style, proof_received=True),
            "intent": "payment",
            "suggested_action": "send_reply",
            "should_escalate": False,
            "journey_stage": "payment_review",
            "message_understanding": {"detected_intent": "payment", "detected_language": style, "scenario": "payment_review"},
        }

    if semantic_intent in {"payment_confirmation", "payment"}:
        return {
            "reply_text": _payment_reply(style, proof_received=bool(context.get("payment_screenshot_received"))),
            "intent": "payment",
            "suggested_action": "send_reply",
            "should_escalate": False,
            "journey_stage": "payment_pending",
            "message_understanding": {"detected_intent": "payment", "detected_language": style, "scenario": "payment_pending"},
        }

    if "[[media:audio]]" in normalized:
        return {
            "reply_text": {
                "english": "Audio kitti 👍 Text aayi product/order detail ayachaal fast aayi help cheyyam.",
                "manglish": "Audio kitti 👍 Product/order detail text aayi ayachaal fast aayi help cheyyam.",
                "malayalam": "Audio കിട്ടി 👍 Product/order detail text ആയി അയച്ചാൽ fast ആയി help ചെയ്യാം.",
            }.get(style, "Audio kitti 👍 Product/order detail text aayi ayachaal fast aayi help cheyyam."),
            "intent": "audio_received",
            "suggested_action": "send_reply",
            "should_escalate": False,
            "message_understanding": {"detected_intent": "audio_received", "detected_language": style, "scenario": "audio_received"},
        }

    if not product_detected and any(term in normalized for term in PLANT_TERMS):
        return {
            "reply_text": _plant_reply(style),
            "intent": "plant_inquiry",
            "suggested_action": "send_reply",
            "should_escalate": False,
            "message_understanding": {"detected_intent": "plant_inquiry", "detected_language": style, "scenario": "unsupported_category"},
        }

    if not product_detected and any(term in normalized for term in LOCATION_TERMS):
        return {
            "reply_text": _location_reply(style),
            "intent": "business_info",
            "suggested_action": "send_reply",
            "should_escalate": False,
            "message_understanding": {"detected_intent": "business_info", "detected_language": style, "scenario": "location_query"},
        }

    if not product_detected and any(term in normalized for term in ADDRESS_CONFIRM_TERMS):
        return {
            "reply_text": _address_reply(style),
            "intent": "address_shared",
            "suggested_action": "send_reply",
            "should_escalate": False,
            "journey_stage": "order_capture",
            "message_understanding": {"detected_intent": "address_shared", "detected_language": style, "scenario": "address_received"},
        }

    if not product_detected and (normalized in ACK_TERMS or re.fullmatch(r"(ok+|okay|yes|fine|sure)[.! ]*", normalized or "")):
        return {
            "reply_text": _ack_reply(style, context),
            "intent": "acknowledgement",
            "suggested_action": "send_reply",
            "should_escalate": False,
            "message_understanding": {"detected_intent": "acknowledgement", "detected_language": style, "scenario": "acknowledgement"},
        }

    return None
