"""
Basil Commerce OS — Phase 5
whatsapp_templates.py

Registry of all 25 Pureleven WhatsApp templates.
Each entry maps a journey stage + customer segment to:
  - template_name  (must match approved Meta template)
  - body_params    (ordered text substitutions for {{1}}, {{2}}, ...)
  - button_params  (URL/quick-reply button parameter overrides)

Template approval: create these names in Meta Business Manager
(Wabis > Template Manager > New Template), then set status APPROVED
before the journey orchestrator will send them.

Variable builders accept a "customer" dict from journey_customers table.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.storage import get_connection


# ─── Site constants (override via env in a future pass) ──────────────────────

STORE_URL = "https://pureleven.com"
GOOGLE_REVIEW_URL = "https://g.page/r/pureleven/review"   # ← update to live URL
CALENDAR_URL = "https://calendly.com/pureleven/bulk"       # ← update to live URL
DELHIVERY_TRACK_URL = "https://www.delhivery.com/track/package"

# Product recommendation matrix (purchased handle → (display name, product URL))
_REC: dict[str, tuple[str, str]] = {
    "kerala-black-pepper-200gm":    ("Green Cardamom",     f"{STORE_URL}/products/green-cardamom-100g"),
    "green-cardamom-100g":          ("Ceylon Cinnamon",    f"{STORE_URL}/products/premium-cassia-cinnamon-200g"),
    "premium-cassia-cinnamon-200g": ("Premium Cloves",     f"{STORE_URL}/products/premium-cloves-100g"),
    "premium-cloves-100g":          ("Kerala Black Pepper",f"{STORE_URL}/products/kerala-black-pepper-200gm"),
    "white-pepper-100g":            ("Black Pepper",       f"{STORE_URL}/products/kerala-black-pepper-200gm"),
    "_default":                     ("Spice Combo Pack",   f"{STORE_URL}/products/spice-combo-pack"),
}
_LIFECYCLE_TEMPLATE_SETTING_KEY = "whatsapp_lifecycle_template_overrides"
_LIFECYCLE_STAGE_ALIASES = {
    "day1": "order_confirmed",
    "day2": "in_transit",
    "day5": "delivered",
    "day15": "review",
    "day30": "upsell",
    "day60": "corporate",
    "day75": "loyalty",
    "day95": "rfm",
}


logger = logging.getLogger(__name__)


# ─── Data model ──────────────────────────────────────────────────────────────

@dataclass
class TemplateSpec:
    name: str
    category: str        # TRANSACTIONAL | MARKETING
    journey_stage: str   # matches journey_customers.journey_stage value
    segment: str = "all" # all | vip | responsive | low | dormant


# ─── Registry ────────────────────────────────────────────────────────────────

REGISTRY: dict[str, TemplateSpec] = {
    # ── Delivery (3) ─────────────────────────────────────────────────────────
    "order_confirmed_v1":            TemplateSpec("order_confirmed_v1",            "TRANSACTIONAL", "order_confirmed"),
    "delivery_begun_v1":             TemplateSpec("delivery_begun_v1",             "TRANSACTIONAL", "in_transit"),
    "delivery_out_for_delivery_v1":  TemplateSpec("delivery_out_for_delivery_v1",  "TRANSACTIONAL", "out_for_delivery"),

    # ── Review (6) ───────────────────────────────────────────────────────────
    "delivered_review_request_v1":   TemplateSpec("delivered_review_request_v1",   "MARKETING", "delivered",      "all"),
    "delivered_vip_v1":              TemplateSpec("delivered_vip_v1",              "MARKETING", "delivered",      "vip"),
    "review_incentive_v1":           TemplateSpec("review_incentive_v1",           "MARKETING", "review",         "responsive"),
    "review_faq_response_v1":        TemplateSpec("review_faq_response_v1",        "MARKETING", "review_faq",     "all"),
    "review_reminder_v1":            TemplateSpec("review_reminder_v1",            "MARKETING", "review_reminder","responsive"),
    "review_thank_you_v1":           TemplateSpec("review_thank_you_v1",           "MARKETING", "review_submitted","all"),

    # ── Upsell (5) ───────────────────────────────────────────────────────────
    "explore_products_v1":           TemplateSpec("explore_products_v1",           "MARKETING", "upsell",         "responsive"),
    "upsell_followup_v1":            TemplateSpec("upsell_followup_v1",            "MARKETING", "upsell_followup","responsive"),
    "price_sensitive_sale_v1":       TemplateSpec("price_sensitive_sale_v1",       "MARKETING", "upsell_sale",    "responsive"),

    # ── B2B (3) ──────────────────────────────────────────────────────────────
    "corporate_pitch_high_v1":       TemplateSpec("corporate_pitch_high_v1",       "MARKETING", "corporate",      "responsive"),
    "corporate_pitch_low_v1":        TemplateSpec("corporate_pitch_low_v1",        "MARKETING", "corporate",      "low"),
    "corporate_followup_v1":         TemplateSpec("corporate_followup_v1",         "MARKETING", "corporate_followup","all"),

    # ── Loyalty (3) ──────────────────────────────────────────────────────────
    "loyalty_checkin_v1":            TemplateSpec("loyalty_checkin_v1",            "MARKETING", "loyalty",        "responsive"),
    "vip_exclusive_v1":              TemplateSpec("vip_exclusive_v1",              "MARKETING", "rfm",            "vip"),
    "repeat_buyer_exclusive_v1":     TemplateSpec("repeat_buyer_exclusive_v1",     "MARKETING", "rfm",            "responsive"),

    # ── Winback (3) ──────────────────────────────────────────────────────────
    "winback_offer_v1":              TemplateSpec("winback_offer_v1",              "MARKETING", "rfm",            "low"),
    "extreme_winback_v1":            TemplateSpec("extreme_winback_v1",            "MARKETING", "rfm",            "dormant"),
    "reactivation_survey_v1":        TemplateSpec("reactivation_survey_v1",        "MARKETING", "rfm",            "dormant"),

    # ── Seasonal (5) ─────────────────────────────────────────────────────────
    "promo_monsoon_v1":              TemplateSpec("promo_monsoon_v1",              "MARKETING", "seasonal",       "responsive"),
    "promo_diwali_v1":               TemplateSpec("promo_diwali_v1",               "MARKETING", "seasonal",       "all"),
    "promo_new_harvest_v1":          TemplateSpec("promo_new_harvest_v1",          "MARKETING", "seasonal",       "responsive"),
    "promo_bulk_sale_v1":            TemplateSpec("promo_bulk_sale_v1",            "MARKETING", "seasonal",       "all"),
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _utm(url: str, template: str, stage: str, customer_id: str) -> str:
    sep = "&" if "?" in url else "?"
    return (
        f"{url}{sep}utm_source=whatsapp"
        f"&utm_medium={template}"
        f"&utm_campaign={stage}"
        f"&utm_content={customer_id}"
    )


def _first_name(customer: dict[str, Any]) -> str:
    return ((customer.get("name") or "there").split()[0])


def _days_since(iso_ts: str | None) -> int:
    if not iso_ts:
        return 0
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        return max(0, int((datetime.now(timezone.utc) - dt).total_seconds() / 86400))
    except ValueError:
        return 0


def _get_recommendation(handle: str | None) -> tuple[str, str]:
    return _REC.get(handle or "", _REC["_default"])


# ─── Variable builder ────────────────────────────────────────────────────────

MessageVars = tuple[str, list[str], list[dict[str, Any]]]
"""(template_name, body_params, button_params)"""


def _canonical_lifecycle_stage(stage: str) -> str:
    normalized = str(stage or "").strip().lower()
    return _LIFECYCLE_STAGE_ALIASES.get(normalized, normalized)


def _load_lifecycle_stage_overrides() -> dict[str, Any]:
    try:
        with get_connection() as connection:
            row = connection.execute(
                "SELECT setting_value FROM app_settings WHERE setting_key = ?",
                (_LIFECYCLE_TEMPLATE_SETTING_KEY,),
            ).fetchone()
    except Exception:  # noqa: BLE001
        return {}

    if not row or not row["setting_value"]:
        return {}

    try:
        payload = json.loads(row["setting_value"])
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _take_override_values(values: list[str], count: int, prefix: str) -> list[str]:
    next_values = [str(value) for value in values[:count]]
    while len(next_values) < count:
        next_values.append(f"{prefix} {len(next_values) + 1}")
    return next_values


def _build_lifecycle_override_message(
    stage: str,
    customer: dict[str, Any],
    override: dict[str, Any],
    *,
    cid: str,
    name: str,
    waybill: str,
    eta: str,
    order_id: str,
    total_paise: int,
    coupon: str,
    rec_handle: str | None,
) -> MessageVars:
    template_name = str(override.get("template_name") or "").strip()
    if not template_name:
        raise ValueError("Lifecycle override missing template_name")

    signature = override.get("signature") if isinstance(override.get("signature"), dict) else {}
    body_var_count = int(signature.get("body_vars") or 0)
    button_specs = signature.get("buttons") if isinstance(signature.get("buttons"), list) else []

    track_url = f"{DELHIVERY_TRACK_URL}/{waybill}" if waybill else f"{STORE_URL}/account/orders"
    review_url = _utm(GOOGLE_REVIEW_URL, template_name, stage, cid)
    shop_url = _utm(STORE_URL, template_name, stage, cid)
    cal_url = _utm(CALENDAR_URL, template_name, stage, cid)
    rec_name, rec_url_raw = _get_recommendation(rec_handle)
    rec_url = _utm(rec_url_raw, template_name, stage, cid)
    total_inr = f"₹{total_paise // 100:,}"
    days_since = str(_days_since(customer.get("delivered_at") or customer.get("journey_started_at")))

    body_pools: dict[str, list[str]] = {
        "order_confirmed": [name, order_id or "Order", eta],
        "in_transit": [name, waybill or "Tracking ID", eta, track_url],
        "delivered": [name, review_url, order_id or "Order delivered", coupon],
        "review": [name, "₹200", review_url, coupon],
        "upsell": [name, rec_name, rec_url, "EXPLORE20"],
        "corporate": [name, total_inr, cal_url],
        "loyalty": [name, days_since, shop_url, "WELCOME20"],
        "rfm": [name, shop_url, "COMEBACK", "₹1,000"],
    }
    button_pools: dict[str, list[str]] = {
        "order_confirmed": [track_url],
        "in_transit": [track_url],
        "delivered": [review_url],
        "review": [review_url],
        "upsell": [rec_url],
        "corporate": [cal_url],
        "loyalty": [shop_url],
        "rfm": [shop_url],
    }

    body_params = _take_override_values(body_pools.get(stage, [name, shop_url]), body_var_count, "Value")
    button_seed = button_pools.get(stage, [shop_url])
    button_params: list[dict[str, Any]] = []
    for button in button_specs:
        vars_needed = int(button.get("vars") or 0)
        if vars_needed <= 0:
            continue
        values = _take_override_values(button_seed, vars_needed, "Link")
        button_params.append({
            "sub_type": str(button.get("sub_type") or "url").lower(),
            "index": int(button.get("index") or 0),
            "parameters": [{"type": "text", "text": value} for value in values],
        })

    return template_name, body_params, button_params


def build_message_vars(stage: str, customer: dict[str, Any]) -> MessageVars:
    """
    Given a journey stage and a journey_customers row (as dict), return
    (template_name, body_params, button_params) ready for wabis_client.send_template_message.

    body_params are ordered text substitutions for {{1}}, {{2}}, ...
    button_params are Wabis button component overrides for dynamic URL buttons.
    """
    cid  = customer.get("id", "")
    name = _first_name(customer)
    waybill  = customer.get("waybill_id", "")
    eta      = customer.get("estimated_delivery_at", "2-5 business days")
    order_id = customer.get("shopify_order_id", "")
    order_paise = int(customer.get("order_value_paise", 0))
    total_paise = int(customer.get("total_spent_paise", 0))
    score    = float(customer.get("engagement_score", 0))
    segment  = customer.get("customer_segment", "low")
    coupon   = customer.get("review_coupon_code") or f"REVIEW{cid[:6].upper()}"
    rec_handle = customer.get("day30_product_recommended")

    canonical_stage = _canonical_lifecycle_stage(stage)
    override = _load_lifecycle_stage_overrides().get(canonical_stage)
    if isinstance(override, dict):
        try:
            return _build_lifecycle_override_message(
                canonical_stage,
                customer,
                override,
                cid=cid,
                name=name,
                waybill=waybill,
                eta=eta,
                order_id=order_id,
                total_paise=total_paise,
                coupon=coupon,
                rec_handle=rec_handle,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Lifecycle template override fallback for stage=%s template=%s error=%s", canonical_stage, override.get("template_name"), exc)

    track_url = f"{DELHIVERY_TRACK_URL}/{waybill}" if waybill else f"{STORE_URL}/account/orders"

    def utm(url: str, tmpl: str) -> str:
        return _utm(url, tmpl, stage, cid)

    def btn_url(url: str, idx: int = 0) -> dict[str, Any]:
        return {"sub_type": "url", "index": idx, "parameters": [{"type": "text", "text": url}]}

    # ── Stage dispatch ────────────────────────────────────────────────────────
    # body_params count must exactly match Meta template {{N}} placeholders.
    # btn_params: only transactional templates (order_confirmed, delivery_begun,
    # delivery_out_for_delivery) have dynamic URL buttons (btn_params=1).
    # All marketing templates have btn_params=0 — buttons are static in template.

    # ── Transactional: Delivery (body 3,3,2 / btn 1,1,1) ─────────────────────
    if stage in ("order_confirmed", "day1"):
        t = "order_confirmed_v1"
        return t, [name, order_id, eta], [btn_url(utm(track_url, t))]

    if stage in ("in_transit", "day2"):
        t = "delivery_begun_v1"
        return t, [name, waybill or "N/A", eta], [btn_url(utm(track_url, t))]

    if stage in ("out_for_delivery",):
        t = "delivery_out_for_delivery_v1"
        return t, [name, waybill or "N/A"], [btn_url(utm(track_url, t))]

    # ── Review & Feedback (btn=0 for all) ─────────────────────────────────────
    if stage in ("delivered", "day5"):
        t = "delivered_vip_v1" if order_paise >= 50_000 else "delivered_review_request_v1"
        review = utm(GOOGLE_REVIEW_URL, t)
        return t, [name, review], []  # body=2, btn=0

    if stage in ("review", "day15"):
        t = "review_incentive_v1"
        review = utm(GOOGLE_REVIEW_URL, t)
        return t, [name, "₹200", review, coupon], []  # body=4, btn=0

    if stage in ("review_reminder", "day18"):
        t = "review_reminder_v1"
        review = utm(GOOGLE_REVIEW_URL, t)
        return t, [name, review, coupon], []  # body=3, btn=0

    if stage in ("review_faq",):
        t = "review_faq_response_v1"
        faq = utm(f"{STORE_URL}/pages/faq", t)
        return t, [name, faq], []  # body=2, btn=0

    if stage in ("review_submitted",):
        t = "review_thank_you_v1"
        shop = utm(STORE_URL, t)
        return t, [name, shop], []  # body=2, btn=0

    # ── Upsell & Cross-sell (btn=0 for all) ───────────────────────────────────
    if stage in ("upsell", "day30"):
        t = "explore_products_v1"
        rec_name, rec_url = _get_recommendation(rec_handle)
        rec_utm = utm(rec_url, t)
        return t, [name, rec_name, rec_utm, "EXPLORE20"], []  # body=4, btn=0

    if stage in ("upsell_followup", "day35"):
        t = "upsell_followup_v1"
        rec_name, rec_url = _get_recommendation(rec_handle)
        rec_utm = utm(rec_url, t)
        return t, [name, rec_name, rec_utm], []  # body=3, btn=0

    if stage in ("upsell_sale",):
        t = "price_sensitive_sale_v1"
        rec_name, rec_url = _get_recommendation(rec_handle)
        rec_utm = utm(rec_url, t)
        return t, [name, rec_name, rec_utm, "SALE25"], []  # body=4, btn=0

    # ── B2B Corporate (btn=0 for all) ─────────────────────────────────────────
    if stage in ("corporate", "day60"):
        total_inr = f"₹{total_paise // 100:,}"
        if score >= 40:
            t = "corporate_pitch_high_v1"
            cal = utm(CALENDAR_URL, t)
            return t, [name, total_inr, cal], []  # body=3, btn=0
        else:
            t = "corporate_pitch_low_v1"
            return t, [name, total_inr], []  # body=2, btn=0

    if stage in ("corporate_followup",):
        t = "corporate_followup_v1"
        cal = utm(CALENDAR_URL, t)
        return t, [name, cal], []  # body=2, btn=0

    # ── Loyalty & Repeat (btn=0 for all) ──────────────────────────────────────
    if stage in ("loyalty", "day75"):
        t = "loyalty_checkin_v1"
        days = _days_since(customer.get("delivered_at") or customer.get("journey_started_at"))
        shop = utm(STORE_URL, t)
        return t, [name, str(days), shop, "WELCOME20"], []  # body=4, btn=0

    # ── Seasonal / Promotional (btn=0 for all) ────────────────────────────────
    if stage in ("seasonal", "promo_monsoon"):
        t = "promo_monsoon_v1"
        shop = utm(f"{STORE_URL}/collections/all?filter=monsoon", t)
        return t, [name, shop], []  # body=2, btn=0

    if stage in ("promo_diwali",):
        t = "promo_diwali_v1"
        shop = utm(f"{STORE_URL}/collections/all?filter=diwali", t)
        return t, [name, shop], []  # body=2, btn=0

    if stage in ("promo_new_harvest",):
        t = "promo_new_harvest_v1"
        shop = utm(f"{STORE_URL}/collections/all?filter=harvest", t)
        return t, [name, shop], []  # body=2, btn=0

    if stage in ("promo_bulk_sale",):
        t = "promo_bulk_sale_v1"
        shop = utm(f"{STORE_URL}/collections/all?filter=bulk", t)
        return t, [name, shop], []  # body=2, btn=0

    # ── RFM & Reactivation (btn=0 for all) ───────────────────────────────────
    if stage in ("reactivation_survey",):
        t = "reactivation_survey_v1"
        return t, [name], []  # body=1, btn=0

    if stage in ("rfm", "day95"):
        if segment == "vip":
            t = "vip_exclusive_v1"
            url = utm(f"{STORE_URL}/collections/all", t)
            return t, [name, url], []  # body=2, btn=0
        elif segment == "responsive":
            t = "repeat_buyer_exclusive_v1"
            url = utm(STORE_URL, t)
            return t, [name, url], []  # body=2, btn=0
        elif segment == "low":
            t = "winback_offer_v1"
            url = utm(STORE_URL, t)
            return t, [name, url, "COMEBACK"], []  # body=3, btn=0
        else:  # dormant / churned
            t = "extreme_winback_v1"
            url = utm(STORE_URL, t)
            return t, [name, url, "₹1,000"], []  # body=3, btn=0

    # ── JOURNEY: Lead Nurturing (5 stages) ──────────────────────────────────
    # Each stage uses a UNIQUE approved template with proper {{1}}, {{2}} vars.

    if stage == "lead_segment_question":
        # "Hi Basil, quick question 🙏 — what happened? Why didn't you buy?"
        return "reactivation_survey_v1", [name], []

    if stage == "lead_trust_story":
        # "Hi Basil, fresh 2026 harvest has arrived! 🌿 — trust-building"
        t = "promo_new_harvest_v1"
        shop = utm(f"{STORE_URL}/collections/all", t)
        return t, [name, shop], []

    if stage == "lead_social_proof":
        # "Hi Basil, because you love Pureleven! 💚 — social proof / loyalty"
        t = "repeat_buyer_exclusive_v1"
        shop = utm(STORE_URL, t)
        return t, [name, shop], []

    if stage == "lead_education":
        # "Hi Basil, time to explore! 🌿 — educational about products"
        t = "explore_products_v1"
        rec_name = "Malabar Black Pepper"
        rec_url = utm(f"{STORE_URL}/products/kerala-black-pepper-200gm", t)
        return t, [name, rec_name, rec_url, "EXPLORE20"], []

    if stage == "lead_cta_urgency":
        # "Hi Basil, bulk sale alert! 📦 — urgency CTA"
        t = "promo_bulk_sale_v1"
        shop = utm(f"{STORE_URL}/collections/all", t)
        return t, [name, shop], []

    # ── JOURNEY: Abandoned Cart Recovery (5 stages) ──────────────────────────

    if stage == "cart_curiosity":
        # "Hi Basil, spices in your cart are flying off the shelves ⏳"
        return "shopify_abandonded_checkout_remainder_240", [name], []

    if stage == "cart_fomo":
        # "Hi Basil, sale alert! 🎉 — FOMO on cart items"
        t = "price_sensitive_sale_v1"
        shop = utm(STORE_URL, t)
        return t, [name, "Kerala Spices", "15", shop], []

    if stage == "cart_risk_removal":
        # "Still thinking about Pureleven Spices? — risk removal"
        t = "upsell_followup_v1"
        shop = utm(STORE_URL, t)
        return t, [name, "Pureleven Spices", shop], []

    if stage == "cart_social_proof":
        # "Hi Basil, we miss you! — loyalty social proof"
        t = "loyalty_checkin_v1"
        shop = utm(STORE_URL, t)
        return t, [name, "30", "WELCOME20", shop], []

    if stage == "cart_last_chance":
        # "Hi Basil, last call! 🎁 — final urgency"
        t = "extreme_winback_v1"
        shop = utm(STORE_URL, t)
        return t, [name, "₹75", shop], []

    # ── JOURNEY: Post-Purchase Delight (5 stages) ────────────────────────────

    if stage == "order_confirmed_trust":
        # "Hi Basil, VIP tier unlocked! 👑 — order trust/gratitude"
        t = "vip_exclusive_v1"
        shop = utm(STORE_URL, t)
        return t, [name, shop], []

    if stage == "order_excitement":
        # "Hi Basil, your order has arrived — thank you! 🙏"
        t = "delivered_vip_v1"
        review = utm(GOOGLE_REVIEW_URL, t)
        return t, [name, review], []

    if stage == "order_quality_check":
        # "Your Pureleven spices have arrived! 😊 Hi Basil, how's the quality?"
        t = "delivered_review_request_v1"
        review = utm(GOOGLE_REVIEW_URL, t)
        return t, [name, review], []

    if stage == "order_delight_story":
        # "⭐ Basil, your review unlocks ₹200 off your next order!"
        t = "review_incentive_v1"
        review = utm(GOOGLE_REVIEW_URL, t)
        coupon_code = customer.get("review_coupon_code", "REVIEW200")
        return t, [name, "₹200", review, coupon_code], []

    if stage == "order_repeat_offer":
        # "Hi Basil, we haven't seen you in a while! — repeat purchase offer"
        t = "winback_offer_v1"
        shop = utm(STORE_URL, t)
        return t, [name, "LOYAL500", shop], []

    # ── REVIEW JOURNEY: Psychology-first post-purchase sequence ─────────────
    # Sequence: Appreciation → Review → Return Visit → Repeat Purchase
    # Day 15: Pure appreciation + review CTA (NO discount — preserve authenticity)
    # Day 18a: If reviewed  → Thank you + loyalty tag + cross-sell
    # Day 18b: If NOT reviewed → Subtle cross-sell nudge
    # Day 45: Replenishment reminder (personalised to purchased product)
    # Day 75: VIP exclusive offer (for those who engaged)

    if stage == "review_pure_day15":
        # Appreciation-first review request, no discount, no pressure
        t = "review_request_pure_v1"
        review = utm(GOOGLE_REVIEW_URL, t)
        shop = utm(STORE_URL, t)
        product = customer.get("purchased_product_name", "our products")
        return t, [name, product, review, shop], []  # body=4, btn=0

    if stage == "review_thanks_day18":
        # Thank-you message IF the customer submitted a review
        t = "review_thanks_loyalty_v1"
        rec_handle_val = customer.get("purchased_product_handle") or customer.get("day30_product_recommended")
        rec_name, rec_url = _get_recommendation(rec_handle_val)
        shop = utm(rec_url, t)
        return t, [name, customer.get("purchased_product_name", "your purchase"), rec_name, shop], []  # body=4, btn=0

    if stage == "crosssell_day18":
        # Cross-sell nudge for those who DID NOT review (gentle, no mention of review)
        t = "upsell_followup_v1"
        rec_handle_val = customer.get("purchased_product_handle") or customer.get("day30_product_recommended")
        rec_name, rec_url = _get_recommendation(rec_handle_val)
        shop = utm(rec_url, t)
        return t, [name, rec_name, shop], []  # body=3, btn=0

    if stage == "replenishment_day45":
        # Replenishment reminder — remind them their product may be running low
        t = "replenishment_reminder_v1"
        product = customer.get("purchased_product_name", "your Pureleven spices")
        shop = utm(f"{STORE_URL}/collections/all", t)
        return t, [name, product, shop], []  # body=3, btn=0

    if stage == "vip_day75":
        # VIP exclusive offer for loyal / engaged customers
        t = "vip_exclusive_v1"
        shop = utm(f"{STORE_URL}/collections/all?utm_campaign=vip_day75", t)
        return t, [name, shop], []  # body=2, btn=0

    # Fallback (should not reach here in normal operation)
    raise ValueError(f"Unknown journey stage: {stage!r}")
