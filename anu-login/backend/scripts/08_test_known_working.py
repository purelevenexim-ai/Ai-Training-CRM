#!/usr/bin/env python3
"""
scripts/08_test_known_working.py

Send all 25 journey templates to a phone number using the correct
parameter counts verified against live Meta template definitions.

Usage:
  cd anu-login/backend
  set -a; source .env; set +a
  ../../.venv/bin/python scripts/08_test_known_working.py --phone 918547574028
"""

from __future__ import annotations

import argparse
import json
import os
import ssl
import time
from datetime import datetime, timezone

try:
    import certifi
    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl.create_default_context()

import urllib.request
import urllib.error

STORE_URL = "https://pureleven.com"
REVIEW_URL = "https://g.page/r/pureleven/review"
CALENDAR_URL = "https://calendly.com/pureleven/bulk"
TRACK_URL = "https://pureleven.com/account/orders"

# ── Meta API ─────────────────────────────────────────────────────────────────

def _send(phone: str, template: str, body: list[str], btn_url: str | None = None) -> tuple[bool, str]:
    token    = os.getenv("META_ACCESS_TOKEN", "").strip()
    phone_id = os.getenv("META_PHONE_NUMBER_ID", "").strip()
    if not token or not phone_id:
        return False, "missing creds"

    components = []
    if body:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": p} for p in body],
        })
    if btn_url:
        components.append({
            "type": "button",
            "sub_type": "url",
            "index": "0",
            "parameters": [{"type": "text", "text": btn_url}],
        })

    payload: dict = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": template,
            "language": {"code": "en"},
        },
    }
    if components:
        payload["template"]["components"] = components

    req = urllib.request.Request(
        f"https://graph.facebook.com/v20.0/{phone_id}/messages",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=20) as resp:
            r = json.loads(resp.read().decode())
            mid = ((r.get("messages") or [{}])[0]).get("id", "")
            return True, mid
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}: {e.read().decode(errors='replace')[:120]}"
    except Exception as e:
        return False, str(e)[:100]


# ── Template definitions (name, body_params, btn_url or None) ────────────────
# Verified against live Meta template components on 2026-05-20.
# body param counts match Meta {{1}}, {{2}}... placeholders exactly.
# Dynamic URL buttons: only order_confirmed, delivery_begun, delivery_out_for_delivery.
# All marketing templates: buttons are static in Meta, send None for btn.

def _templates() -> list[tuple[str, list[str], str | None]]:
    name = "Test"
    waybill = "AWB123456"
    order_id = "#1234"
    eta = "2-5 business days"
    review = f"{REVIEW_URL}?utm_source=test"
    shop = f"{STORE_URL}?utm_source=test"
    coupon = "REVIEW50"
    rec_name = "Green Cardamom"
    rec_url = f"{STORE_URL}/products/green-cardamom-100g?utm_source=test"
    cal = f"{CALENDAR_URL}?utm_source=test"

    return [
        # ── Transactional (btn=1 dynamic URL) ─────────────────────────────────
        ("order_confirmed_v1",            [name, order_id, eta],                     TRACK_URL),
        ("delivery_begun_v1",             [name, waybill, eta],                      TRACK_URL),
        ("delivery_out_for_delivery_v1",  [name, waybill],                           TRACK_URL),
        # ── Review & Feedback (btn=0) ──────────────────────────────────────────
        ("delivered_review_request_v1",   [name, review],                            None),
        ("delivered_vip_v1",              [name, review],                            None),
        ("review_incentive_v1",           [name, "₹200", review, coupon],           None),
        ("review_reminder_v1",            [name, review, coupon],                    None),
        ("review_faq_response_v1",        [name, f"{STORE_URL}/pages/faq"],         None),
        ("review_thank_you_v1",           [name, shop],                              None),
        # ── Upsell & Cross-sell (btn=0) ───────────────────────────────────────
        ("explore_products_v1",           [name, rec_name, rec_url, "EXPLORE20"],   None),
        ("upsell_followup_v1",            [name, rec_name, rec_url],                 None),
        ("price_sensitive_sale_v1",       [name, rec_name, rec_url, "SALE25"],      None),
        # ── B2B Corporate (btn=0) ─────────────────────────────────────────────
        ("corporate_pitch_high_v1",       [name, "₹15,000", cal],                  None),
        ("corporate_pitch_low_v1",        [name, "₹5,000"],                         None),
        ("corporate_followup_v1",         [name, cal],                               None),
        # ── Loyalty & Repeat (btn=0) ──────────────────────────────────────────
        ("loyalty_checkin_v1",            [name, "75", shop, "WELCOME20"],          None),
        ("vip_exclusive_v1",              [name, shop],                              None),
        ("repeat_buyer_exclusive_v1",     [name, shop],                              None),
        # ── Winback & Reactivation (btn=0) ────────────────────────────────────
        ("winback_offer_v1",              [name, shop, "COMEBACK"],                  None),
        ("extreme_winback_v1",            [name, shop, "₹1,000"],                  None),
        ("reactivation_survey_v1",        [name],                                    None),
        # ── Seasonal & Promotional (btn=0) ────────────────────────────────────
        ("promo_monsoon_v1",              [name, shop],                              None),
        ("promo_diwali_v1",               [name, shop],                              None),
        ("promo_new_harvest_v1",          [name, shop],                              None),
        ("promo_bulk_sale_v1",            [name, shop],                              None),
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phone", required=True)
    args = parser.parse_args()
    phone = args.phone

    templates = _templates()
    total = len(templates)

    print(f"\n── Sending {total} Templates (Verified Params) ─────────────────────────────")
    print(f"   To  : {phone}")
    print(f"   Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print()

    sent = 0
    failed = 0
    results: list[dict] = []

    for i, (tname, body, btn) in enumerate(templates, 1):
        ok, result = _send(phone, tname, body, btn)
        if ok:
            sent += 1
            print(f"  ✅  [{i:02}/{total}]  {tname:40}  {result[:38]}")
            results.append({"template": tname, "status": "sent", "message_id": result})
        else:
            failed += 1
            print(f"  ❌  [{i:02}/{total}]  {tname:40}  {result[:65]}")
            results.append({"template": tname, "status": "failed", "error": result})
        time.sleep(0.4)

    print()
    print(f"── Summary ─────────────────────────────────────────────────────────────────")
    print(f"   Sent  : {sent}/{total}")
    print(f"   Failed: {failed}/{total}")

    if failed:
        print()
        print("── Failed Templates ─────────────────────────────────────────────────────────")
        for r in results:
            if r["status"] == "failed":
                print(f"   ❌  {r['template']:40}  {r.get('error','')[:80]}")

    print()
    print("── Audit Delivery (wait 30 sec for Meta webhooks, then run) ────────────────")
    print(f"   curl 'http://localhost:8000/api/tracking/meta-status/by-phone?phone={phone}&limit=100'")
    print()


if __name__ == "__main__":
    main()

