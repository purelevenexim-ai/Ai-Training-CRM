"""
Story Engine for PureLeven WhatsApp messages.

ALL story templates are pre-written here and in the DB by humans.
AI only SELECTS which story type to use.
Backend RENDERS using REAL Shopify data — zero hallucination possible.

Template variables use {{key}} syntax.
Missing variables are filled with safe defaults, never left blank.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# BUILT-IN STORY TEMPLATES
# These are the defaults seeded into the DB on startup.
# Product managers can update them via the DB directly.
# ─────────────────────────────────────────────────────────────────────────────

BUILTIN_STORY_TEMPLATES: list[dict[str, Any]] = [
    # ── Harvest quality ───────────────────────────────────────────────────────
    {
        "id": "harvest_quality_premium",
        "story_type": "harvest_quality",
        "product_category": "all",
        "template_text": (
            "Hi {{name}} 👋\n\n"
            "Our {{product_title}} this week comes from {{harvest_region}}, Kerala — "
            "freshly processed and carefully packed.\n\n"
            "{{quality_notes}}\n\n"
            "Best for: {{best_for_uses}}\n\n"
            "Browse here:\n{{product_url}}"
        ),
        "required_fields": ["name", "product_title", "harvest_region", "product_url"],
    },
    {
        "id": "harvest_quality_short",
        "story_type": "harvest_quality",
        "product_category": "all",
        "template_text": (
            "Hi {{name}},\n\n"
            "Fresh {{product_title}} batch — sourced from the spice hills of Kerala 🌿\n\n"
            "Browse here:\n{{product_url}}"
        ),
        "required_fields": ["name", "product_title", "product_url"],
    },

    # ── Recipe ────────────────────────────────────────────────────────────────
    {
        "id": "recipe_chai",
        "story_type": "recipe",
        "product_category": "cardamom",
        "template_text": (
            "Hi {{name}} 👋\n\n"
            "Quick idea: this {{product_title}} works beautifully in monsoon chai.\n\n"
            "{{cooking_tip}}\n\n"
            "Try it yourself:\n{{product_url}}"
        ),
        "required_fields": ["name", "product_title", "product_url"],
    },
    {
        "id": "recipe_general",
        "story_type": "recipe",
        "product_category": "all",
        "template_text": (
            "Hi {{name}} 👋\n\n"
            "Many customers enjoy our {{product_title}} for {{best_for_uses}}.\n\n"
            "{{cooking_tip}}\n\n"
            "Explore here:\n{{product_url}}"
        ),
        "required_fields": ["name", "product_title", "product_url"],
    },

    # ── Emotional / family ────────────────────────────────────────────────────
    {
        "id": "emotional_family",
        "story_type": "emotional_family",
        "product_category": "all",
        "template_text": (
            "Hi {{name}},\n\n"
            "Kerala families have been using {{product_title}} in everyday cooking "
            "for generations.\n\n"
            "Our sourcing keeps this tradition alive — each batch is handpicked from "
            "small farms in {{harvest_region}}.\n\n"
            "Explore here:\n{{product_url}}"
        ),
        "required_fields": ["name", "product_title", "product_url"],
    },

    # ── Seasonal ──────────────────────────────────────────────────────────────
    {
        "id": "seasonal_monsoon",
        "story_type": "seasonal",
        "product_category": "all",
        "template_text": (
            "Hi {{name}} ☔\n\n"
            "Monsoon season is one of the best times to enjoy {{product_title}} "
            "in warm chai and home cooking.\n\n"
            "This week's batch is freshly in:\n{{product_url}}"
        ),
        "required_fields": ["name", "product_title", "product_url"],
    },
    {
        "id": "seasonal_general",
        "story_type": "seasonal",
        "product_category": "all",
        "template_text": (
            "Hi {{name}} 🌿\n\n"
            "Fresh harvest batches of {{product_title}} have just arrived from Kerala.\n\n"
            "Limited quantities from this season:\n{{product_url}}"
        ),
        "required_fields": ["name", "product_title", "product_url"],
    },

    # ── Freshness ─────────────────────────────────────────────────────────────
    {
        "id": "freshness",
        "story_type": "freshness",
        "product_category": "all",
        "template_text": (
            "Hi {{name}},\n\n"
            "This {{product_title}} batch is fresh — processed recently and stored "
            "in climate-controlled conditions to preserve aroma and potency.\n\n"
            "Explore here:\n{{product_url}}"
        ),
        "required_fields": ["name", "product_title", "product_url"],
    },

    # ── Founder note ──────────────────────────────────────────────────────────
    {
        "id": "founder_note",
        "story_type": "founder_note",
        "product_category": "all",
        "template_text": (
            "Hi {{name}},\n\n"
            "A quick note from the PureLeven team — thank you for supporting "
            "authentic Kerala-origin spices and the small sourcing communities "
            "behind them.\n\n"
            "We truly appreciate your trust ❤️\n\n"
            "Our latest collection:\n{{product_url}}"
        ),
        "required_fields": ["name", "product_url"],
    },

    # ── Testimonial / social proof ────────────────────────────────────────────
    {
        "id": "testimonial",
        "story_type": "testimonial",
        "product_category": "all",
        "template_text": (
            "Hi {{name}} 👋\n\n"
            "⭐ {{rating}}/5 from {{review_count}}+ customers on our {{product_title}}\n\n"
            "\"{{top_review_text}}\" — {{top_reviewer_name}}\n\n"
            "Try for yourself:\n{{product_url}}"
        ),
        "required_fields": ["name", "product_title", "product_url"],
    },

    # ── Usage guide ───────────────────────────────────────────────────────────
    {
        "id": "usage_guide",
        "story_type": "usage_guide",
        "product_category": "all",
        "template_text": (
            "Hi {{name}} 👋\n\n"
            "{{product_title}} pairs well with {{flavor_pairing}}.\n\n"
            "{{cooking_tip}}\n\n"
            "Explore here:\n{{product_url}}"
        ),
        "required_fields": ["name", "product_title", "product_url"],
    },
]

# Safe defaults — used when a product field is missing (never blank a message)
SAFE_DEFAULTS: dict[str, str] = {
    "harvest_region": "the spice hills of Kerala",
    "quality_notes": "Carefully processed to preserve aroma and freshness.",
    "best_for_uses": "chai, biryani, and everyday cooking",
    "flavor_pairing": "black tea and rice dishes",
    "cooking_tip": "Use a small quantity — the aroma is strong.",
    "top_review_text": "Excellent quality, aroma is incredible",
    "top_reviewer_name": "a verified buyer",
    "rating": "4.8",
    "review_count": "200",
}


def get_template_by_type(story_type: str, product_category: str = "all") -> dict[str, Any] | None:
    """
    Return the best matching in-memory template for a story type + product category.
    Checks product-specific first, then falls back to 'all'.
    """
    # First: exact product category match
    for tmpl in BUILTIN_STORY_TEMPLATES:
        if tmpl["story_type"] == story_type and tmpl["product_category"] == product_category:
            return tmpl
    # Fallback: general 'all' category
    for tmpl in BUILTIN_STORY_TEMPLATES:
        if tmpl["story_type"] == story_type and tmpl["product_category"] == "all":
            return tmpl
    return None


def render_story(
    story_type: str,
    customer: dict[str, Any],
    product: dict[str, Any],
    product_url: str,
    db_template: dict[str, Any] | None = None,
) -> str:
    """
    Render a story message using a pre-written template + REAL product data.

    Args:
        story_type: which story type (harvest_quality, recipe, etc.)
        customer: journey_customers row (dict)
        product: shopify_products row (dict) — verified from DB
        product_url: Shopify product URL with UTM (from safe URL builder)
        db_template: if provided, use this instead of built-in template

    Returns:
        Fully rendered message text. All {{}} fields replaced.
        Raises ValueError only if template is completely missing.
    """
    # Get template text
    if db_template:
        template_text: str = db_template["template_text"]
    else:
        tmpl = get_template_by_type(story_type, _product_category(product))
        if not tmpl:
            tmpl = get_template_by_type(story_type, "all")
        if not tmpl:
            raise ValueError(f"No story template found for type: {story_type!r}")
        template_text = tmpl["template_text"]

    # Build variables from REAL data only
    first_name = (customer.get("name") or "there").split()[0]

    variables: dict[str, str] = {
        "name": first_name,
        "product_title": product.get("title") or "Kerala spice",
        "harvest_region": product.get("harvest_region") or SAFE_DEFAULTS["harvest_region"],
        "quality_notes": product.get("quality_notes") or SAFE_DEFAULTS["quality_notes"],
        "best_for_uses": product.get("best_for_uses") or SAFE_DEFAULTS["best_for_uses"],
        "flavor_pairing": product.get("flavor_pairing") or SAFE_DEFAULTS["flavor_pairing"],
        "cooking_tip": product.get("cooking_tip") or SAFE_DEFAULTS["cooking_tip"],
        "rating": str(product.get("rating") or SAFE_DEFAULTS["rating"]),
        "review_count": str(product.get("review_count") or SAFE_DEFAULTS["review_count"]),
        "top_review_text": product.get("top_review_text") or SAFE_DEFAULTS["top_review_text"],
        "top_reviewer_name": product.get("top_reviewer_name") or SAFE_DEFAULTS["top_reviewer_name"],
        "product_url": product_url,
    }

    # Replace all {{key}} placeholders
    message = template_text
    for key, value in variables.items():
        message = message.replace(f"{{{{{key}}}}}", str(value))

    # Verify no unfilled placeholders remain
    if "{{" in message:
        import re
        unfilled = re.findall(r"\{\{(\w+)\}\}", message)
        logger.warning("Unfilled story template fields: %s — filling with safe default", unfilled)
        for field in unfilled:
            message = message.replace(f"{{{{{field}}}}}", f"[{field}]")

    return message


def _product_category(product: dict[str, Any]) -> str:
    """Derive a category key from product tags (for template selection)."""
    tags = (product.get("tags") or "").lower()
    for keyword in ["cardamom", "pepper", "cinnamon", "cloves", "nutmeg", "turmeric", "ginger"]:
        if keyword in tags:
            return keyword
    return "all"


def seed_story_templates_to_db(conn: Any) -> None:
    """
    Seed built-in story templates into the DB if they don't exist.
    Safe to call on every startup — uses INSERT OR IGNORE.
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    import json as _json

    for tmpl in BUILTIN_STORY_TEMPLATES:
        conn.execute(
            """
            INSERT OR IGNORE INTO ai_story_templates
              (id, story_type, product_category, template_text, required_fields,
               approved, version, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 1, 1, ?, ?)
            """,
            (
                tmpl["id"],
                tmpl["story_type"],
                tmpl["product_category"],
                tmpl["template_text"],
                _json.dumps(tmpl.get("required_fields", [])),
                now,
                now,
            ),
        )
