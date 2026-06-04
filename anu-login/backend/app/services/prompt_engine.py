"""
app/services/prompt_engine.py

AI Prompt Template Engine.

Provides variable interpolation and safe rendering for personalized messages
using {{variable_name}} syntax. Integrates with OpenRouter for AI generation.

Usage:
    from app.services.prompt_engine import PromptEngine
    engine = PromptEngine()
    msg = engine.render("Hi {{first_name}}, try {{product}}!", {"first_name": "Priya", "product": "Ceylon Cinnamon"})
    ai_msg = engine.generate_personalized(template_id="order_confirm", variables={...})
"""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.storage import get_connection

logger = logging.getLogger(__name__)

# ── Safety limits ─────────────────────────────────────────────────────────────
MAX_TEMPLATE_LEN = 2000
MAX_OUTPUT_LEN   = 800
UNSAFE_PATTERNS  = re.compile(
    r"(SELECT\s|INSERT\s|DROP\s|DELETE\s|<script|javascript:|data:text)",
    re.IGNORECASE,
)

# ── 20 seed templates for immediate use ───────────────────────────────────────
SEED_TEMPLATES = [
    # Order Confirmation (5)
    {
        "id": "order_confirm_warm",
        "story_type": "order_confirmation",
        "product_category": "spices",
        "template_text": "Hi {{first_name}}! Your {{product_name}} is on its way 🌿 We handpicked it fresh from Kerala. Expected delivery: {{delivery_date}}. Track your order: {{tracking_url}}",
        "required_fields": '["first_name","product_name","delivery_date","tracking_url"]',
    },
    {
        "id": "order_confirm_professional",
        "story_type": "order_confirmation",
        "product_category": "spices",
        "template_text": "Order confirmed, {{first_name}}. Your {{product_name}} (Order #{{order_id}}) is being prepared with care. We source directly from {{origin_region}} for authentic quality.",
        "required_fields": '["first_name","product_name","order_id","origin_region"]',
    },
    {
        "id": "order_confirm_story",
        "story_type": "order_confirmation",
        "product_category": "cinnamon",
        "template_text": "{{first_name}}, your True Ceylon Cinnamon is being packed! Unlike grocery store cinnamon, yours is hand-rolled from inner bark in Sri Lanka — real {{product_name}} with 0.04% coumarin (grocery: 5-8%). Arriving {{delivery_date}}.",
        "required_fields": '["first_name","product_name","delivery_date"]',
    },
    {
        "id": "order_confirm_brief",
        "story_type": "order_confirmation",
        "product_category": "all",
        "template_text": "Thank you {{first_name}}! 🙏 {{product_name}} confirmed. Delivery in {{delivery_days}} days. Use code {{coupon_code}} for 10% off your next order.",
        "required_fields": '["first_name","product_name","delivery_days","coupon_code"]',
    },
    {
        "id": "order_confirm_upsell",
        "story_type": "order_confirmation",
        "product_category": "all",
        "template_text": "Order received, {{first_name}}! Your {{product_name}} will arrive by {{delivery_date}}. Customers who bought this also love {{related_product}} — add it to your next order and save {{discount_pct}}%.",
        "required_fields": '["first_name","product_name","delivery_date","related_product","discount_pct"]',
    },
    # Review Requests (5)
    {
        "id": "review_gentle",
        "story_type": "review_request",
        "product_category": "all",
        "template_text": "Hi {{first_name}}, we hope you're loving your {{product_name}}! 🌿 If you have a moment, we'd be grateful for your honest review. It helps other families find quality spices. {{review_url}}",
        "required_fields": '["first_name","product_name","review_url"]',
    },
    {
        "id": "review_with_story",
        "story_type": "review_request",
        "product_category": "spices",
        "template_text": "{{first_name}}, how is your {{product_name}} working out in the kitchen? 🍛 Our farmers in {{origin_region}} would love to hear! Your review helps us keep supporting direct-from-farm sourcing. {{review_url}}",
        "required_fields": '["first_name","product_name","origin_region","review_url"]',
    },
    {
        "id": "review_with_incentive",
        "story_type": "review_request",
        "product_category": "all",
        "template_text": "Hi {{first_name}}! 🌟 Leave a review for your {{product_name}} and get {{discount_pct}}% off your next order with code {{coupon_code}}. Your feedback means everything to us! {{review_url}}",
        "required_fields": '["first_name","product_name","discount_pct","coupon_code","review_url"]',
    },
    {
        "id": "review_followup",
        "story_type": "review_request",
        "product_category": "all",
        "template_text": "Just a gentle reminder, {{first_name}} — your review of {{product_name}} would really help other customers. Takes just 30 seconds! {{review_url}}",
        "required_fields": '["first_name","product_name","review_url"]',
    },
    {
        "id": "review_satisfaction",
        "story_type": "review_request",
        "product_category": "all",
        "template_text": "{{first_name}}, it's been {{days_since_delivery}} days since your {{product_name}} arrived. How are you finding it? 5-star quality is our goal — let us know if we've earned it. {{review_url}}",
        "required_fields": '["first_name","product_name","days_since_delivery","review_url"]',
    },
    # Replenishment (5)
    {
        "id": "replenish_gentle",
        "story_type": "replenishment",
        "product_category": "all",
        "template_text": "Hi {{first_name}} 🌿 You ordered {{product_name}} about {{days_ago}} days ago — running low? Reorder now and we'll dispatch same day. {{shop_url}}",
        "required_fields": '["first_name","product_name","days_ago","shop_url"]',
    },
    {
        "id": "replenish_urgency",
        "story_type": "replenishment",
        "product_category": "all",
        "template_text": "{{first_name}}, your {{product_name}} stock is likely running out! Don't let your kitchen miss it. Reorder with {{discount_pct}}% off using code {{coupon_code}}. {{shop_url}}",
        "required_fields": '["first_name","product_name","discount_pct","coupon_code","shop_url"]',
    },
    {
        "id": "replenish_bundle",
        "story_type": "replenishment",
        "product_category": "spices",
        "template_text": "Time to restock, {{first_name}}! Get {{product_name}} + {{bundle_product}} together and save {{bundle_discount}}%. Our Kerala Spice Bundle is perfect for daily cooking. {{shop_url}}",
        "required_fields": '["first_name","product_name","bundle_product","bundle_discount","shop_url"]',
    },
    {
        "id": "replenish_story",
        "story_type": "replenishment",
        "product_category": "cinnamon",
        "template_text": "{{first_name}}, true Ceylon Cinnamon loses potency after 6 months. Since you ordered {{days_ago}} days ago, it's a good time to refresh your stock for full health benefits. {{shop_url}}",
        "required_fields": '["first_name","days_ago","shop_url"]',
    },
    {
        "id": "replenish_vip",
        "story_type": "replenishment",
        "product_category": "all",
        "template_text": "VIP restock alert, {{first_name}}! As a loyal PureLeven customer, you get first access to our new {{product_name}} harvest. Limited stock — {{discount_pct}}% off with {{coupon_code}}. {{shop_url}}",
        "required_fields": '["first_name","product_name","discount_pct","coupon_code","shop_url"]',
    },
    # Special Offers (5)
    {
        "id": "offer_flash_sale",
        "story_type": "special_offer",
        "product_category": "all",
        "template_text": "⚡ 24-hour flash sale, {{first_name}}! {{discount_pct}}% off everything with code {{coupon_code}}. Sale ends {{expiry_time}}. Don't miss it! {{shop_url}}",
        "required_fields": '["first_name","discount_pct","coupon_code","expiry_time","shop_url"]',
    },
    {
        "id": "offer_seasonal",
        "story_type": "special_offer",
        "product_category": "spices",
        "template_text": "{{first_name}}, our {{season}} harvest is here! Fresh {{product_name}} from Kerala, harvested this {{month}}. {{discount_pct}}% early-bird discount with code {{coupon_code}}. {{shop_url}}",
        "required_fields": '["first_name","season","product_name","month","discount_pct","coupon_code","shop_url"]',
    },
    {
        "id": "offer_vip_exclusive",
        "story_type": "special_offer",
        "product_category": "all",
        "template_text": "Exclusive for you, {{first_name}} 🌟 As one of our top customers, you get {{discount_pct}}% off our premium collection before anyone else. Code {{coupon_code}} expires in 48 hours. {{shop_url}}",
        "required_fields": '["first_name","discount_pct","coupon_code","shop_url"]',
    },
    {
        "id": "offer_bundle",
        "story_type": "special_offer",
        "product_category": "all",
        "template_text": "Bundle and save, {{first_name}}! Buy {{product_name}} + {{bundle_product}} together for ₹{{bundle_price}} (save ₹{{savings}}). Best value we've ever offered. {{shop_url}}",
        "required_fields": '["first_name","product_name","bundle_product","bundle_price","savings","shop_url"]',
    },
    {
        "id": "offer_winback",
        "story_type": "special_offer",
        "product_category": "all",
        "template_text": "We miss you, {{first_name}}! It's been {{days_inactive}} days since your last order. Here's {{discount_pct}}% off to welcome you back — code {{coupon_code}} valid for 7 days. {{shop_url}}",
        "required_fields": '["first_name","days_inactive","discount_pct","coupon_code","shop_url"]',
    },
]


class PromptEngine:
    """Variable interpolation + AI personalization engine."""

    def __init__(self) -> None:
        self._ensure_seed_templates()

    def _ensure_seed_templates(self) -> None:
        """Populate ai_story_templates if empty."""
        try:
            with get_connection() as conn:
                count = conn.execute("SELECT COUNT(*) FROM ai_story_templates").fetchone()[0]
                if count >= len(SEED_TEMPLATES):
                    return  # Already seeded

                now = datetime.now(timezone.utc).isoformat()
                for tpl in SEED_TEMPLATES:
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO ai_story_templates
                          (id, story_type, product_category, template_text,
                           required_fields, approved, version, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, 1, 1, ?, ?)
                        """,
                        (
                            tpl["id"], tpl["story_type"], tpl["product_category"],
                            tpl["template_text"], tpl["required_fields"], now, now,
                        ),
                    )
        except Exception as exc:
            logger.warning("Could not seed story templates: %s", exc)

    def render(self, template_text: str, variables: dict[str, Any]) -> str:
        """
        Render {{variable}} placeholders from the variables dict.
        Raises ValueError if template or output fails safety checks.
        """
        if len(template_text) > MAX_TEMPLATE_LEN:
            raise ValueError(f"Template exceeds max length {MAX_TEMPLATE_LEN}")
        if UNSAFE_PATTERNS.search(template_text):
            raise ValueError("Template contains unsafe patterns")

        def replacer(match: re.Match) -> str:
            key = match.group(1).strip()
            val = variables.get(key, match.group(0))  # Leave {{key}} if no value
            return str(val)

        result = re.sub(r"\{\{(\w+)\}\}", replacer, template_text)

        if len(result) > MAX_OUTPUT_LEN:
            result = result[:MAX_OUTPUT_LEN] + "…"

        return result

    def get_template(
        self,
        story_type: str,
        product_category: str = "all",
        template_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Fetch a template by type/category or explicit ID."""
        with get_connection() as conn:
            if template_id:
                row = conn.execute(
                    "SELECT * FROM ai_story_templates WHERE id=? AND approved=1",
                    (template_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT * FROM ai_story_templates
                    WHERE story_type=? AND approved=1
                      AND (product_category=? OR product_category='all')
                    ORDER BY RANDOM() LIMIT 1
                    """,
                    (story_type, product_category),
                ).fetchone()
        return dict(row) if row else None

    def list_templates(self, story_type: str | None = None) -> list[dict[str, Any]]:
        """List all approved templates, optionally filtered by type."""
        with get_connection() as conn:
            if story_type:
                rows = conn.execute(
                    "SELECT * FROM ai_story_templates WHERE approved=1 AND story_type=? ORDER BY story_type, id",
                    (story_type,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM ai_story_templates WHERE approved=1 ORDER BY story_type, id",
                ).fetchall()
        return [dict(r) for r in rows]

    def render_for_journey(
        self,
        story_type: str,
        variables: dict[str, Any],
        product_category: str = "all",
        template_id: str | None = None,
    ) -> dict[str, Any]:
        """
        High-level: fetch template + render variables. Returns rendered text + metadata.
        Skips AI generation for speed; uses template directly.
        """
        template = self.get_template(story_type, product_category, template_id)
        if not template:
            # Fallback: simple formatted message
            return {
                "text": f"Hi {variables.get('first_name', 'there')}! 🌿 Your order is on the way.",
                "template_id": None,
                "story_type": story_type,
                "source": "fallback",
            }

        try:
            rendered = self.render(template["template_text"], variables)
        except ValueError as exc:
            logger.warning("Template render failed %s: %s", template["id"], exc)
            rendered = f"Hi {variables.get('first_name', 'there')}! Thank you for your order."

        return {
            "text": rendered,
            "template_id": template["id"],
            "story_type": story_type,
            "product_category": template["product_category"],
            "source": "template",
        }

    def generate_ai_personalized(
        self,
        story_type: str,
        variables: dict[str, Any],
        product_category: str = "all",
    ) -> dict[str, Any]:
        """
        Use OpenRouter to generate a personalized message using a template as seed.
        Falls back to direct template render if AI fails or key is missing.
        """
        template = self.get_template(story_type, product_category)
        if not template:
            return self.render_for_journey(story_type, variables, product_category)

        if not settings.openrouter_api_key:
            return self.render_for_journey(story_type, variables, product_category, template["id"])

        try:
            import urllib.request
            seed_text = self.render(template["template_text"], variables)
            prompt = (
                f"Rewrite this customer message to sound more personal and warm, "
                f"keeping it under 160 characters. Keep {{{{variable}}}} placeholders as-is. "
                f"Brand: PureLeven organic spices from Kerala.\n\nOriginal: {seed_text}"
            )

            payload = json.dumps({
                "model": "meta-llama/llama-3.1-8b-instruct:free",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
            }).encode()

            req = urllib.request.Request(
                f"{settings.openrouter_base_url}/chat/completions",
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "HTTP-Referer": "https://adsapi.pureleven.com",
                },
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                ai_text = data["choices"][0]["message"]["content"].strip()
                if len(ai_text) > MAX_OUTPUT_LEN:
                    ai_text = ai_text[:MAX_OUTPUT_LEN] + "…"
                return {
                    "text": ai_text,
                    "template_id": template["id"],
                    "story_type": story_type,
                    "source": "ai",
                }
        except Exception as exc:
            logger.warning("AI generation failed, using template: %s", exc)
            return self.render_for_journey(story_type, variables, product_category, template["id"])


# Module-level singleton
_engine: PromptEngine | None = None


def get_prompt_engine() -> PromptEngine:
    global _engine
    if _engine is None:
        _engine = PromptEngine()
    return _engine
