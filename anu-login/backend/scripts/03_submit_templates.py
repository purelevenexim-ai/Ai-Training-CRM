#!/usr/bin/env python3
"""
scripts/03_submit_templates.py

Submit all 25 Pureleven WhatsApp templates to Meta for approval via the
Meta Graph API (which Wabis uses under the hood for template management).

Templates take 24-72 hours to be reviewed by Meta.

Usage:
  cd anu-login/backend
  python scripts/03_submit_templates.py [--dry-run] [--filter NAME]

  --dry-run         Print templates without submitting
  --filter NAME     Only submit templates matching NAME (substring match)

Required env vars:
  META_ACCESS_TOKEN             - Permanent token from Meta Business Suite
                                  System Users → Generate Token
                                  Scopes needed: whatsapp_business_management
  WHATSAPP_BUSINESS_ACCOUNT_ID  - Meta Business Suite → WhatsApp → Account ID

How to get credentials:
  1. Go to https://business.facebook.com
  2. Settings → Business Settings → System Users
  3. Add System User (role: Admin)
  4. Click "Generate New Token" → select your WhatsApp app
  5. Enable scope: whatsapp_business_management, whatsapp_business_messaging
  6. Copy token → META_ACCESS_TOKEN
  7. Go to WhatsApp → Accounts → copy Account ID → WHATSAPP_BUSINESS_ACCOUNT_ID
"""

from __future__ import annotations

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
from typing import Any

try:
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = ssl.create_default_context()

# ─── Config ──────────────────────────────────────────────────────────────────

META_TOKEN  = os.getenv("META_ACCESS_TOKEN", "").strip()
WABA_ID     = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "").strip()
GRAPH_URL   = "https://graph.facebook.com/v20.0"
STORE_URL   = "https://pureleven.com"
REVIEW_URL  = "https://g.page/r/pureleven/review"
CALENDAR_URL = "https://calendly.com/pureleven/bulk"
TRACK_URL   = "https://www.delhivery.com/track/package"


# ─── Template definitions ────────────────────────────────────────────────────
# body_text_example: sample values for {{1}}, {{2}}, ... for Meta review
# button_url_suffix_example: sample value for dynamic URL button {{1}}

TEMPLATES: list[dict[str, Any]] = [

    # ─────────────────────────────────────────────────────────────────────────
    # DELIVERY (3)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "name": "order_confirmed_v1",
        "category": "UTILITY",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Hi {{1}}, your Pureleven order #{{2}} is confirmed! 🎉\n\n"
                    "Expected delivery: {{3}}\n\n"
                    "Track your order below 👇"
                ),
                "example": {"body_text": [["Priya", "PL-10042", "May 22-24"]]},
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Track Order",
                        "url": f"{TRACK_URL}/{{{{1}}}}",
                        "example": ["AWB123456?utm_source=whatsapp&utm_campaign=order_confirmed"],
                    },
                    {"type": "QUICK_REPLY", "text": "Ask Question"},
                ],
            },
        ],
    },
    {
        "name": "delivery_begun_v1",
        "category": "UTILITY",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Your Pureleven spices are on the way! 🚚\n\n"
                    "Hi {{1}},\n"
                    "Waybill: {{2}}\n"
                    "ETA: {{3}}\n\n"
                    "Track live 👇"
                ),
                "example": {"body_text": [["Priya", "AWB123456", "May 22"]]},
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Track Live",
                        "url": f"{TRACK_URL}/{{{{1}}}}",
                        "example": ["AWB123456"],
                    },
                    {"type": "QUICK_REPLY", "text": "Got it!"},
                ],
            },
        ],
    },
    {
        "name": "delivery_out_for_delivery_v1",
        "category": "UTILITY",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Great news {{1}}! 🚚\n\n"
                    "Your Pureleven order is out for delivery today.\n"
                    "Waybill: {{2}}\n\n"
                    "Please keep your phone handy for the delivery partner."
                ),
                "example": {"body_text": [["Priya", "AWB123456"]]},
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Track Order",
                        "url": f"{TRACK_URL}/{{{{1}}}}",
                        "example": ["AWB123456?utm_source=whatsapp&utm_campaign=out_for_delivery"],
                    },
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # REVIEW (6)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "name": "delivered_review_request_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Your Pureleven spices have arrived! 😊\n\n"
                    "Hi {{1}}, how's the aroma and quality?\n"
                    "Your 1-minute review helps other customers\n"
                    "discover authentic Kerala spices.\n\n"
                    "⭐ {{2}} - tap to share your experience!"
                ),
                "example": {
                    "body_text": [["Priya", f"{REVIEW_URL}?utm_source=whatsapp"]],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Write Review",
                        "url": f"{REVIEW_URL}?utm_source=whatsapp",
                    },
                    {"type": "QUICK_REPLY", "text": "Love it!"},
                    {"type": "QUICK_REPLY", "text": "Ask Question"},
                ],
            },
        ],
    },
    {
        "name": "delivered_vip_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Hi {{1}}, your order has arrived — thank you! 🙏\n\n"
                    "As a valued Pureleven customer, your feedback matters most to us.\n\n"
                    "Share your experience (takes 60 seconds):\n"
                    "⭐ {{2}} - your feedback means a lot!"
                ),
                "example": {
                    "body_text": [["Priya", f"{REVIEW_URL}?utm_source=whatsapp"]],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Write Review",
                        "url": f"{REVIEW_URL}?utm_source=whatsapp",
                    },
                    {"type": "QUICK_REPLY", "text": "Love it!"},
                ],
            },
        ],
    },
    {
        "name": "review_incentive_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "⭐ {{1}}, your review unlocks {{2}} off your next order!\n\n"
                    "Write a quick Google review (under 60 seconds)\n"
                    "and get shop credit instantly.\n\n"
                    "Review link: {{3}}\n"
                    "Your coupon: {{4}} - valid for 30 days!"
                ),
                "example": {
                    "body_text": [["Priya", "₹200", f"{REVIEW_URL}?utm_source=whatsapp", "REVIEW123"]],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Write and Earn",
                        "url": f"{REVIEW_URL}?utm_source=whatsapp",
                    },
                    {"type": "QUICK_REPLY", "text": "How does it work?"},
                    {"type": "QUICK_REPLY", "text": "Maybe later"},
                ],
            },
        ],
    },
    {
        "name": "review_faq_response_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Great question, {{1}}! Here's how it works:\n\n"
                    "1️⃣  Write your review on Google\n"
                    "2️⃣  Reply 'Done!' with a screenshot\n"
                    "3️⃣  ₹200 credit added to your account instantly\n\n"
                    "Ready? {{2}} - it takes 60 seconds!"
                ),
                "example": {
                    "body_text": [["Priya", f"{REVIEW_URL}?utm_source=whatsapp"]],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Write Review Now",
                        "url": f"{REVIEW_URL}?utm_source=whatsapp",
                    },
                    {"type": "QUICK_REPLY", "text": "I'll do it later"},
                    {"type": "QUICK_REPLY", "text": "Help me!"},
                ],
            },
        ],
    },
    {
        "name": "review_reminder_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "⏰ {{1}}, 3 days left to claim your reward! ⭐\n\n"
                    "Your ₹200 coupon expires soon.\n"
                    "One review = one coupon. Don't miss out!\n\n"
                    "{{2}}\n"
                    "Code: {{3}} - expires soon!"
                ),
                "example": {
                    "body_text": [["Priya", f"{REVIEW_URL}?utm_source=whatsapp", "REVIEW123"]],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Get My Reward",
                        "url": f"{REVIEW_URL}?utm_source=whatsapp",
                    },
                    {"type": "QUICK_REPLY", "text": "Not interested"},
                ],
            },
        ],
    },
    {
        "name": "review_thank_you_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Thank you {{1}}! 🎉\n\n"
                    "Your review helps other customers discover authentic Kerala spices.\n\n"
                    "Here's your ₹200 reward coupon: {{2}}\n"
                    "Valid for 30 days on any order at pureleven.com"
                ),
                "example": {"body_text": [["Priya", "REVIEW123"]]},
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # UPSELL (3)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "name": "explore_products_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Hi {{1}}, time to explore! 🌿\n\n"
                    "You've been enjoying our spices.\n"
                    "Ready to try {{2}}?\n\n"
                    "{{3}}\n"
                    "Use code *{{4}}* for 20% off — today only!"
                ),
                "example": {
                    "body_text": [
                        ["Priya", "Green Cardamom",
                         f"{STORE_URL}/products/green-cardamom-100g?utm_source=whatsapp",
                         "EXPLORE20"],
                    ],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Explore Now",
                        "url": f"{STORE_URL}/collections/all?utm_source=whatsapp",
                    },
                    {"type": "QUICK_REPLY", "text": "Show me reviews"},
                    {"type": "QUICK_REPLY", "text": "No thanks"},
                ],
            },
        ],
    },
    {
        "name": "upsell_followup_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Still thinking about {{2}}? 🤔\n\n"
                    "{{1}}, we're holding your EXPLORE20 discount code.\n"
                    "It expires soon — don't let it go to waste!\n\n"
                    "{{3}} - use EXPLORE20 at checkout!"
                ),
                "example": {
                    "body_text": [
                        ["Priya", "Green Cardamom",
                         f"{STORE_URL}/products/green-cardamom-100g?utm_source=whatsapp"],
                    ],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Get It Now",
                        "url": f"{STORE_URL}/collections/all?utm_source=whatsapp",
                    },
                    {"type": "QUICK_REPLY", "text": "Tell me more"},
                    {"type": "QUICK_REPLY", "text": "Wait for sale"},
                ],
            },
        ],
    },
    {
        "name": "price_sensitive_sale_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Hi {{1}}, sale alert! 🎉\n\n"
                    "{{2}} is now {{3}}% off — limited time offer!\n\n"
                    "{{4}} - today only, limited stock!"
                ),
                "example": {
                    "body_text": [
                        ["Priya", "Green Cardamom", "30",
                         f"{STORE_URL}/products/green-cardamom?utm_source=whatsapp"],
                    ],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Shop Now",
                        "url": f"{STORE_URL}/collections/all?utm_source=whatsapp",
                    },
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # B2B / CORPORATE (3)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "name": "corporate_pitch_high_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Hi {{1}}, let's talk bulk! 💼\n\n"
                    "You've spent {{2}} with Pureleven — thank you!\n\n"
                    "Running a restaurant, catering business, or event?\n"
                    "We offer:\n"
                    "✓ 50% below retail on bulk orders\n"
                    "✓ Free consultation + custom pricing\n"
                    "✓ Direct-from-farm freshness\n\n"
                    "Book a free 15-min call: {{3}} - spots are limited!"
                ),
                "example": {
                    "body_text": [
                        ["Priya", "₹3,500",
                         f"{CALENDAR_URL}?utm_source=whatsapp"],
                    ],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Book 15-min Call",
                        "url": f"{CALENDAR_URL}?utm_source=whatsapp",
                    },
                    {"type": "QUICK_REPLY", "text": "Email me details"},
                    {"type": "QUICK_REPLY", "text": "Not interested"},
                ],
            },
        ],
    },
    {
        "name": "corporate_pitch_low_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Hi {{1}}, quick question! 🤔\n\n"
                    "Planning any events, catering, or cooking in bulk?\n\n"
                    "Pureleven supplies fresh spices to 500+ restaurants and weddings.\n"
                    "Custom pricing available. No pressure — let's chat!\n\n"
                    "Book here: {{2}} - no commitment needed!"
                ),
                "example": {
                    "body_text": [
                        ["Priya",
                         f"{CALENDAR_URL}?utm_source=whatsapp"],
                    ],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Tell Me More",
                        "url": f"{CALENDAR_URL}?utm_source=whatsapp",
                    },
                    {"type": "QUICK_REPLY", "text": "Not now"},
                ],
            },
        ],
    },
    {
        "name": "corporate_followup_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Hi {{1}}, following up on our bulk spice offer! 📦\n\n"
                    "We have special pricing ready for catering orders.\n"
                    "Takes just 15 minutes to get a quote.\n\n"
                    "Book a call: {{2}} - 15 minutes is all we need!"
                ),
                "example": {
                    "body_text": [["Priya", f"{CALENDAR_URL}?utm_source=whatsapp"]],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Book a Call",
                        "url": f"{CALENDAR_URL}?utm_source=whatsapp",
                    },
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # LOYALTY (3)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "name": "loyalty_checkin_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Hi {{1}}, we miss you! 🌿\n\n"
                    "It's been {{2}} days since your last Pureleven order.\n\n"
                    "Spices running low? We have fresh 2026 harvest in stock!\n\n"
                    "Welcome back — use code *{{3}}* for 20% off\n"
                    "{{4}} - start shopping today!"
                ),
                "example": {
                    "body_text": [
                        ["Priya", "45",
                         "WELCOME20",
                         f"{STORE_URL}?utm_source=whatsapp"],
                    ],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Shop Now",
                        "url": f"{STORE_URL}/collections/all?utm_source=whatsapp",
                    },
                    {"type": "QUICK_REPLY", "text": "What's new?"},
                    {"type": "QUICK_REPLY", "text": "Not yet"},
                ],
            },
        ],
    },
    {
        "name": "vip_exclusive_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Hi {{1}}, VIP tier unlocked! 👑\n\n"
                    "You're in the top 5% of Pureleven customers!\n\n"
                    "Your exclusive benefits:\n"
                    "✓ 25% lifetime discount on all orders\n"
                    "✓ Free shipping, always\n"
                    "✓ First access to limited seasonal batches\n\n"
                    "{{2}} - your VIP benefits are active now!"
                ),
                "example": {
                    "body_text": [
                        ["Priya",
                         f"{STORE_URL}/collections/all?utm_source=whatsapp"],
                    ],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Claim VIP Access",
                        "url": f"{STORE_URL}/collections/all?utm_source=whatsapp",
                    },
                    {"type": "QUICK_REPLY", "text": "Tell me more"},
                ],
            },
        ],
    },
    {
        "name": "repeat_buyer_exclusive_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Hi {{1}}, because you love Pureleven! 💚\n\n"
                    "Your loyalty deserves a special reward:\n"
                    "15% off all orders this month\n\n"
                    "No code needed — discount applied automatically.\n\n"
                    "{{2}} - discount applied at checkout!"
                ),
                "example": {
                    "body_text": [["Priya", f"{STORE_URL}?utm_source=whatsapp"]],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Shop with 15% Off",
                        "url": f"{STORE_URL}/collections/all?utm_source=whatsapp",
                    },
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # WINBACK (3)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "name": "winback_offer_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Hi {{1}}, we haven't seen you in a while! 👋\n\n"
                    "Your favourite Pureleven spices are waiting...\n\n"
                    "Special offer — ₹500 off your next order\n"
                    "Code: *{{2}}*\n\n"
                    "{{3}} - use code at checkout!"
                ),
                "example": {
                    "body_text": [
                        ["Priya",
                         "COMEBACK",
                         f"{STORE_URL}?utm_source=whatsapp"],
                    ],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Welcome Me Back",
                        "url": f"{STORE_URL}/collections/all?utm_source=whatsapp",
                    },
                    {"type": "QUICK_REPLY", "text": "Tell me what's new"},
                ],
            },
        ],
    },
    {
        "name": "extreme_winback_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Hi {{1}}, last call! 🎁\n\n"
                    "We're offering {{2}} off any order — seriously!\n\n"
                    "This is a one-time offer that expires in 7 days.\n\n"
                    "Last chance: {{3}} - act now before it expires!"
                ),
                "example": {
                    "body_text": [
                        ["Priya",
                         "₹1,000",
                         f"{STORE_URL}?utm_source=whatsapp"],
                    ],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Shop Now",
                        "url": f"{STORE_URL}/collections/all?utm_source=whatsapp",
                    },
                    {"type": "QUICK_REPLY", "text": "Why so much discount?"},
                ],
            },
        ],
    },
    {
        "name": "reactivation_survey_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Hi {{1}}, quick question 🙏\n\n"
                    "It's been a while since your last order.\n"
                    "What happened? Your honest feedback helps us improve for everyone."
                ),
                "example": {"body_text": [["Priya"]]},
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {"type": "QUICK_REPLY", "text": "Price was too high"},
                    {"type": "QUICK_REPLY", "text": "Quality issue"},
                    {"type": "QUICK_REPLY", "text": "Just busy, I'll be back"},
                ],
            },
        ],
    },

    # ─────────────────────────────────────────────────────────────────────────
    # SEASONAL (4)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "name": "promo_monsoon_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "☕ {{1}}, monsoon chai season is here!\n\n"
                    "Fresh Kerala Ginger (2026 harvest) now in stock.\n"
                    "₹399 → ₹199 for a limited time (50% off!)\n\n"
                    "{{2}} - limited time, order today!"
                ),
                "example": {
                    "body_text": [["Priya", f"{STORE_URL}/products/ginger?utm_source=whatsapp"]],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Shop Ginger",
                        "url": f"{STORE_URL}/products/ginger-100g?utm_source=whatsapp",
                    },
                    {"type": "QUICK_REPLY", "text": "Recipe ideas?"},
                ],
            },
        ],
    },
    {
        "name": "promo_diwali_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "🪔 {{1}}, Diwali Spice Hampers are here!\n\n"
                    "Gift authentic Kerala spices to loved ones this festive season.\n"
                    "Beautifully packed, farm-fresh quality.\n\n"
                    "{{2}} - order before stocks run out!"
                ),
                "example": {
                    "body_text": [["Priya", f"{STORE_URL}/collections/gift-hampers?utm_source=whatsapp"]],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Shop Gift Hampers",
                        "url": f"{STORE_URL}/collections/gift-hampers?utm_source=whatsapp",
                    },
                ],
            },
        ],
    },
    {
        "name": "promo_new_harvest_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Hi {{1}}, fresh 2026 harvest has arrived! 🌿\n\n"
                    "Our spices are packed within 24 hours of harvest\n"
                    "for maximum freshness and aroma.\n\n"
                    "Be among the first to taste: {{2}} - packed fresh from Kerala!"
                ),
                "example": {
                    "body_text": [["Priya", f"{STORE_URL}/collections/new?utm_source=whatsapp"]],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Shop Fresh",
                        "url": f"{STORE_URL}/collections/new?utm_source=whatsapp",
                    },
                ],
            },
        ],
    },
    {
        "name": "promo_bulk_sale_v1",
        "category": "MARKETING",
        "language": "en",
        "components": [
            {
                "type": "BODY",
                "text": (
                    "Hi {{1}}, bulk sale alert! 📦\n\n"
                    "Order 500g+ of any spice and save 30%!\n"
                    "Free shipping on all bulk orders.\n\n"
                    "{{2}} - free shipping on all bulk orders!"
                ),
                "example": {
                    "body_text": [["Priya", f"{STORE_URL}/collections/bulk?utm_source=whatsapp"]],
                },
            },
            {
                "type": "BUTTONS",
                "buttons": [
                    {
                        "type": "URL", "text": "Shop Bulk",
                        "url": f"{STORE_URL}/collections/bulk?utm_source=whatsapp",
                    },
                ],
            },
        ],
    },
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _post_template(body: dict) -> dict:
    url  = f"{GRAPH_URL}/{WABA_ID}/message_templates"
    data = json.dumps(body, ensure_ascii=True).encode()
    req  = urllib.request.Request(
        url, data=data,
        headers={
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {META_TOKEN}",
        },
        method="POST",
    )
    try:
            with urllib.request.urlopen(req, timeout=20, context=_SSL_CONTEXT) as resp:  # noqa: S310
                return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        return {"error": exc.code, "detail": body_text}


def _get_existing_templates() -> list[dict]:
    url = f"{GRAPH_URL}/{WABA_ID}/message_templates?limit=200"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {META_TOKEN}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15, context=_SSL_CONTEXT) as resp:  # noqa: S310
            data = json.loads(resp.read())
            return data.get("data", [])
    except urllib.error.HTTPError:
        return []


# ─── Main ─────────────────────────────────────────────────────────────────────

def main(dry_run: bool = False, name_filter: str = "") -> None:
    # Preflight — skip for dry-run
    if not dry_run:
        errors = []
        if not META_TOKEN:
            errors.append("META_ACCESS_TOKEN is not set")
        if not WABA_ID:
            errors.append("WHATSAPP_BUSINESS_ACCOUNT_ID is not set")
        if errors:
            print("❌  Missing required env vars:")
            for e in errors:
                print(f"    • {e}")
            sys.exit(1)

    to_submit = TEMPLATES
    if name_filter:
        to_submit = [t for t in TEMPLATES if name_filter.lower() in t["name"]]
        print(f"🔍  Filter: '{name_filter}' → {len(to_submit)} templates\n")

    if dry_run:
        print(f"[DRY RUN] Would submit {len(to_submit)} templates:\n")
        for t in to_submit:
            body_text = next(
                (c["text"] for c in t["components"] if c["type"] == "BODY"), ""
            )
            print(f"  • {t['name']:45s} [{t['category']}]")
            print(f"    {body_text[:80]}{'...' if len(body_text) > 80 else ''}\n")
        return

    # Get existing templates (to skip already-approved ones)
    print("── Fetching existing Meta templates ──────────────────────────────")
    existing = _get_existing_templates()
    existing_names = {t["name"]: t["status"] for t in existing}
    if existing_names:
        print(f"  Found {len(existing_names)} existing templates")
        for name, status in existing_names.items():
            if any(name == tmpl["name"] for tmpl in TEMPLATES):
                icon = "✅" if status == "APPROVED" else "⏳" if status == "PENDING" else "❌"
                print(f"    {icon}  {name:45s} [{status}]")
    else:
        print("  (none found — submitting all)")

    # Submit
    print(f"\n── Submitting {len(to_submit)} templates ─────────────────────────────────")
    results: list[tuple[str, str, str]] = []   # (name, status, detail)

    for tmpl in to_submit:
        name = tmpl["name"]
        if name in existing_names:
            status = existing_names[name]
            if status in ("APPROVED", "PENDING"):
                print(f"  ⏩  {name:45s} skip ({status})")
                results.append((name, "SKIPPED", status))
                continue

        payload = {
            "name":       name,
            "category":   tmpl["category"],
            "language":   tmpl["language"],
            "components": tmpl["components"],
        }
        resp = _post_template(payload)

        if "error" in resp:
            detail = resp.get("detail", "")[:100]
            print(f"  ❌  {name:45s} FAILED: {detail}")
            results.append((name, "FAILED", detail))
        elif resp.get("status") in ("PENDING", "APPROVED"):
            print(f"  ✅  {name:45s} {resp['status']} (id={resp.get('id','?')})")
            results.append((name, resp["status"], ""))
        else:
            print(f"  ⚠️   {name:45s} resp={resp}")
            results.append((name, "UNKNOWN", str(resp)[:80]))

        time.sleep(0.5)  # rate limit courtesy delay

    # Summary
    print("\n── Summary ───────────────────────────────────────────────────────")
    by_status: dict[str, list[str]] = {}
    for name, status, _ in results:
        by_status.setdefault(status, []).append(name)
    for status, names in sorted(by_status.items()):
        print(f"  {status:10s}: {len(names)}")

    pending = by_status.get("PENDING", [])
    if pending:
        print(f"\n  ⏳  {len(pending)} templates pending Meta review (24-72 hours)")
        print("      Check status: https://business.facebook.com → WhatsApp → Templates")

    failed = by_status.get("FAILED", [])
    if failed:
        print(f"\n  ❌  {len(failed)} templates failed. Re-run with --filter <name> to retry.")

    print("\n  📝  Next steps:")
    print("      1. Wait for APPROVED status (24-72 hours)")
    print("      2. Update template names in app/whatsapp_templates.py if Meta changes any names")
    print("      3. Run scripts/04_test_e2e.py to validate end-to-end\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Submit WhatsApp templates to Meta")
    parser.add_argument("--dry-run",  action="store_true", help="Print templates, don't submit")
    parser.add_argument("--filter",   default="", help="Only submit templates matching this name")
    args = parser.parse_args()
    main(dry_run=args.dry_run, name_filter=args.filter)
