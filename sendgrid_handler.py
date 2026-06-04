"""
sendgrid_handler.py — Pureleven Hybrid Email Sender (Phase 5)
Sends transactional and lifecycle emails via SendGrid and/or self-hosted Plunk.

ROUTING STRATEGY:
  Preferred SendGrid templates:
    - order_confirmation (D0)
    - review_request_d3 (D3 — first touch, high-value conversion)
    - order_fulfilled
    - order_cancelled
    - _raw_html

  Preferred Plunk templates:
    - repeat_offer_d7 (D7, lower priority)
    - replenishment_d30 (D30, re-engagement)
    - winback_d60 (D60, re-engagement)
    - cart_abandonment (follow-up)

  If the preferred provider is unavailable or errors, the sender falls back to
  the other provider automatically.

All sends deduplicated via crm_messages (unique: email + template_id).

Required env:
  SENDGRID_API_KEY  = SG.xxxxx (optional, used when configured)
  PLUNK_API_URL     = http://pureleven-plunk:8080 (self-hosted instance)
  PLUNK_API_KEY     = xxxxx
  EMAIL_FROM        = noreply@pureleven.com
  EMAIL_FROM_NAME   = Organic Pure Leven
  SITE_URL          = https://pureleven.com
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger("pureleven.email")

# SendGrid (high-priority, conversion-critical emails)
SENDGRID_API_URL = "https://api.sendgrid.com/v3/mail/send"
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")

# Plunk Self-Hosted (cost-optimized follow-ups)
# Local Plunk instance running on same VPS in Docker
PLUNK_API_URL = os.getenv("PLUNK_API_URL", "http://pureleven-plunk:8080")
PLUNK_API_KEY = os.getenv("PLUNK_API_KEY", "")

# Email config
EMAIL_FROM      = os.getenv("EMAIL_FROM",      "noreply@mail.pureleven.com")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Organic Pure Leven")
SITE_URL        = os.getenv("SITE_URL",        "https://pureleven.com")

# Routing: which templates prefer SendGrid vs Plunk
PREFERRED_SENDGRID_TEMPLATES = {
  "_raw_html",
  "welcome",
  "order_confirmation",
  "order_confirmation_cod",
  "order_fulfilled",
  "order_cancelled",
  "out_for_delivery",
  "review_request_d3",
  "payment_pending_cod",
}
PREFERRED_PLUNK_TEMPLATES = {
  "repeat_offer_d7",
  "replenishment_d30",
  "winback_d60",
  "cart_abandonment",
  "review_reminder_d7",
}

_SUCCESS_STATUSES = {"queued", "sent", "delivered", "opened", "clicked"}


# ─── INLINE HTML TEMPLATES ────────────────────────────────────────────────────

_TEMPLATES: dict[str, dict] = {
  "_raw_html": {
    "subject": "{{subject}}",
    "html": "{{__html__}}",
  },

    "welcome": {
        "subject": "Welcome to Organic Pure Leven! 🌿 Your journey to real spices begins",
        "html": """
<div style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;max-width:600px;margin:0 auto;color:#2d2d2d;background:#fff">
  <div style="background:linear-gradient(135deg,#2E7D32 0%,#1B5E20 100%);padding:40px 24px;text-align:center">
    <img src="https://pureleven.com/cdn/shop/files/logo_white.png" alt="Organic Pure Leven" style="height:48px;margin-bottom:16px" onerror="this.style.display='none'">
    <h1 style="color:#fff;margin:0;font-size:26px;font-weight:700;letter-spacing:-0.5px">Welcome to Pure Leven! 🌿</h1>
    <p style="color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:15px">Farm-origin spices, direct to your kitchen</p>
  </div>
  <div style="padding:32px 24px">
    <p style="font-size:16px">Hi <strong>{{customer_name}}</strong>,</p>
    <p style="font-size:15px;line-height:1.6">We're so glad you're here! At Organic Pure Leven, every spice travels directly from family farms in Kerala &amp; the Western Ghats to your kitchen — with no middlemen and no compromises.</p>
    <div style="background:#f0f7f0;border-left:4px solid #2E7D32;border-radius:0 8px 8px 0;padding:20px;margin:24px 0">
      <p style="margin:0 0 8px;font-weight:700;font-size:15px">What makes us different:</p>
      <p style="margin:4px 0;font-size:14px">🌱 <strong>100% Farm-origin</strong> — sourced directly from farmers</p>
      <p style="margin:4px 0;font-size:14px">🏅 <strong>No additives</strong> — pure spices, nothing else</p>
      <p style="margin:4px 0;font-size:14px">🚚 <strong>Free delivery</strong> on orders ₹499+</p>
      <p style="margin:4px 0;font-size:14px">💸 <strong>Cash on Delivery</strong> available across India</p>
    </div>
    <p style="font-size:15px">Explore our bestsellers and start your order today:</p>
    <div style="text-align:center;margin:28px 0">
      <a href="{{shop_url}}" style="background:#2E7D32;color:#fff;padding:14px 36px;text-decoration:none;border-radius:6px;font-size:16px;font-weight:600;display:inline-block">Shop Now →</a>
    </div>
    <p style="color:#666;font-size:13px">Questions? Just reply to this email — we respond within 2 hours.</p>
    <p style="font-size:15px">Happy cooking!<br><strong>— The Pureleven Team</strong></p>
  </div>
  <div style="background:#f5f5f5;padding:16px 24px;text-align:center;font-size:11px;color:#999;border-top:1px solid #e0e0e0">
    <a href="{{unsubscribe_url}}" style="color:#999">Unsubscribe</a> · Organic Pure Leven · Kerala, India
  </div>
</div>
""",
    },

    "order_confirmation_cod": {
        "subject": "Order #{{order_id}} confirmed — Pay ₹{{total}} on delivery 📦",
        "html": """
<div style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;max-width:600px;margin:0 auto;color:#2d2d2d;background:#fff">
  <div style="background:linear-gradient(135deg,#E65100 0%,#BF360C 100%);padding:32px 24px;text-align:center">
    <h1 style="color:#fff;margin:0;font-size:22px;font-weight:700">COD Order Confirmed! 🎉</h1>
    <p style="color:rgba(255,255,255,0.9);margin:8px 0 0;font-size:14px">Cash on Delivery — pay at your door</p>
  </div>
  <div style="padding:28px 24px">
    <p style="font-size:16px">Hi <strong>{{customer_name}}</strong>,</p>
    <p style="font-size:15px">Your order is confirmed! Please keep <strong>₹{{total}}</strong> ready to pay our delivery partner.</p>
    <div style="background:#fff8e1;border:2px solid #FF6B35;border-radius:8px;padding:20px;margin:20px 0;text-align:center">
      <p style="margin:0;font-size:20px;font-weight:700;color:#E65100">Keep ₹{{total}} ready</p>
      <p style="margin:6px 0 0;font-size:13px;color:#666">Pay to the delivery person when your order arrives</p>
    </div>
    <table style="width:100%;border-collapse:collapse;margin:16px 0;border:1px solid #e0e0e0;border-radius:6px;overflow:hidden">
      <tr style="background:#f5f5f5"><td style="padding:10px 14px;font-weight:600;font-size:13px;width:40%">Order ID</td>
          <td style="padding:10px 14px;font-size:14px">#{{order_id}}</td></tr>
      <tr><td style="padding:10px 14px;font-weight:600;font-size:13px;background:#fff">Date</td>
          <td style="padding:10px 14px;font-size:14px">{{order_date}}</td></tr>
      <tr style="background:#f5f5f5"><td style="padding:10px 14px;font-weight:600;font-size:13px">Amount to Pay</td>
          <td style="padding:10px 14px;font-size:14px;font-weight:700;color:#E65100">₹{{total}}</td></tr>
      <tr><td style="padding:10px 14px;font-weight:600;font-size:13px;background:#fff">Items</td>
          <td style="padding:10px 14px;font-size:14px">{{items}}</td></tr>
      <tr style="background:#f5f5f5"><td style="padding:10px 14px;font-weight:600;font-size:13px">Deliver to</td>
          <td style="padding:10px 14px;font-size:14px">{{delivery_address}}</td></tr>
      <tr><td style="padding:10px 14px;font-weight:600;font-size:13px;background:#fff">Expected by</td>
          <td style="padding:10px 14px;font-size:14px">{{delivery_date}}</td></tr>
    </table>
    <div style="text-align:center;margin:24px 0">
      <a href="{{tracking_url}}" style="background:#2E7D32;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-size:15px;font-weight:600">Track My Order</a>
    </div>
    <div style="background:#f0f7f0;border-radius:6px;padding:16px;margin:16px 0">
      <p style="margin:0;font-size:14px">✓ Organic, farm-origin quality guaranteed</p>
      <p style="margin:6px 0;font-size:14px">✓ Return accepted if quality doesn't match</p>
      <p style="margin:0;font-size:14px">✓ Customer support: reply to this email</p>
    </div>
    <p style="color:#666;font-size:13px">Have questions? Reply here or call <strong>8590 123456</strong>.</p>
    <p>Thank you for choosing farm-origin spices!<br><strong>— The Pureleven Team</strong></p>
  </div>
  <div style="background:#f5f5f5;padding:12px 24px;text-align:center;font-size:11px;color:#999;border-top:1px solid #e0e0e0">
    <a href="{{unsubscribe_url}}" style="color:#999">Unsubscribe</a> · Organic Pure Leven · Kerala, India
  </div>
</div>
""",
    },

    "out_for_delivery": {
        "subject": "Your Pureleven order #{{order_id}} arrives today! 🚴",
        "html": """
<div style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;max-width:600px;margin:0 auto;color:#2d2d2d;background:#fff">
  <div style="background:linear-gradient(135deg,#1565C0 0%,#0D47A1 100%);padding:32px 24px;text-align:center">
    <h1 style="color:#fff;margin:0;font-size:24px;font-weight:700">Out for Delivery! 🚴</h1>
    <p style="color:rgba(255,255,255,0.9);margin:8px 0 0;font-size:15px">Your order is on its way — arriving today</p>
  </div>
  <div style="padding:28px 24px">
    <p style="font-size:16px">Hi <strong>{{customer_name}}</strong>,</p>
    <p style="font-size:15px;line-height:1.6">Great news! Your order <strong>#{{order_id}}</strong> is out for delivery and will reach you <strong>today</strong>.</p>
    <div style="background:#e3f2fd;border-left:4px solid #1565C0;border-radius:0 8px 8px 0;padding:20px;margin:20px 0">
      <p style="margin:0;font-size:18px;font-weight:700;color:#0D47A1">📦 Delivering today!</p>
      <p style="margin:8px 0 0;font-size:14px">Please be available at: <strong>{{delivery_address}}</strong></p>
      {{cod_reminder}}
    </div>
    <table style="width:100%;border-collapse:collapse;margin:16px 0;border:1px solid #e0e0e0;border-radius:6px;overflow:hidden">
      <tr style="background:#f5f5f5"><td style="padding:10px 14px;font-weight:600;font-size:13px;width:40%">Order</td>
          <td style="padding:10px 14px;font-size:14px">#{{order_id}}</td></tr>
      <tr><td style="padding:10px 14px;font-weight:600;font-size:13px">Items</td>
          <td style="padding:10px 14px;font-size:14px">{{items}}</td></tr>
      <tr style="background:#f5f5f5"><td style="padding:10px 14px;font-weight:600;font-size:13px">Tracking</td>
          <td style="padding:10px 14px;font-size:14px"><a href="{{tracking_url}}" style="color:#1565C0">Track shipment</a></td></tr>
    </table>
    <div style="text-align:center;margin:24px 0">
      <a href="{{tracking_url}}" style="background:#1565C0;color:#fff;padding:12px 28px;text-decoration:none;border-radius:6px;font-size:15px;font-weight:600">Live Tracking →</a>
    </div>
    <p style="color:#666;font-size:13px">Can't receive today? Reply to this email immediately and we'll reschedule.</p>
    <p>Enjoy your fresh spices!<br><strong>— The Pureleven Team</strong></p>
  </div>
  <div style="background:#f5f5f5;padding:12px 24px;text-align:center;font-size:11px;color:#999;border-top:1px solid #e0e0e0">
    <a href="{{unsubscribe_url}}" style="color:#999">Unsubscribe</a> · Organic Pure Leven · Kerala, India
  </div>
</div>
""",
    },

    "review_reminder_d7": {
        "subject": "Still enjoying your {{product_name}}? Share your thoughts 🌟",
        "html": """
<div style="font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;max-width:600px;margin:0 auto;color:#2d2d2d;background:#fff">
  <div style="background:linear-gradient(135deg,#F57F17 0%,#E65100 100%);padding:32px 24px;text-align:center">
    <h1 style="color:#fff;margin:0;font-size:22px;font-weight:700">A week with your spice — how is it? ⭐</h1>
  </div>
  <div style="padding:28px 24px">
    <p style="font-size:16px">Hi <strong>{{customer_name}}</strong>,</p>
    <p style="font-size:15px;line-height:1.6">It's been a week since your <strong>{{product_name}}</strong> arrived. We hope you've had a chance to cook with it!</p>
    <p style="font-size:15px">Your experience matters — both to us and to customers deciding to buy. A quick review (even 1 sentence!) helps us improve and earns you <strong>₹100 loyalty points</strong>.</p>
    <div style="background:#fff8e1;border:2px solid #FF6B35;border-radius:8px;padding:20px;text-align:center;margin:24px 0">
      <p style="margin:0;font-size:18px;font-weight:700;color:#E65100">₹100 loyalty points</p>
      <p style="margin:6px 0 0;font-size:14px;color:#666">Just for sharing your honest thoughts</p>
    </div>
    <div style="text-align:center;margin:28px 0">
      <a href="{{review_url}}" style="background:#FF6B35;color:#fff;padding:14px 36px;text-decoration:none;border-radius:6px;font-size:16px;font-weight:600;display:inline-block">Write My Review ⭐</a>
    </div>
    <p style="color:#999;font-size:12px">Not interested? No worries — <a href="{{unsubscribe_url}}" style="color:#999">unsubscribe</a> here.</p>
    <p>— Pureleven Team</p>
  </div>
</div>
""",
    },

    "order_confirmation": {
        "subject": "Your Pureleven order #{{order_id}} is confirmed! 🎉",
        "html": """
<div style="font-family:sans-serif;max-width:600px;margin:0 auto;color:#2d2d2d">
  <div style="background:#2E7D32;padding:24px;text-align:center">
    <h1 style="color:#fff;margin:0;font-size:22px">Order Confirmed! 🎉</h1>
  </div>
  <div style="padding:24px">
    <p>Hi {{customer_name}},</p>
    <p>Thank you for your order! Here are your details:</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0">
      <tr><td style="padding:8px;background:#f5f5f5;font-weight:bold">Order ID</td>
          <td style="padding:8px">#{{order_id}}</td></tr>
      <tr><td style="padding:8px;background:#f5f5f5;font-weight:bold">Date</td>
          <td style="padding:8px">{{order_date}}</td></tr>
      <tr><td style="padding:8px;background:#f5f5f5;font-weight:bold">Total</td>
          <td style="padding:8px">₹{{total}}</td></tr>
      <tr><td style="padding:8px;background:#f5f5f5;font-weight:bold">Items</td>
          <td style="padding:8px">{{items}}</td></tr>
      <tr><td style="padding:8px;background:#f5f5f5;font-weight:bold">Delivery to</td>
          <td style="padding:8px">{{delivery_address}}</td></tr>
      <tr><td style="padding:8px;background:#f5f5f5;font-weight:bold">Method</td>
          <td style="padding:8px">{{payment_method}}</td></tr>
      <tr><td style="padding:8px;background:#f5f5f5;font-weight:bold">Expected delivery</td>
          <td style="padding:8px">{{delivery_date}}</td></tr>
    </table>
    <div style="text-align:center;margin:24px 0">
      <a href="{{tracking_url}}" style="background:#2E7D32;color:#fff;padding:12px 28px;text-decoration:none;border-radius:4px;font-size:15px">Track My Order</a>
    </div>
    <p style="color:#666;font-size:13px">Questions? Reply to this email or call <strong>8590 123456</strong>.</p>
    <p>Thank you for supporting farm-origin spices!<br>— The Pureleven Team</p>
  </div>
  <div style="background:#f5f5f5;padding:12px;text-align:center;font-size:11px;color:#999">
    <a href="{{unsubscribe_url}}">Unsubscribe</a> · Organic Pure Leven · Kerala, India
  </div>
</div>
""",
    },

    "order_fulfilled": {
        "subject": "Your Pureleven order #{{order_id}} is on the way 🚚",
        "html": """
<div style="font-family:sans-serif;max-width:600px;margin:0 auto;color:#2d2d2d">
  <div style="background:#2E7D32;padding:24px;text-align:center">
    <h1 style="color:#fff;margin:0;font-size:22px">Your order is on the way 🚚</h1>
  </div>
  <div style="padding:24px">
    <p>Hi {{customer_name}},</p>
    <p>Your order <strong>#{{order_id}}</strong> has been fulfilled and is moving through dispatch.</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0">
      <tr><td style="padding:8px;background:#f5f5f5;font-weight:bold">Items</td>
          <td style="padding:8px">{{items}}</td></tr>
      <tr><td style="padding:8px;background:#f5f5f5;font-weight:bold">Delivery to</td>
          <td style="padding:8px">{{delivery_address}}</td></tr>
      <tr><td style="padding:8px;background:#f5f5f5;font-weight:bold">Expected delivery</td>
          <td style="padding:8px">{{delivery_date}}</td></tr>
    </table>
    <div style="text-align:center;margin:24px 0">
      <a href="{{tracking_url}}" style="background:#2E7D32;color:#fff;padding:12px 28px;text-decoration:none;border-radius:4px;font-size:15px">Track Shipment</a>
    </div>
    <p>We will keep you posted until it arrives.<br>— The Pureleven Team</p>
  </div>
</div>
""",
    },

    "order_cancelled": {
        "subject": "Update on your Pureleven order #{{order_id}}",
        "html": """
<div style="font-family:sans-serif;max-width:600px;margin:0 auto;color:#2d2d2d">
  <div style="background:#6D4C41;padding:24px;text-align:center">
    <h1 style="color:#fff;margin:0;font-size:22px">Order update</h1>
  </div>
  <div style="padding:24px">
    <p>Hi {{customer_name}},</p>
    <p>Your order <strong>#{{order_id}}</strong> has been cancelled.</p>
    <p>{{cancel_reason}}</p>
    <div style="background:#f9f9f9;padding:16px;border-radius:6px;margin:20px 0">
      <p style="margin:0"><strong>Need help placing a fresh order?</strong></p>
      <p style="margin:8px 0 0">We can help you reorder the same farm-origin spices in a few clicks.</p>
    </div>
    <div style="text-align:center;margin:24px 0">
      <a href="{{shop_url}}" style="background:#2E7D32;color:#fff;padding:12px 28px;text-decoration:none;border-radius:4px;font-size:15px">Shop Again</a>
    </div>
    <p>If this looks incorrect, reply to this email and we’ll sort it out quickly.<br>— The Pureleven Team</p>
  </div>
</div>
""",
    },

    "review_request_d3": {
        "subject": "How's your {{product_name}}? We'd love your feedback 🌟",
        "html": """
<div style="font-family:sans-serif;max-width:600px;margin:0 auto;color:#2d2d2d">
  <div style="background:#2E7D32;padding:24px;text-align:center">
    <h1 style="color:#fff;margin:0;font-size:20px">How was your experience?</h1>
  </div>
  <div style="padding:24px">
    <p>Hi {{customer_name}},</p>
    <p>Your order arrived! How do you like your fresh <strong>{{product_name}}</strong>?</p>
    <p>Your honest review helps us improve — and earns you <strong>₹100 loyalty points</strong>.</p>
    <div style="background:#f9f9f9;border-left:4px solid #2E7D32;padding:16px;margin:20px 0">
      <p style="margin:0"><strong>10-second review:</strong></p>
      <ol style="margin:8px 0 0">
        <li>Rate 1–5 stars</li>
        <li>Write 1–2 sentences (optional)</li>
        <li>Get ₹100 loyalty points instantly!</li>
      </ol>
    </div>
    <div style="text-align:center;margin:24px 0">
      <a href="{{review_url}}" style="background:#FF6B35;color:#fff;padding:12px 28px;text-decoration:none;border-radius:4px;font-size:15px">Write My Review ⭐</a>
    </div>
    <p style="color:#666;font-size:13px">Questions? Reply here — we respond within 2 hours.</p>
    <p>— Pureleven Team</p>
  </div>
</div>
""",
    },

    "repeat_offer_d7": {
        "subject": "Your first order was great. Order again — ₹50 off! 💚",
        "html": """
<div style="font-family:sans-serif;max-width:600px;margin:0 auto;color:#2d2d2d">
  <div style="background:#2E7D32;padding:24px;text-align:center">
    <h1 style="color:#fff;margin:0;font-size:20px">Complete Your Spice Collection 🌿</h1>
  </div>
  <div style="padding:24px">
    <p>Hi {{customer_name}},</p>
    <p>Love your fresh {{product_name}}? Here's what pairs perfectly with it:</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0">
      <tr><td style="padding:10px;background:#f0f7f0;border-radius:4px">✓ Turmeric 100g (₹199) — Immunity + colour</td></tr>
      <tr><td style="padding:10px">✓ Clove 50g (₹249) — Digestion + aroma</td></tr>
      <tr><td style="padding:10px;background:#f0f7f0;border-radius:4px">✓ Bundle all 3 (₹699, normally ₹749)</td></tr>
    </table>
    <div style="background:#fff3e0;border:2px solid #FF6B35;padding:16px;text-align:center;border-radius:6px;margin:20px 0">
      <p style="margin:0;font-size:18px">Use code <strong>REPEAT50</strong> for ₹50 off!</p>
      <p style="margin:4px 0;color:#666;font-size:13px">Valid for 7 days only.</p>
    </div>
    <div style="text-align:center;margin:20px 0">
      <a href="{{shop_url}}" style="background:#2E7D32;color:#fff;padding:12px 28px;text-decoration:none;border-radius:4px;font-size:15px">Shop Now</a>
    </div>
    <p>— Pureleven Team</p>
  </div>
</div>
""",
    },

    "replenishment_d30": {
        "subject": "Time to reorder? Fresh harvest just in stock 💚",
        "html": """
<div style="font-family:sans-serif;max-width:600px;margin:0 auto;color:#2d2d2d">
  <div style="background:#2E7D32;padding:24px;text-align:center">
    <h1 style="color:#fff;margin:0;font-size:20px">Running Low? Fresh Stock Arrived! 🌿</h1>
  </div>
  <div style="padding:24px">
    <p>Hi {{customer_name}},</p>
    <p>30 days ago you ordered <strong>{{product_name}}</strong>.</p>
    <p>We just got a fresh harvest from Wayanad. Same quality you loved.</p>
    <div style="background:#f9f9f9;padding:16px;border-radius:6px;margin:20px 0">
      <p style="margin:0;font-weight:bold">{{product_name}}</p>
      <p style="margin:4px 0">Price: ₹{{price}}</p>
      <p style="margin:4px 0;color:#2E7D32">✓ Free delivery to {{city}}</p>
    </div>
    <div style="background:#fff3e0;border:2px solid #FF6B35;padding:16px;text-align:center;border-radius:6px;margin:20px 0">
      <p style="margin:0;font-size:18px">Use code <strong>REFILL30</strong> for ₹100 off!</p>
      <p style="margin:4px 0;color:#666;font-size:13px">Valid for 14 days only.</p>
    </div>
    <div style="text-align:center;margin:20px 0">
      <a href="{{product_url}}" style="background:#2E7D32;color:#fff;padding:12px 28px;text-decoration:none;border-radius:4px;font-size:15px">Reorder Now</a>
    </div>
    <p>— Pureleven Team</p>
  </div>
</div>
""",
    },

    "winback_d60": {
        "subject": "We miss you! Fresh harvest + ₹150 loyalty discount 💚",
        "html": """
<div style="font-family:sans-serif;max-width:600px;margin:0 auto;color:#2d2d2d">
  <div style="background:#1B5E20;padding:24px;text-align:center">
    <h1 style="color:#fff;margin:0;font-size:20px">We Miss You, {{customer_name}}! 💚</h1>
  </div>
  <div style="padding:24px">
    <p>It's been {{days_since}} days since your last order with us.</p>
    <p>We've been thinking — how can we earn you back?</p>
    <div style="background:#fff3e0;border:2px solid #FF6B35;padding:20px;text-align:center;border-radius:6px;margin:20px 0">
      <p style="margin:0;font-size:20px;font-weight:bold">₹150 off orders above ₹649</p>
      <p style="margin:8px 0;font-size:18px">Code: <strong>MISSYOU150</strong></p>
      <p style="margin:4px 0;color:#666;font-size:13px">Valid for 7 days only.</p>
    </div>
    <p><strong>Your favourites are still here:</strong></p>
    <ul>{{previously_purchased_items}}</ul>
    <div style="text-align:center;margin:20px 0">
      <a href="{{shop_url}}" style="background:#2E7D32;color:#fff;padding:12px 28px;text-decoration:none;border-radius:4px;font-size:15px">Shop Now</a>
    </div>
    <p>Let's reconnect! 💚<br>— Pureleven Team</p>
  </div>
</div>
""",
    },

    "cart_abandonment": {
        "subject": "You left {{product_name}} in your cart 🛒",
        "html": """
<div style="font-family:sans-serif;max-width:600px;margin:0 auto;color:#2d2d2d">
  <div style="background:#2E7D32;padding:24px;text-align:center">
    <h1 style="color:#fff;margin:0;font-size:20px">Something caught your eye! 👀</h1>
  </div>
  <div style="padding:24px">
    <p>Hi {{customer_name}},</p>
    <p>You left <strong>{{product_name}}</strong> (₹{{price}}) in your cart.</p>
    <div style="background:#f0f7f0;padding:16px;border-radius:6px;margin:20px 0">
      <p style="margin:0">✓ Cash on Delivery available</p>
      <p style="margin:6px 0">✓ Free delivery on orders ₹499+</p>
      <p style="margin:0">✓ Complete checkout in 2 minutes</p>
    </div>
    <div style="text-align:center;margin:24px 0">
      <a href="{{cart_url}}" style="background:#FF6B35;color:#fff;padding:14px 32px;text-decoration:none;border-radius:4px;font-size:16px">Complete My Order →</a>
    </div>
    <p style="color:#666;font-size:13px">This cart will expire in 24 hours.</p>
    <p>— Pureleven Team</p>
  </div>
</div>
""",
    },
}


def _render(template_name: str, substitutions: dict) -> tuple[str, str]:
    """Render subject + HTML from internal template with substitutions."""
    tmpl = _TEMPLATES.get(template_name)
    if not tmpl:
        raise ValueError(f"Unknown email template: '{template_name}'")

    subject = tmpl["subject"]
    html    = tmpl["html"]

    for key, value in substitutions.items():
        placeholder = "{{" + key + "}}"
        subject = subject.replace(placeholder, str(value or ""))
        html    = html.replace(placeholder, str(value or ""))

    return subject, html


def _normalize_email(email: str) -> str:
    return (email or "").strip().lower()


def _build_message_template_id(template_name: str, dedup_key: Optional[str]) -> str:
    if not dedup_key:
        return template_name
    digest = hashlib.sha1(str(dedup_key).encode("utf-8")).hexdigest()[:16]
    return f"{template_name}:{digest}"


def _provider_order_for_template(template_name: str) -> list[str]:
    if template_name in PREFERRED_SENDGRID_TEMPLATES:
        return ["sendgrid", "plunk"]
    if template_name in PREFERRED_PLUNK_TEMPLATES:
        return ["plunk", "sendgrid"]
    return ["plunk", "sendgrid"]


def send_email(
    to_email: str,
    template_name: str,
    substitutions: Optional[dict] = None,
    dedup_key: Optional[str] = None,
    db=None,
) -> dict:
    """
    Send email via SendGrid or Plunk.
    Deduplicates by (to_email, template_name, dedup_key) using crm_messages.

    Returns: {"status": "sent" | "duplicate" | "error", ...}
    """
    substitutions = dict(substitutions or {})
    to_email = _normalize_email(to_email)
    dedup_key = dedup_key or substitutions.pop("__dedup_key__", None)

    if template_name == "_raw_html" and not dedup_key:
        html_seed = f"{substitutions.get('subject', '')}:{substitutions.get('__html__', '')}"
        dedup_key = hashlib.sha1(html_seed.encode("utf-8")).hexdigest()[:16]

    message_template_id = _build_message_template_id(template_name, dedup_key)

    if db is not None:
        try:
            from crm_models import MessageLog

            existing = (
                db.query(MessageLog)
                .filter(
                    MessageLog.customer_email == to_email,
                    MessageLog.template_id == message_template_id,
                    MessageLog.status.in_(tuple(_SUCCESS_STATUSES)),
                )
                .first()
            )
            if existing:
                logger.info("Email dedup: %s already sent %s", to_email, message_template_id)
                return {"status": "duplicate", "sent_at": str(existing.sent_at)}
        except Exception as exc:
            logger.warning("Dedup check failed (non-fatal): %s", exc)

    try:
        subject, html_body = _render(template_name, substitutions)
    except ValueError as exc:
        return {"status": "error", "reason": str(exc)}

    result = None
    attempts: list[dict] = []
    for provider in _provider_order_for_template(template_name):
        if provider == "sendgrid":
            attempt = _send_via_sendgrid(to_email, template_name, subject, html_body, substitutions)
        else:
            attempt = _send_via_plunk(to_email, template_name, subject, html_body)

        attempts.append({
            "provider": provider,
            "status": attempt.get("status"),
            "detail": attempt.get("reason") or attempt.get("detail"),
        })

        if attempt.get("status") == "sent":
            result = attempt
            break

        logger.warning(
            "Email send attempt failed provider=%s template=%s recipient=%s reason=%s",
            provider,
            template_name,
            to_email,
            attempt.get("reason") or attempt.get("detail") or attempt.get("status"),
        )

    if result is None:
        final_attempt = attempts[-1] if attempts else {"provider": "unknown", "status": "error"}
        result = {
            "status": "error",
            "provider": final_attempt.get("provider", "unknown"),
            "reason": final_attempt.get("detail") or "All email providers failed",
            "http_code": None,
        }

    result["attempted"] = attempts

    provider = result.get("provider", "unknown")
    metadata = {
        "template_name": template_name,
        "dedup_key": dedup_key,
        "attempted_providers": [attempt["provider"] for attempt in attempts],
        "quality": provider == "sendgrid",
    }

    if result["status"] == "sent":
        _log_message(db, to_email, message_template_id, "sent", result.get("http_code"), provider, metadata)
        logger.info("Email %s sent: %s → %s", provider, template_name, to_email)
    else:
        _log_message(db, to_email, message_template_id, "failed", result.get("http_code"), provider, metadata)

    return result


def _send_via_sendgrid(
    to_email: str,
    template_name: str,
    subject: str,
    html_body: str,
    substitutions: dict,
) -> dict:
    """Send via SendGrid when configured."""
    if not SENDGRID_API_KEY:
        return {"status": "skipped", "reason": "SENDGRID_API_KEY not configured", "provider": "sendgrid"}

    payload = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": EMAIL_FROM, "name": EMAIL_FROM_NAME},
        "subject": subject,
        "content": [{"type": "text/html", "value": html_body}],
    }

    sg_template_key = f"SENDGRID_TEMPLATE_{template_name.upper()}"
    sg_template_id = os.getenv(sg_template_key, "")
    if sg_template_id:
        payload = {
            "personalizations": [{
                "to": [{"email": to_email}],
                "dynamic_template_data": substitutions,
            }],
            "from": {"email": EMAIL_FROM, "name": EMAIL_FROM_NAME},
            "template_id": sg_template_id,
        }

    body = json.dumps(payload).encode()

    try:
        req = urllib.request.Request(
            SENDGRID_API_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {SENDGRID_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            status_code = resp.status
            message_id = resp.headers.get("X-Message-Id", "")
        return {
            "status": "sent",
            "message_id": message_id,
            "http_code": status_code,
            "provider": "sendgrid",
        }
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="ignore")
        logger.error("SendGrid HTTP %d: %s", exc.code, err)
        return {"status": "error", "http_code": exc.code, "detail": err, "provider": "sendgrid"}
    except Exception as exc:
        logger.error("SendGrid send error: %s", exc)
        return {"status": "error", "reason": str(exc), "provider": "sendgrid"}


def _send_via_plunk(
    to_email: str,
    template_name: str,
    subject: str,
    html_body: str,
) -> dict:
    """
    Send via the self-hosted Plunk instance.
    """
    if not PLUNK_API_URL:
        return {"status": "skipped", "reason": "PLUNK_API_URL not configured", "provider": "plunk"}
    if not PLUNK_API_KEY:
        return {"status": "skipped", "reason": "PLUNK_API_KEY not configured", "provider": "plunk"}

    send_endpoint = f"{PLUNK_API_URL}/v1/send"
    payload = {
        "to": to_email,
        "subject": subject,
        "body": html_body,
        "from": EMAIL_FROM,
    }
    body = json.dumps(payload).encode()

    try:
        req = urllib.request.Request(
            send_endpoint,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {PLUNK_API_KEY}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            status_code = resp.status
            response_data = json.loads(resp.read().decode())
        message_id = response_data.get("id", "")
        return {
            "status": "sent",
            "message_id": message_id,
            "http_code": status_code,
            "provider": "plunk",
        }
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="ignore")
        logger.error("Plunk HTTP %d: %s", exc.code, err)
        return {"status": "error", "http_code": exc.code, "detail": err, "provider": "plunk"}
    except Exception as exc:
        logger.error("Plunk send error: %s", exc)
        return {"status": "error", "reason": str(exc), "provider": "plunk"}


def _mark_email_quality(db, email: str, template_id: str):
    """Mark email as quality traffic when it was delivered by SendGrid."""
    if db is None:
        return
    try:
        from crm_models import MessageLog

        existing = (
            db.query(MessageLog)
            .filter(
                MessageLog.customer_email == email,
                MessageLog.template_id == template_id,
            )
            .first()
        )
        if existing and isinstance(existing.msg_metadata, dict):
            existing.msg_metadata["quality"] = True
            db.commit()
            logger.info("Marked %s/%s as quality", email, template_id)
    except Exception as exc:
        logger.warning("Quality mark failed: %s", exc)


def _log_message(db, email: str, template_id: str, status: str, response_code, provider: str = None, metadata: Optional[dict] = None):
    """Write send result to crm_messages."""
    if db is None:
        return
    try:
        from crm_models import MessageLog
        from uuid import uuid4

        record = (
            db.query(MessageLog)
            .filter(
                MessageLog.customer_email == email,
                MessageLog.template_id == template_id,
            )
            .first()
        )
        sent_at = datetime.now(timezone.utc)
        if record:
            existing_metadata = record.msg_metadata if isinstance(record.msg_metadata, dict) else {}
            record.status = status
            record.response_code = response_code
            record.provider = provider or record.provider or "unknown"
            record.msg_metadata = {**existing_metadata, **(metadata or {})}
            record.sent_at = sent_at
        else:
            record = MessageLog(
                id=str(uuid4()),
                customer_email=email,
                channel="email",
                template_id=template_id,
                status=status,
                response_code=response_code,
                provider=provider or "unknown",
                msg_metadata=metadata or None,
                sent_at=sent_at,
            )
            db.add(record)
        db.commit()
    except Exception as exc:
        logger.warning("MessageLog write failed: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
