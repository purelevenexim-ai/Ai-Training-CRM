"""
app/email_templates.py

HTML email templates for each journey stage.

Each template:
  - Is fully self-contained HTML (inline CSS for Gmail compatibility)
  - Uses customer name personalisation
  - Includes UTM-tracked links
  - Has an unsubscribe footer
  - Returns (subject, html_body, text_body)
"""

from __future__ import annotations

import html as html_lib
import logging
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)


# ─── Brand constants ──────────────────────────────────────────────────────────

BRAND_COLOR  = "#2E7D32"      # PureLeven forest green
ACCENT_COLOR = "#81C784"      # light green
BG_COLOR     = "#F9FBF9"
TEXT_COLOR   = "#1A1A1A"
MUTED_COLOR  = "#6B7280"
LOGO_URL     = "https://cdn.shopify.com/s/files/1/0948/2151/9226/files/pureleven-logo.png"
STORE_URL    = "https://pureleven.com"


# ─── Shared HTML helpers ──────────────────────────────────────────────────────

def _e(value: Any) -> str:
    """HTML-escape a value for safe template insertion."""
    return html_lib.escape(str(value or ""))


def _unsubscribe_url(customer_id: Any, token: Any) -> str:
    base = settings.public_base_url.rstrip("/")
    return f"{base}/api/email/unsubscribe?customer_id={_e(customer_id)}&token={_e(token)}"


def _utm(url: str, campaign: str, medium: str = "email", source: str = "pureleven") -> str:
    return f"{url}?utm_source={source}&utm_medium={medium}&utm_campaign={campaign}"


def _wrap_layout(customer: dict[str, Any], title: str, inner_html: str) -> str:
    """Wrap inner HTML in a full branded layout with header/footer."""
    unsub_url = _unsubscribe_url(customer.get("id", ""), customer.get("unsubscribe_token", ""))
    store_link = _utm(STORE_URL, title.lower().replace(" ", "_"))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_e(title)}</title>
</head>
<body style="margin:0;padding:0;background:{BG_COLOR};font-family:Arial,Helvetica,sans-serif;color:{TEXT_COLOR};">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{BG_COLOR};padding:24px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.07);">

        <!-- Header -->
        <tr>
          <td style="background:{BRAND_COLOR};padding:24px 32px;text-align:center;">
            <a href="{store_link}" style="text-decoration:none;">
              <img src="{LOGO_URL}" alt="PureLeven" height="40" style="display:block;margin:0 auto;" onerror="this.style.display='none'">
              <span style="color:#ffffff;font-size:22px;font-weight:bold;letter-spacing:1px;display:block;margin-top:6px;">PureLeven</span>
            </a>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:32px;">
            {inner_html}
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#F3F4F6;padding:20px 32px;text-align:center;border-top:1px solid #E5E7EB;">
            <p style="margin:0 0 8px;font-size:13px;color:{MUTED_COLOR};">
              PureLeven — Premium Organic Spices &amp; Superfoods<br>
              <a href="{store_link}" style="color:{BRAND_COLOR};text-decoration:none;">Shop Now</a>
            </p>
            <p style="margin:0;font-size:12px;color:#9CA3AF;">
              You received this email because you placed an order with PureLeven.
              <br>
              <a href="{unsub_url}" style="color:#9CA3AF;text-decoration:underline;">Unsubscribe</a>
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _btn(label: str, url: str, color: str = BRAND_COLOR) -> str:
    return (
        f'<a href="{url}" style="display:inline-block;background:{color};color:#ffffff;'
        f'padding:14px 28px;border-radius:8px;text-decoration:none;font-size:16px;'
        f'font-weight:bold;margin-top:16px;">{_e(label)}</a>'
    )


def _product_card(product: dict[str, Any], campaign: str) -> str:
    name = _e(product.get("title", ""))
    price = product.get("price", "")
    url = _utm(product.get("url", STORE_URL), campaign)
    img = product.get("image_url", "")
    img_html = f'<img src="{img}" alt="{name}" width="120" style="border-radius:8px;display:block;" onerror="this.style.display=\'none\'">' if img else ""
    return f"""
<table cellpadding="0" cellspacing="0" style="margin:12px 0;background:{BG_COLOR};border-radius:8px;overflow:hidden;width:100%;">
  <tr>
    <td style="padding:12px;width:136px;vertical-align:top;">{img_html}</td>
    <td style="padding:12px;vertical-align:top;">
      <p style="margin:0 0 4px;font-weight:bold;font-size:15px;">{name}</p>
      <p style="margin:0 0 8px;color:{MUTED_COLOR};font-size:13px;">₹{_e(price)}</p>
      <a href="{url}" style="font-size:13px;color:{BRAND_COLOR};font-weight:bold;text-decoration:none;">View Product →</a>
    </td>
  </tr>
</table>"""


# ─── Stage templates ──────────────────────────────────────────────────────────

def _order_confirmed_template(customer: dict[str, Any], vars: dict[str, Any]) -> tuple[str, str, str]:
    name = _e(customer.get("customer_name", "there"))
    order_id = _e(customer.get("order_id") or vars.get("order_id", ""))
    shop_link = _utm(STORE_URL, "order_confirmed")

    subject = f"Your PureLeven order is confirmed! 🌿"
    inner = f"""
<h2 style="margin:0 0 16px;font-size:24px;color:{BRAND_COLOR};">Hi {name}, your order is confirmed! ✅</h2>
<p style="font-size:16px;line-height:1.6;margin:0 0 16px;">
  Thank you for choosing PureLeven! We've received your order
  {f'<strong>#{order_id}</strong>' if order_id else ''} and our team is getting it ready for you.
</p>
<div style="background:#E8F5E9;border-left:4px solid {BRAND_COLOR};padding:16px;border-radius:0 8px 8px 0;margin:0 0 24px;">
  <p style="margin:0;font-size:15px;color:{BRAND_COLOR};font-weight:bold;">What happens next?</p>
  <ul style="margin:8px 0 0;padding-left:20px;font-size:14px;line-height:1.8;">
    <li>We'll pack your order with care</li>
    <li>Dispatch within 1–2 business days</li>
    <li>You'll get a tracking update via WhatsApp &amp; email</li>
  </ul>
</div>
<p style="font-size:15px;margin:0 0 24px;">
  While you wait, explore our full range of organic spices and superfoods. 🌱
</p>
{_btn("Explore Our Products", shop_link)}
<p style="font-size:14px;color:{MUTED_COLOR};margin:24px 0 0;">
  Questions? Reply to this email or message us on WhatsApp. We're always here!
</p>"""

    text = f"Hi {customer.get('customer_name', 'there')}, your PureLeven order is confirmed! We'll send tracking updates soon. Visit {STORE_URL} to explore more."
    return subject, _wrap_layout(customer, "Order Confirmed", inner), text


def _in_transit_template(customer: dict[str, Any], vars: dict[str, Any]) -> tuple[str, str, str]:
    name = _e(customer.get("customer_name", "there"))
    tracking_id = _e(customer.get("tracking_id") or vars.get("tracking_id", ""))
    carrier = _e(customer.get("carrier") or "Delhivery")
    shop_link = _utm(STORE_URL, "in_transit")

    subject = f"Your PureLeven order is on its way! 🚚"
    inner = f"""
<h2 style="margin:0 0 16px;font-size:24px;color:{BRAND_COLOR};">Your order is on its way! 🚚</h2>
<p style="font-size:16px;line-height:1.6;margin:0 0 16px;">
  Hi {name}! Great news — your PureLeven order has been dispatched and is heading your way.
</p>
{f'''<div style="background:#E3F2FD;border-radius:8px;padding:16px;margin:0 0 24px;text-align:center;">
  <p style="margin:0 0 4px;font-size:13px;color:{MUTED_COLOR};">Tracking ID</p>
  <p style="margin:0;font-size:20px;font-weight:bold;letter-spacing:2px;">{tracking_id}</p>
  <p style="margin:4px 0 0;font-size:13px;color:{MUTED_COLOR};">via {carrier}</p>
</div>''' if tracking_id else ''}
<p style="font-size:15px;line-height:1.6;margin:0 0 24px;">
  You can expect delivery within <strong>2–4 business days</strong>. We'll keep you updated on WhatsApp too!
</p>
{_btn("Shop More", shop_link)}
<p style="font-size:14px;color:{MUTED_COLOR};margin:24px 0 0;">
  Can't wait to hear what you think of your order! 🌿
</p>"""

    text = f"Hi {customer.get('customer_name', 'there')}, your PureLeven order is on its way! Tracking: {tracking_id}. Visit {STORE_URL} for more."
    return subject, _wrap_layout(customer, "Order Dispatched", inner), text


def _delivered_template(customer: dict[str, Any], vars: dict[str, Any]) -> tuple[str, str, str]:
    name = _e(customer.get("customer_name", "there"))
    shop_link = _utm(STORE_URL, "delivered")

    subject = f"Your PureLeven order was delivered! 🌿"
    inner = f"""
<h2 style="margin:0 0 16px;font-size:24px;color:{BRAND_COLOR};">Hi {name}, your order has been delivered! ✅</h2>
<p style="font-size:16px;line-height:1.6;margin:0 0 16px;">
  Your PureLeven order should now be with you. We hope it reached you safely and that your kitchen already smells a little better.
</p>
<div style="background:#ECFDF5;border-left:4px solid {BRAND_COLOR};padding:16px;border-radius:0 8px 8px 0;margin:0 0 24px;">
  <p style="margin:0;font-size:15px;color:{BRAND_COLOR};font-weight:bold;">What happens next?</p>
  <ul style="margin:8px 0 0;padding-left:20px;font-size:14px;line-height:1.8;">
    <li>Try your products for a few days</li>
    <li>We will check back soon for your feedback</li>
    <li>You will continue receiving useful updates on WhatsApp and email</li>
  </ul>
</div>
<p style="font-size:15px;margin:0 0 24px;">
  Need more ideas while you wait to cook? Browse our pantry for pairings, refills, and new arrivals.
</p>
{_btn("Browse the Pantry", shop_link)}
<p style="font-size:14px;color:{MUTED_COLOR};margin:24px 0 0;">
  If anything about the delivery was not right, just reply to this email and our team will help.
</p>"""

    text = f"Hi {customer.get('customer_name', 'there')}, your PureLeven order was delivered. We're here if you need anything, and we'll follow up soon for feedback. Visit {STORE_URL} for more."
    return subject, _wrap_layout(customer, "Order Delivered", inner), text


def _day15_template(customer: dict[str, Any], vars: dict[str, Any]) -> tuple[str, str, str]:
    name = _e(customer.get("customer_name", "there"))
    review_link = _utm("https://g.page/r/pureleven/review", "day15_review_request", source="email_journey")
    shop_link = _utm(STORE_URL, "day15_review")

    # ── AI-optimised review incentive ────────────────────────────────────
    incentive_html = ""
    try:
        from app.services.review_incentive_optimizer import ReviewIncentiveOptimizer
        customer_id = str(customer.get("id") or customer.get("customer_id") or "anon")
        incentive = ReviewIncentiveOptimizer.get_incentive(
            customer_id=customer_id,
            customer_segment=str(customer.get("customer_segment", "new")),
            engagement_score=float(customer.get("engagement_score") or 0),
            purchase_count=int(customer.get("purchase_count") or 1),
            review_status=str(customer.get("google_review_status") or "not_submitted"),
        )
        incentive_html = ReviewIncentiveOptimizer.format_for_email(incentive)
        # Store the coupon code for use in follow-up
        vars["review_coupon_code"] = incentive.get("coupon_code", "REVIEW100")
    except Exception as exc:
        logger.warning("Review incentive optimization failed: %s", exc)
        incentive_html = ""
        vars.setdefault("review_coupon_code", "REVIEW100")

    subject = f"How's your PureLeven experience? We'd love your review! ⭐"
    inner = f"""
<h2 style="margin:0 0 16px;font-size:24px;color:{BRAND_COLOR};">Hi {name}, how's your experience? ⭐</h2>
<p style="font-size:16px;line-height:1.6;margin:0 0 16px;">
  We hope you're loving your PureLeven products! Your feedback means the world to us and helps other 
  health-conscious families discover organic goodness.
</p>
<div style="text-align:center;padding:24px;background:#FFFDE7;border-radius:12px;margin:0 0 24px;">
  <p style="font-size:36px;margin:0 0 8px;">⭐⭐⭐⭐⭐</p>
  <p style="font-size:16px;font-weight:bold;margin:0 0 16px;color:{TEXT_COLOR};">Leave us a Google Review</p>
  <p style="font-size:14px;color:{MUTED_COLOR};margin:0 0 16px;">Takes less than 2 minutes — and it helps us grow as a small organic brand!</p>
  {_btn("Write a Review", review_link)}
</div>
{incentive_html}
<p style="font-size:14px;color:{MUTED_COLOR};margin:0 0 8px;">
  💚 <strong>Bonus:</strong> Share a photo of your products and tag <strong>@pureleven</strong> for a chance to be featured!
</p>"""

    text = f"Hi {customer.get('customer_name', 'there')}, we'd love your Google review! Visit {review_link} to share your experience."
    return subject, _wrap_layout(customer, "Share Your Review", inner), text


def _day30_template(customer: dict[str, Any], vars: dict[str, Any]) -> tuple[str, str, str]:
    name = _e(customer.get("customer_name", "there"))
    shop_link = _utm(STORE_URL, "day30_upsell")

    # ── AI-driven product recommendations ──────────────────────────────────
    product_cards_html = ""
    try:
        from app.services.product_recommendation_engine import ProductRecommendationEngine
        customer_id = str(customer.get("id") or customer.get("customer_id") or "anon")
        purchased = str(customer.get("last_product_purchased") or vars.get("last_product", "spices"))
        recs = ProductRecommendationEngine.get_recommendations(
            customer_id=customer_id,
            purchased_product=purchased,
            customer_segment=str(customer.get("customer_segment", "new")),
            purchase_count=int(customer.get("purchase_count") or 1),
            utm_campaign="day30_upsell",
        )
        product_cards_html = ProductRecommendationEngine.format_for_email(recs)
    except Exception as exc:
        logger.warning("Product recommendation failed in day30 email: %s", exc)

    # Fallback to static product cards from vars
    if not product_cards_html:
        products = vars.get("recommended_products", [])
        product_cards_html = "".join(_product_card(p, "day30_upsell") for p in products[:3]) if products else ""

    if not product_cards_html:
        product_cards_html = f'<p style="font-size:15px;"><a href="{shop_link}" style="color:{BRAND_COLOR};font-weight:bold;">Browse our full collection →</a></p>'

    subject = f"Complete your PureLeven pantry, {customer.get('customer_name', '')} 🌿"
    inner = f"""
<h2 style="margin:0 0 16px;font-size:24px;color:{BRAND_COLOR};">Hi {name}, time to restock? 🌱</h2>
<p style="font-size:16px;line-height:1.6;margin:0 0 16px;">
  It's been about a month since your last order — we hope you've been enjoying your products!
  Here are some hand-picked recommendations just for you:
</p>
{product_cards_html}
<p style="font-size:15px;line-height:1.6;margin:16px 0 24px;">
  Use code <strong style="background:#E8F5E9;padding:2px 8px;border-radius:4px;color:{BRAND_COLOR};">PURE10</strong> 
  for 10% off your next order. Valid for the next 7 days!
</p>
{_btn("Shop Now", shop_link)}"""

    text = f"Hi {customer.get('customer_name', 'there')}, time to restock your PureLeven pantry! Use code PURE10 for 10% off. Visit {STORE_URL}."
    return subject, _wrap_layout(customer, "Recommended For You", inner), text


def _day60_template(customer: dict[str, Any], vars: dict[str, Any]) -> tuple[str, str, str]:
    name = _e(customer.get("customer_name", "there"))
    bulk_link = _utm(f"{STORE_URL}/pages/bulk-orders", "day60_corporate")

    subject = f"Corporate organic gifting? We've got you covered 🎁"
    inner = f"""
<h2 style="margin:0 0 16px;font-size:24px;color:{BRAND_COLOR};">Hi {name}, know a business that loves organic? 🏢</h2>
<p style="font-size:16px;line-height:1.6;margin:0 0 24px;">
  PureLeven offers <strong>bulk orders and corporate gifting packages</strong> — perfect for 
  Diwali gifts, employee wellness kits, or health-conscious client hampers.
</p>
<div style="background:#E8F5E9;border-radius:12px;padding:24px;margin:0 0 24px;">
  <p style="margin:0 0 12px;font-weight:bold;font-size:16px;color:{BRAND_COLOR};">Corporate Benefits</p>
  <ul style="margin:0;padding-left:20px;font-size:15px;line-height:2;">
    <li>Custom branding &amp; packaging</li>
    <li>Volume discounts (15–30% off)</li>
    <li>Pan-India delivery</li>
    <li>Dedicated account manager</li>
    <li>GST invoice provided</li>
  </ul>
</div>
{_btn("Enquire About Bulk Orders", bulk_link)}
<p style="font-size:14px;color:{MUTED_COLOR};margin:24px 0 0;">
  For immediate queries, reply to this email or WhatsApp us directly.
</p>"""

    text = f"Hi {customer.get('customer_name', 'there')}, PureLeven offers bulk and corporate gifting. Visit {bulk_link} or reply to this email."
    return subject, _wrap_layout(customer, "Corporate & Bulk Orders", inner), text


def _day75_template(customer: dict[str, Any], vars: dict[str, Any]) -> tuple[str, str, str]:
    name = _e(customer.get("customer_name", "there"))
    shop_link = _utm(STORE_URL, "day75_loyalty")
    segment = customer.get("customer_segment", "")

    subject = f"You're a PureLeven VIP — here's something special 💚"
    offer_block = ""
    if segment == "vip":
        offer_block = f"""
<div style="background:linear-gradient(135deg,{BRAND_COLOR},{ACCENT_COLOR});border-radius:12px;padding:24px;margin:0 0 24px;text-align:center;color:#fff;">
  <p style="margin:0 0 4px;font-size:13px;opacity:0.9;">EXCLUSIVE VIP OFFER</p>
  <p style="margin:0 0 8px;font-size:28px;font-weight:bold;">15% OFF</p>
  <p style="margin:0 0 12px;font-size:14px;opacity:0.9;">Your entire next order</p>
  <p style="margin:0;font-size:18px;font-weight:bold;background:rgba(255,255,255,0.2);display:inline-block;padding:6px 16px;border-radius:6px;">VIP15</p>
</div>"""
    else:
        offer_block = f"""
<div style="background:#E8F5E9;border-radius:12px;padding:24px;margin:0 0 24px;text-align:center;">
  <p style="margin:0 0 8px;font-size:22px;font-weight:bold;color:{BRAND_COLOR};">10% OFF</p>
  <p style="margin:0 0 12px;font-size:14px;color:{MUTED_COLOR};">Use code <strong>LOYAL10</strong> on your next order</p>
</div>"""

    inner = f"""
<h2 style="margin:0 0 16px;font-size:24px;color:{BRAND_COLOR};">Hi {name}, you're one of our favourites! 💚</h2>
<p style="font-size:16px;line-height:1.6;margin:0 0 24px;">
  As one of our most valued customers, we want to show our appreciation with an exclusive offer — 
  just for you!
</p>
{offer_block}
<p style="font-size:15px;line-height:1.6;margin:0 0 24px;">
  Thank you for being part of the PureLeven family. Your trust means everything to us. 🙏
</p>
{_btn("Redeem Now", shop_link)}"""

    text = f"Hi {customer.get('customer_name', 'there')}, you're a valued PureLeven customer! Here's an exclusive loyalty offer. Visit {STORE_URL}."
    return subject, _wrap_layout(customer, "Loyalty Reward", inner), text


def _day95_template(customer: dict[str, Any], vars: dict[str, Any]) -> tuple[str, str, str]:
    name = _e(customer.get("customer_name", "there"))
    shop_link = _utm(STORE_URL, "day95_winback")

    subject = f"We miss you, {customer.get('customer_name', '')}! Come back with 15% off 🌿"
    inner = f"""
<h2 style="margin:0 0 16px;font-size:24px;color:{BRAND_COLOR};">Hi {name}, it's been a while! 👋</h2>
<p style="font-size:16px;line-height:1.6;margin:0 0 24px;">
  We noticed it's been some time since your last order, and we genuinely miss you! 
  We have exciting new products and offers we think you'll love.
</p>
<div style="background:#FFF3E0;border:2px dashed #FF8F00;border-radius:12px;padding:24px;margin:0 0 24px;text-align:center;">
  <p style="margin:0 0 8px;font-size:13px;color:#E65100;font-weight:bold;">WELCOME BACK OFFER</p>
  <p style="margin:0 0 4px;font-size:32px;font-weight:bold;color:#E65100;">15% OFF</p>
  <p style="margin:0 0 12px;font-size:14px;color:{MUTED_COLOR};">On your next order — expires in 7 days</p>
  <p style="margin:0;font-size:20px;font-weight:bold;background:#fff;display:inline-block;padding:8px 20px;border-radius:8px;border:1px solid #FF8F00;color:#E65100;">COMEBACK15</p>
</div>
<p style="font-size:15px;line-height:1.6;margin:0 0 24px;">
  We've added new Kerala spices, Himalayan superfoods, and special festive bundles since you last visited. 🌶️
</p>
{_btn("Shop & Claim Offer", shop_link)}
<p style="font-size:14px;color:{MUTED_COLOR};margin:24px 0 0;">
  Offer valid for 7 days. Cannot be combined with other offers.
</p>"""

    text = f"Hi {customer.get('customer_name', 'there')}, we miss you! Use code COMEBACK15 for 15% off your next PureLeven order. Visit {STORE_URL}."
    return subject, _wrap_layout(customer, "We Miss You", inner), text


# ─── Review Journey email templates ──────────────────────────────────────────

GOOGLE_REVIEW_URL = "https://g.page/r/CUrWIcPGInbFEBE/review"


def _review_pure_day15_email(customer: dict[str, Any], vars: dict[str, Any]) -> tuple[str, str, str]:
    """Day 15: Pure appreciation + review CTA (no discount, no pressure)."""
    name = _e(customer.get("customer_name") or customer.get("name", "there"))
    product = _e(customer.get("purchased_product_name", "your PureLeven spices"))
    review_link = _utm(GOOGLE_REVIEW_URL, "review_pure_day15")
    store_link  = _utm(STORE_URL, "review_pure_day15")
    subject = f"How is your {product} treating you? 🌿"

    inner = f"""
<tr><td style="padding:36px 32px;">
  <h2 style="margin:0 0 16px;font-size:24px;color:{BRAND_COLOR};font-weight:700;">
    Hi {name} 👋
  </h2>
  <p style="font-size:16px;line-height:1.7;margin:0 0 20px;">
    It's been about 2 weeks since your <strong>{product}</strong> arrived, and we hope you're loving every sprinkle! 🌿
  </p>
  <p style="font-size:15px;line-height:1.7;color:{MUTED_COLOR};margin:0 0 24px;">
    We're a small Kerala-based family business, and every review genuinely helps us grow and reach more spice lovers like you.
    If you have 60 seconds, we'd be incredibly grateful for your honest thoughts.
  </p>
  {_btn("Leave a Google Review ⭐", review_link, BRAND_COLOR)}
  <p style="font-size:13px;color:{MUTED_COLOR};margin:24px 0 0;text-align:center;">
    No account needed. It takes less than 60 seconds.
  </p>
  <hr style="border:none;border-top:1px solid #e5e7eb;margin:28px 0;">
  <p style="font-size:14px;text-align:center;color:{MUTED_COLOR};">
    <a href="{store_link}" style="color:{BRAND_COLOR};">Browse our full collection</a> &nbsp;|&nbsp;
    Crafted with love from Kerala ❤️
  </p>
</td></tr>"""

    text = f"Hi {name}, how's your {product} treating you? We'd love an honest review — it takes under 60 seconds. {review_link}"
    return subject, _wrap_layout(customer, subject, inner), text


def _review_thanks_day18_email(customer: dict[str, Any], vars: dict[str, Any]) -> tuple[str, str, str]:
    """Day 18 (reviewed): Thank-you + cross-sell recommendation."""
    name = _e(customer.get("customer_name") or customer.get("name", "there"))
    product = _e(customer.get("purchased_product_name", "your purchase"))
    rec_name = _e(vars.get("rec_name", "Kerala Black Pepper"))
    rec_url  = vars.get("rec_url", _utm(f"{STORE_URL}/products/kerala-black-pepper-200gm", "review_thanks_day18"))
    store_link = _utm(STORE_URL, "review_thanks_day18")
    subject = f"Thank you for your review, {name}! 🙏"

    inner = f"""
<tr><td style="padding:36px 32px;">
  <h2 style="margin:0 0 16px;font-size:24px;color:{BRAND_COLOR};font-weight:700;">
    {name}, you made our day! 🙏
  </h2>
  <p style="font-size:16px;line-height:1.7;margin:0 0 20px;">
    Thank you so much for sharing your experience with <strong>{product}</strong>.
    Reviews like yours help our small Kerala farm-to-table business reach more spice lovers — and they mean the world to our farmers.
  </p>
  <div style="background:#f0fdf4;border-left:4px solid {BRAND_COLOR};padding:16px 20px;border-radius:4px;margin:0 0 24px;">
    <p style="margin:0;font-size:15px;color:{BRAND_COLOR};font-weight:600;">You might also love…</p>
    <p style="margin:8px 0 0;font-size:15px;">{_e(rec_name)} — a perfect companion to your current spices.</p>
  </div>
  {_btn(f"Explore {_e(rec_name)}", rec_url)}
  <p style="font-size:14px;text-align:center;color:{MUTED_COLOR};margin-top:20px;">
    <a href="{store_link}" style="color:{BRAND_COLOR};">Shop full collection</a>
  </p>
</td></tr>"""

    text = f"Thank you for your review, {name}! You might also love our {rec_name}. {rec_url}"
    return subject, _wrap_layout(customer, subject, inner), text


def _crosssell_day18_email(customer: dict[str, Any], vars: dict[str, Any]) -> tuple[str, str, str]:
    """Day 18 (did NOT review): Gentle cross-sell, no mention of review."""
    name = _e(customer.get("customer_name") or customer.get("name", "there"))
    product = _e(customer.get("purchased_product_name", "your PureLeven spices"))
    rec_name = _e(vars.get("rec_name", "Kerala Black Pepper"))
    rec_url  = vars.get("rec_url", _utm(f"{STORE_URL}/products/kerala-black-pepper-200gm", "crosssell_day18"))
    store_link = _utm(STORE_URL, "crosssell_day18")
    subject = f"Customers who love {product} also enjoy this…"

    inner = f"""
<tr><td style="padding:36px 32px;">
  <h2 style="margin:0 0 16px;font-size:24px;color:{BRAND_COLOR};font-weight:700;">
    Hi {name}, a spice pairing idea for you 🌿
  </h2>
  <p style="font-size:16px;line-height:1.7;margin:0 0 20px;">
    Customers who purchased <strong>{product}</strong> often love pairing it with…
  </p>
  <div style="background:#f9fafb;border-radius:8px;padding:20px;margin:0 0 24px;border:1px solid #e5e7eb;">
    <p style="margin:0;font-size:18px;font-weight:700;color:{BRAND_COLOR};">{_e(rec_name)}</p>
    <p style="margin:8px 0 0;font-size:14px;color:{MUTED_COLOR};">
      Freshly sourced from the Cardamom Hills, Kerala. Farm-fresh, no preservatives.
    </p>
  </div>
  {_btn(f"Shop {_e(rec_name)}", rec_url)}
  <p style="font-size:14px;text-align:center;color:{MUTED_COLOR};margin-top:20px;">
    <a href="{store_link}" style="color:{BRAND_COLOR};">See all spices →</a>
  </p>
</td></tr>"""

    text = f"Hi {name}, customers who love {product} often pair it with our {rec_name}. {rec_url}"
    return subject, _wrap_layout(customer, subject, inner), text


def _replenishment_day45_email(customer: dict[str, Any], vars: dict[str, Any]) -> tuple[str, str, str]:
    """Day 45: Replenishment reminder."""
    name = _e(customer.get("customer_name") or customer.get("name", "there"))
    product = _e(customer.get("purchased_product_name", "your Pureleven spices"))
    store_link = _utm(f"{STORE_URL}/collections/all", "replenishment_day45")
    subject = f"Running low on {product}? 🌿 Time to restock!"

    inner = f"""
<tr><td style="padding:36px 32px;">
  <h2 style="margin:0 0 16px;font-size:24px;color:{BRAND_COLOR};font-weight:700;">
    Hi {name}, your spices might be running low 🌿
  </h2>
  <p style="font-size:16px;line-height:1.7;margin:0 0 20px;">
    It's been about 6 weeks since your <strong>{product}</strong> arrived.
    If you cook regularly, you're probably running low!
  </p>
  <p style="font-size:15px;color:{MUTED_COLOR};line-height:1.7;margin:0 0 24px;">
    Our spices are harvested fresh each season from small farms in Kerala.
    Reorder now to ensure you get the freshest batch — stocks are limited.
  </p>
  <div style="background:#fff8e1;border-radius:8px;padding:16px 20px;margin:0 0 24px;border:1px solid #fde68a;">
    <p style="margin:0;font-size:15px;font-weight:600;">🎁 Loyalty reward: Use code <strong>LOYAL10</strong> for 10% off</p>
    <p style="margin:6px 0 0;font-size:13px;color:{MUTED_COLOR};">Valid for 48 hours only</p>
  </div>
  {_btn("Restock My Spices", store_link, "#f59e0b")}
</td></tr>"""

    text = f"Hi {name}, it's been 6 weeks since your {product} arrived — time to restock! Use LOYAL10 for 10% off. {store_link}"
    return subject, _wrap_layout(customer, subject, inner), text


def _vip_day75_email(customer: dict[str, Any], vars: dict[str, Any]) -> tuple[str, str, str]:
    """Day 75: VIP exclusive offer."""
    name = _e(customer.get("customer_name") or customer.get("name", "there"))
    vip_link = _utm(f"{STORE_URL}/collections/all", "vip_day75")
    subject = f"{name}, you're a PureLeven VIP ⭐ Exclusive Access Inside"

    inner = f"""
<tr><td style="padding:36px 32px;">
  <div style="background:linear-gradient(135deg,{BRAND_COLOR} 0%,#1b5e20 100%);border-radius:12px;padding:28px 24px;text-align:center;margin:0 0 28px;">
    <p style="color:#fff;font-size:28px;margin:0;">⭐</p>
    <h2 style="color:#fff;font-size:22px;margin:8px 0 6px;font-weight:700;">You're a VIP, {name}!</h2>
    <p style="color:#a5d6a7;font-size:14px;margin:0;">Exclusive 72-hour early access to our new Kerala collection</p>
  </div>
  <p style="font-size:16px;line-height:1.7;margin:0 0 20px;">
    As one of our most valued customers, you get <strong>first access</strong> to our new harvest — before it goes live to the public.
  </p>
  <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:18px 20px;margin:0 0 24px;">
    <p style="margin:0 0 8px;font-size:15px;font-weight:700;color:{BRAND_COLOR};">Your VIP benefits:</p>
    <ul style="margin:0;padding-left:20px;font-size:15px;line-height:1.8;color:{TEXT_COLOR};">
      <li>🎁 20% off your entire order</li>
      <li>📦 Free premium spice packaging</li>
      <li>🔒 72-hour exclusive access (then public)</li>
    </ul>
  </div>
  {_btn("Shop VIP Collection ⭐", vip_link, BRAND_COLOR)}
  <p style="font-size:13px;color:{MUTED_COLOR};margin-top:20px;text-align:center;">
    This is a limited 72-hour window. Access expires automatically.
  </p>
</td></tr>"""

    text = f"Congratulations {name}, you're a PureLeven VIP! Get 20% off + free packaging on our new Kerala collection. {vip_link}"
    return subject, _wrap_layout(customer, subject, inner), text


# ─── Stage router ─────────────────────────────────────────────────────────────

_STAGE_HANDLERS = {
  "order_confirmed": _order_confirmed_template,
  "day1": _order_confirmed_template,
  "in_transit": _in_transit_template,
  "day2": _in_transit_template,
  "delivered": _delivered_template,
  "day5": _delivered_template,
  "review": _day15_template,
  "day15": _day15_template,
  "upsell": _day30_template,
  "day30": _day30_template,
  "corporate": _day60_template,
  "day60": _day60_template,
  "loyalty": _day75_template,
  "day75": _day75_template,
  "rfm": _day95_template,
  "day95": _day95_template,
    # Review journey stages
    "review_pure_day15":   _review_pure_day15_email,
    "review_thanks_day18": _review_thanks_day18_email,
    "crosssell_day18":     _crosssell_day18_email,
    "replenishment_day45": _replenishment_day45_email,
    "vip_day75":           _vip_day75_email,
}


def build_email_for_stage(
    stage: str,
    customer: dict[str, Any],
    vars: dict[str, Any],
) -> tuple[str, str, str]:
    """
    Build (subject, html_body, text_body) for a given journey stage.

    Args:
      stage:    Journey stage key (`order_confirmed`, `in_transit`, `delivered`,
            `review`, `upsell`, `corporate`, `loyalty`, `rfm`) or the
            legacy internal aliases (`day1`, `day2`, `day5`, `day15`, etc.)
        customer: Customer row dict from journey_customers
        vars:     Extra template variables (product_recs, tracking_id, etc.)
                  Pass vars["use_ai_subject"] = True to enable AI subject generation.

    Returns:
        Tuple of (subject, html_body, text_body)

    Raises:
        ValueError if stage is unrecognised
    """
    handler = _STAGE_HANDLERS.get(stage)
    if not handler:
        raise ValueError(f"No email template for stage: {stage!r}")

    subject, html_body, text_body = handler(customer, vars)

    # ── AI subject line enhancement (non-blocking) ────────────────────────────
    if vars.get("use_ai_subject", True):
        try:
            from app.services.ai_enhancement_service import AIEnhancementService
            customer_id = str(customer.get("id") or customer.get("customer_id") or "anon")
            segment = str(customer.get("customer_segment", "new"))
            psychograph = ""
            psych_json = customer.get("psychograph_ai_json")
            if psych_json:
                import json as _json
                try:
                    psych_json = _json.loads(psych_json)
                    psychograph = psych_json.get("psychograph", "")
                except Exception:
                    pass

            # Derive product name from stage
            _stage_products = {
              "order_confirmed": "your order",
              "day1": "your order",
              "in_transit": "your delivery",
              "day2": "your delivery",
              "delivered": "your delivery",
              "day5": "your delivery",
              "review": "your experience",
              "day15": "your experience",
              "upsell": "organic pantry",
              "day30": "organic pantry",
              "corporate": "corporate gifting",
              "day60": "corporate gifting",
              "loyalty": "VIP rewards",
              "day75": "VIP rewards",
              "rfm": "a special offer",
              "day95": "a special offer",
            }
            product_name = _stage_products.get(stage, "organic spices")

            ai_result = AIEnhancementService.generate_email_subjects(
                customer_id=customer_id,
                stage=stage,
                customer_segment=segment,
                product_name=product_name,
                psychology_type=psychograph or "explorer",
            )
            ai_subject = ai_result.get("best", "").strip()
            if ai_subject:
                subject = ai_subject
                logger.debug("AI subject for %s/%s: %s (source=%s)", customer_id, stage, subject, ai_result.get("source"))
        except Exception as exc:
            logger.warning("AI subject generation skipped (%s) — using template subject", exc)

    return subject, html_body, text_body
