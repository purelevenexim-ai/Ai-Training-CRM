"""
Product Recommendation Engine — PureLeven

Replaces the static _REC lookup table in whatsapp_templates.py with
AI-driven cross-sell recommendations.

Features:
  - AI picks top 3 complementary products with reasoning
  - Only recommends from verified PureLeven categories (via url_config)
  - Falls back to static matrix if AI unavailable
  - Wraps each recommendation with a verified purchase URL
  - 7-day cache per customer to reduce API calls
"""

from __future__ import annotations

import logging
from typing import Any

from app.url_config import urls
from app.services.ai_enhancement_service import AIEnhancementService

logger = logging.getLogger(__name__)

# ── Verified PureLeven product catalog ────────────────────────────────────────
# Maps category slug → display name + URL method
PRODUCT_CATALOG: dict[str, dict[str, Any]] = {
    "turmeric": {
        "display_name": "Organic Turmeric Powder",
        "url": urls.PRODUCTS_TURMERIC,
        "tagline": "Anti-inflammatory superfood from Kerala farms",
    },
    "ghee": {
        "display_name": "Organic A2 Ghee",
        "url": urls.PRODUCTS_GHEE,
        "tagline": "Traditionally churned, pure and golden",
    },
    "spices": {
        "display_name": "Premium Spice Collection",
        "url": urls.PRODUCTS_SPICES,
        "tagline": "Whole and ground spices, farm-sourced",
    },
    "supplements": {
        "display_name": "Organic Supplements",
        "url": urls.PRODUCTS_SUPPLEMENTS,
        "tagline": "Nature's best in every capsule",
    },
    "bundles": {
        "display_name": "Spice Combo Pack",
        "url": urls.PRODUCTS_PAGE,
        "tagline": "Best value — everything you need",
    },
}

ALLOWED_CATEGORIES = list(PRODUCT_CATALOG.keys())


class ProductRecommendationEngine:
    """AI-driven product recommendation engine with verified URL resolution."""

    @staticmethod
    def get_recommendations(
        customer_id: str,
        purchased_product: str,
        customer_segment: str = "new",
        purchase_count: int = 1,
        utm_campaign: str = "product_rec",
        count: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Get top N product recommendations for a customer.

        Returns a list of recommendation dicts:
          [{category, product_name, tagline, url, reason}, ...]

        Always returns valid recs — falls back to static cross-sell if AI fails.
        """
        ai_result = AIEnhancementService.get_product_recommendations(
            customer_id=customer_id,
            purchased_product=purchased_product,
            customer_segment=customer_segment,
            purchase_count=purchase_count,
        )

        raw_recs = ai_result.get("recommendations", [])
        enriched = []

        for rec in raw_recs[:count]:
            category = rec.get("category", "").lower()
            catalog_entry = PRODUCT_CATALOG.get(category)

            if not catalog_entry:
                # AI returned invalid category despite validation — skip
                logger.warning("Recommendation engine skipping unknown category: %s", category)
                continue

            product_url = urls.get_product_link(
                category=category,
                utm_source="email",
                utm_medium="email",
                utm_campaign=utm_campaign,
            )

            enriched.append({
                "category": category,
                "product_name": rec.get("product_name") or catalog_entry["display_name"],
                "tagline": catalog_entry["tagline"],
                "url": product_url,
                "reason": rec.get("reason", ""),
                "source": ai_result.get("source", "ai"),
            })

        # Pad with static fallbacks if we got fewer than requested
        if len(enriched) < count:
            enriched.extend(_static_fallback_recs(purchased_product, utm_campaign, count - len(enriched)))

        return enriched[:count]

    @staticmethod
    def get_top_recommendation(
        customer_id: str,
        purchased_product: str,
        customer_segment: str = "new",
        purchase_count: int = 1,
        utm_campaign: str = "product_rec",
    ) -> dict[str, Any]:
        """
        Get the single best product recommendation.
        Convenience wrapper around get_recommendations().
        """
        recs = ProductRecommendationEngine.get_recommendations(
            customer_id=customer_id,
            purchased_product=purchased_product,
            customer_segment=customer_segment,
            purchase_count=purchase_count,
            utm_campaign=utm_campaign,
            count=1,
        )
        if recs:
            return recs[0]

        # Ultimate fallback — spice combo
        return {
            "category": "bundles",
            "product_name": "Spice Combo Pack",
            "tagline": "Best value — everything you need",
            "url": urls.PRODUCTS_PAGE,
            "reason": "Complete your organic pantry",
            "source": "ultimate_fallback",
        }

    @staticmethod
    def format_for_email(
        recs: list[dict[str, Any]],
        brand_color: str = "#2E7D32",
        bg_color: str = "#F9FBF9",
    ) -> str:
        """
        Render product recommendations as HTML cards for email templates.

        Returns: HTML string with product cards
        """
        if not recs:
            return ""

        cards = ""
        for rec in recs:
            cards += f"""
<table cellpadding="0" cellspacing="0" style="margin:12px 0;background:{bg_color};border-radius:8px;width:100%;border:1px solid #E5E7EB;">
  <tr>
    <td style="padding:16px;vertical-align:top;">
      <p style="margin:0 0 4px;font-weight:bold;font-size:15px;color:#1A1A1A;">{rec['product_name']}</p>
      <p style="margin:0 0 8px;font-size:13px;color:#6B7280;">{rec['tagline']}</p>
      <p style="margin:0 0 10px;font-size:13px;color:#374151;font-style:italic;">{rec['reason']}</p>
      <a href="{rec['url']}" style="display:inline-block;background:{brand_color};color:#ffffff;padding:10px 20px;border-radius:6px;text-decoration:none;font-size:14px;font-weight:bold;">View Product →</a>
    </td>
  </tr>
</table>"""

        return cards


# ── Private helpers ───────────────────────────────────────────────────────────

def _static_fallback_recs(
    purchased_product: str,
    utm_campaign: str,
    count: int,
) -> list[dict[str, Any]]:
    """Static cross-sell fallback when AI recommendations are insufficient."""
    lower = purchased_product.lower()

    fallback_matrix = {
        "turmeric": ["ghee", "spices", "bundles"],
        "ghee":     ["turmeric", "spices", "bundles"],
        "spice":    ["turmeric", "ghee", "bundles"],
        "default":  ["bundles", "turmeric", "ghee"],
    }

    key = next((k for k in fallback_matrix if k in lower), "default")
    categories = fallback_matrix[key][:count]

    result = []
    for cat in categories:
        entry = PRODUCT_CATALOG.get(cat, PRODUCT_CATALOG["bundles"])
        product_url = urls.get_product_link(
            category=cat,
            utm_source="email",
            utm_medium="email",
            utm_campaign=utm_campaign,
        )
        result.append({
            "category": cat,
            "product_name": entry["display_name"],
            "tagline": entry["tagline"],
            "url": product_url,
            "reason": "Pairs well with your purchase",
            "source": "static_fallback",
        })

    return result
