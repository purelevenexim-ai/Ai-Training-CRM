from __future__ import annotations

import re
from typing import Any


SUPPORTED_INTENTS = (
    "availability",
    "price",
    "details",
    "quality",
    "origin",
    "processing",
    "usage",
    "benefits",
    "best_pack",
    "budget",
    "combo",
    "comparison",
    "price_objection",
    "delivery_charge",
    "delivery_time",
    "free_delivery",
    "order_request",
    "order_confirm",
    "wholesale",
    "gift",
    "stock_check",
    "complaint",
    "return_refund",
    "followup",
    "negation",
    "human_handoff",
    "business_info",
    "payment",
    "payment_confirmation",
    "payment_proof_shared",
    "address_shared",
    "acknowledgement",
    "plant_inquiry",
    "location_query",
    "button_reply",
    "audio_received",
    "fallback",
)

GREETING_PATTERN = re.compile(r"^(hi|hello|hey|hai|namaste|ഹായ്|assalam|vanakkam)\b", re.IGNORECASE)

INTENT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "availability": ("undo", "undu", "available", "stock", "kitumo", "kittumo", "kittuo", "undo?", "stock undo"),
    "price": ("price", "rate", "cost", "how much", "ethra", "vila", "amount", "charge", "mrp"),
    "details": ("details", "detail", "more info", "more expa info", "info", "kurich", "about this", "entha ith", "parayamo"),
    "quality": ("quality", "fresh", "best quality", "export quality", "nallathano", "fresh ano", "pure"),
    "origin": ("origin", "where from", "evide ninn", "source", "from where"),
    "processing": ("processed", "processing", "farm product", "cultivate", "engane undakkunnu", "how processed", "natural process"),
    "usage": ("how to use", "use", "engane use", "cooking", "tea", "fry", "fried rice"),
    "benefits": ("benefit", "benefits", "health benefit", "upayogam", "nallath entha"),
    "best_pack": ("best pack", "which size best", "eth pack", "regular use", "recommended", "best value"),
    "budget": ("small pack", "budget", "trial pack", "low budget", "cheapest"),
    "combo": ("combo", "offer", "combo pack", "bundle"),
    "comparison": ("difference", "compare", "comparison", "vs", "white vs black pepper", "cassia vs ceylon", "why yours"),
    "price_objection": ("expensive", "kooduthal", "discount", "rate kurakkan", "costly", "high rate"),
    "delivery_charge": ("delivery charge", "shipping charge", "courier charge", "delivery charge undo", "shipping charge undo"),
    "delivery_time": (
        "ethra divasam",
        "how many days",
        "when will arrive",
        "delivery eppo",
        "delivery time",
        "when reach",
        "delivery undo",
        "delivery",
        "shipping",
        "ship",
        "courier",
        "dispatch",
        "days delivery",
    ),
    "free_delivery": ("free delivery", "free shipping", "free delivery undo", "free shipping undo"),
    "order_request": (
        "order",
        "venam",
        "order cheyyam",
        "buy",
        "buy now",
        "edukkam",
        "need this",
        "place order",
        "engane ayakunath",
        "engane ayakkunath",
        "ayakunath",
        "ayakkunath",
        "ayakkum",
        "how to order",
        "how can i order",
        "how to buy",
    ),
    "order_confirm": ("confirm order", "order confirm", "cash paid", "paid", "payment done", "sent payment"),
    "wholesale": ("wholesale", "bulk", "reseller", "hotel", "restaurant", "b2b"),
    "gift": ("gift", "gift pack", "gift item"),
    "stock_check": ("stock check", "stock undo", "stock ano"),
    "complaint": (
        "complaint",
        "issue",
        "damaged",
        "broken",
        "wrong item",
        "late",
        "delay",
        "missing",
        "not received",
        "did not receive",
        "didn't receive",
        "not delivered",
    ),
    "return_refund": ("refund", "return", "replace", "money back"),
    "followup": (
        "follow up",
        "still available",
        "paranjille",
        "what next",
        "tomorrow",
        "let you know",
        "will let you know",
        "i will let you know",
        "i'll let you know",
        "nale",
        "naale",
        "നാളെ",
        "pinne parayam",
        "pinne nokkam",
        "later nokkam",
    ),
    "negation": ("venda", "vendam", "not interested", "dont want", "don't want", "no need"),
    "human_handoff": ("call me", "human", "agent", "owner", "direct", "speak to"),
    "business_info": ("who are you", "about pureleven", "location", "shop", "company", "farm"),
    "payment": (
        "gpay",
        "upi",
        "payment",
        "bank",
        "account number",
        "cash paid",
        "paid rs",
        "transaction",
        "paid",
        "payment done",
        "payment sent",
        "sent payment",
        "screenshot",
        "payment proof",
        "transaction ref",
    ),
    "address_shared": ("yes saved", "address saved", "sent address", "address sent", "ayachu", "save cheythu"),
    "acknowledgement": ("ok", "okay", "fine", "sure", "noted", "ശരി"),
    "plant_inquiry": ("plants", "plant", "plonts", "plont", "seedlings", "seedling", "green gold", "nalyani"),
    "location_query": ("location", "where is", "shop evide", "place evide", "evide aanu", "address evide"),
    "button_reply": ("#button reply#",),
    "audio_received": ("[[media:audio]]", "voice note", "audio"),
}


def normalize_message(message: str) -> str:
    text = (message or "").strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def detect_language(message: str) -> str:
    text = message or ""
    lower = text.lower()
    if any("\u0D00" <= ch <= "\u0D7F" for ch in text):
        return "malayalam"
    manglish_markers = (
        "undo",
        "undu",
        "venam",
        "venda",
        "ethra",
        "engane",
        "aano",
        "pincode",
        "ayakkum",
        "cheyyam",
        "parayamo",
        "kitti",
        "kitty",
        "nale",
    )
    if any(marker in lower for marker in manglish_markers):
        return "manglish"
    return "english"


def is_pure_greeting(message: str, *, product_detected: bool = False) -> bool:
    normalized = normalize_message(message)
    if not normalized or product_detected:
        return False
    if not GREETING_PATTERN.search(normalized):
        return False
    return len(normalized.split()) <= 3


def message_starts_with_greeting(message: str) -> bool:
    return bool(GREETING_PATTERN.search(normalize_message(message)))


def detect_intent(message: str, *, product_detected: bool = False) -> str:
    normalized = normalize_message(message)
    if not normalized:
        return "fallback"

    if product_detected:
        for intent in (
            "complaint",
            "return_refund",
            "wholesale",
            "payment",
            "followup",
            "negation",
            "combo",
            "comparison",
            "price_objection",
            "delivery_charge",
            "free_delivery",
            "delivery_time",
            "order_confirm",
            "order_request",
            "price",
            "details",
            "quality",
            "origin",
            "processing",
            "usage",
            "benefits",
            "best_pack",
            "budget",
            "gift",
            "stock_check",
            "availability",
        ):
            if any(keyword in normalized for keyword in INTENT_KEYWORDS.get(intent, ())):
                return intent
        if "delivery" in normalized or "shipping" in normalized or "courier" in normalized:
            return "delivery_time"
        if len(normalized.split()) <= 3:
            return "availability"
        return "fallback"

    for intent in (
        "complaint",
        "return_refund",
        "order_confirm",
        "payment",
        "address_shared",
        "plant_inquiry",
        "location_query",
        "human_handoff",
        "business_info",
        "wholesale",
        "acknowledgement",
        "followup",
        "combo",
        "delivery_charge",
        "free_delivery",
        "delivery_time",
    ):
        if any(keyword in normalized for keyword in INTENT_KEYWORDS.get(intent, ())):
            if intent == "order_confirm":
                return "payment"
            if intent == "location_query":
                return "business_info"
            return intent

    if "delivery" in normalized or "shipping" in normalized or "courier" in normalized:
        return "delivery_time"

    if is_pure_greeting(message):
        return "fallback"

    return "fallback"


def intent_metadata(message: str, *, product_detected: bool = False) -> dict[str, Any]:
    return {
        "normalized_message": normalize_message(message),
        "detected_language": detect_language(message),
        "detected_intent": detect_intent(message, product_detected=product_detected),
        "starts_with_greeting": message_starts_with_greeting(message),
        "is_pure_greeting": is_pure_greeting(message, product_detected=product_detected),
    }
