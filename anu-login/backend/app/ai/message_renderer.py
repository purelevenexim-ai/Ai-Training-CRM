"""
Safe message renderer for PureLeven WhatsApp.

Takes an AI decision (tone, story_type, product_id, cta_type, urgency)
and renders a complete WhatsApp message using ONLY verified Shopify data.

CRITICAL RULES:
  - NEVER interpolate data that hasn't been fetched from DB/Shopify
  - If product not found → raise, do not guess
  - If offer not found → skip offer (do NOT invent one)
  - All prices/stock/offers come exclusively from shopify_sync tables
"""

from __future__ import annotations

import logging
from typing import Any

from app.ai.story_engine import render_story
from app.intelligence.shopify_sync import (
    build_product_url,
    get_active_offer_for_product,
    get_product_by_id,
)
from app.storage import get_db_connection

logger = logging.getLogger(__name__)


def render_followup_message(
    message_type: str,
    decision: dict[str, Any],
    customer: dict[str, Any],
    session_id: str,
) -> str | None:
    """
    Render one follow-up message for a 24h session.

    Args:
        message_type: "story" | "offer" | "social_proof" | "urgency" | "soft_exit"
        decision: AI decision dict {tone, story_type, product_id, cta_type, urgency}
        customer: journey_customers row
        session_id: for UTM tracking

    Returns:
        Rendered message text, or None if product not found.
    """
    with get_db_connection() as conn:
        product_id = decision.get("product_id", "")
        product = get_product_by_id(conn, product_id) if product_id else None

        if not product:
            logger.warning("render_followup: product_id '%s' not found — skipping", product_id)
            return None

        product_url = build_product_url(
            product,
            customer_id=str(customer.get("id") or ""),
            campaign=f"24h_{message_type}_{session_id[:8]}",
        )

        if message_type == "story":
            return render_story(
                story_type=decision.get("story_type", "harvest_quality"),
                customer=customer,
                product=product,
                product_url=product_url,
            )

        elif message_type == "offer":
            return _render_offer_message(conn, customer, product, product_url)

        elif message_type == "social_proof":
            return _render_social_proof_message(customer, product, product_url)

        elif message_type == "urgency":
            return _render_urgency_message(conn, customer, product, product_url)

        elif message_type == "soft_exit":
            return _render_soft_exit_message(customer)

        elif message_type == "recipe_link":
            return render_story(
                story_type="recipe",
                customer=customer,
                product=product,
                product_url=product_url,
            )

        else:
            # Default: story
            return render_story(
                story_type="harvest_quality",
                customer=customer,
                product=product,
                product_url=product_url,
            )


def _render_offer_message(
    conn: Any,
    customer: dict[str, Any],
    product: dict[str, Any],
    product_url: str,
) -> str:
    """
    Render an offer message.
    ONLY includes discount if a valid offer exists in shopify_offers table.
    NEVER invents a discount.
    """
    name = (customer.get("name") or "there").split()[0]
    title = product.get("title") or "Kerala spice"

    # Fetch REAL price from product (never guess)
    price = product.get("price")
    compare_at = product.get("compare_at_price")

    # Fetch REAL offer (only if active in Shopify)
    offer = get_active_offer_for_product(conn, product.get("id"))

    # Inventory status (real)
    inv_status = product.get("inventory_status", "available")
    qty = product.get("quantity")

    # Build message with real data
    lines = [f"Hi {name},", ""]

    if compare_at and compare_at > price and price:
        lines.append(f"{title} — ₹{int(price)} (was ₹{int(compare_at)})")
    elif price:
        lines.append(f"{title} — ₹{int(price)}")
    else:
        lines.append(f"{title}")

    if offer:
        disc_type = offer.get("discount_type", "percentage")
        disc_val = offer.get("discount_value", 0)
        code = offer.get("code", "")
        if disc_type == "percentage":
            lines.append(f"Use code {code} for {int(disc_val)}% off.")
        else:
            lines.append(f"Use code {code} for ₹{int(disc_val)} off.")

    if inv_status == "critical" and qty and qty > 0:
        lines.append(f"Only {qty} packs left from this batch.")
    elif inv_status == "medium":
        lines.append("Limited stock from this harvest batch.")

    lines += ["", f"Order here:\n{product_url}"]
    return "\n".join(lines)


def _render_social_proof_message(
    customer: dict[str, Any],
    product: dict[str, Any],
    product_url: str,
) -> str:
    """Render social proof using REAL review data from shopify_products."""
    name = (customer.get("name") or "there").split()[0]
    title = product.get("title") or "this product"
    rating = product.get("rating")
    review_count = product.get("review_count")
    top_review = product.get("top_review_text")
    reviewer = product.get("top_reviewer_name")

    lines = [f"Hi {name} 👋", ""]

    if rating and review_count:
        lines.append(f"⭐ {rating}/5 from {review_count}+ customers on our {title}")
    else:
        lines.append(f"Customers love our {title}")

    if top_review and reviewer:
        lines.append(f"\"{top_review}\" — {reviewer}")
    elif top_review:
        lines.append(f"\"{top_review}\"")

    lines += ["", f"Try for yourself:\n{product_url}"]
    return "\n".join(lines)


def _render_urgency_message(
    conn: Any,
    customer: dict[str, Any],
    product: dict[str, Any],
    product_url: str,
) -> str:
    """
    Render a gentle urgency message.
    ONLY uses real inventory/offer data — never invents urgency.
    """
    name = (customer.get("name") or "there").split()[0]
    title = product.get("title") or "this product"
    inv_status = product.get("inventory_status", "available")
    qty = product.get("quantity")
    offer = get_active_offer_for_product(conn, product.get("id"))

    lines = [f"Hi {name} 👋", ""]

    if inv_status == "critical" and qty and qty > 0:
        lines.append(f"Just a note — only {qty} packs left of our {title}.")
    elif offer and offer.get("valid_until"):
        # Show offer expiry if real
        lines.append(f"The offer on {title} is available for a limited time.")
    else:
        lines.append(f"Our {title} batch is still available if you'd like to explore it.")

    lines += ["", f"Order here:\n{product_url}"]
    return "\n".join(lines)


def _render_soft_exit_message(customer: dict[str, Any]) -> str:
    """Graceful end-of-window message. No product push, pure relationship."""
    name = (customer.get("name") or "there").split()[0]
    return (
        f"Hi {name} 👋\n\n"
        "Anytime you'd like recommendations or have questions about our spices, "
        "we're here.\n\n"
        "Thank you for being part of PureLeven 🌿"
    )
