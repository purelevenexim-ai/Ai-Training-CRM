#!/usr/bin/env python3
"""
scripts/04_test_e2e.py

End-to-end journey simulation test.

Simulates a complete customer lifecycle:
  1. Shopify order created   → Day 1 order_confirmed_v1 (dev stub)
  2. Delhivery in-transit    → Day 2 delivery_begun_v1 (dev stub)
  3. Delhivery delivered     → Day 5 delivered_review_request_v1 (dev stub)
  4. WhatsApp button click   → engagement_score += 5
  5. Orchestrate dry-run     → preview Day 15/30/60 cohorts
  6. Mark reviewed           → engagement_score += 50
  7. Final stats check

The server must be running before you execute this script.

Usage:
  # Start the server in another terminal:
  cd anu-login/backend
  uvicorn app.main:app --reload --port 8000

  # Run this test:
  python scripts/04_test_e2e.py [--base-url http://localhost:8000]
  python scripts/04_test_e2e.py --base-url https://your-tunnel.loca.lt

Options:
  --base-url URL      API base URL (default: http://localhost:8000)
  --phone PHONE       Test phone in E.164 format (default: 919876543210)
  --shop DOMAIN       Shop domain (default: rwxtic-gz.myshopify.com)
  --cleanup           Delete test customer after run
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

# ─── Config ──────────────────────────────────────────────────────────────────

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_PHONE    = "919876543210"
DEFAULT_SHOP     = os.getenv("SHOPIFY_SHOP_DOMAIN", "rwxtic-gz.myshopify.com")
SHOPIFY_SECRET   = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")
DELHIVERY_SECRET = os.getenv("DELHIVERY_WEBHOOK_SECRET", "")

PASS = "✅"
FAIL = "❌"
INFO = "ℹ️ "
WARN = "⚠️ "


# ─── HTTP helpers ─────────────────────────────────────────────────────────────

def _call(method: str, url: str, body: dict | None = None,
          headers: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body, ensure_ascii=True).encode() if body else None
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            return exc.code, json.loads(detail)
        except json.JSONDecodeError:
            return exc.code, {"detail": detail}


def post(base: str, path: str, body: dict, headers: dict | None = None,
         params: dict | None = None) -> tuple[int, dict]:
    url = f"{base}{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{qs}"
    return _call("POST", url, body, headers)


def get(base: str, path: str, params: dict | None = None) -> tuple[int, dict]:
    url = f"{base}{path}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url = f"{url}?{qs}"
    return _call("GET", url)


# ─── HMAC helpers ─────────────────────────────────────────────────────────────

def _shopify_hmac(body: bytes, secret: str) -> str:
    if not secret:
        return "dev_no_secret"
    sig = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(sig).decode()


def _delhivery_hmac(body: bytes, secret: str) -> str:
    if not secret:
        return "dev_no_secret"
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


# ─── Test runner ──────────────────────────────────────────────────────────────

class TestRunner:
    def __init__(self, base_url: str, phone: str, shop: str) -> None:
        self.base    = base_url.rstrip("/")
        self.phone   = phone
        self.shop    = shop
        self.passed  = 0
        self.failed  = 0
        self.customer_id: str | None = None

    def check(self, label: str, cond: bool, detail: str = "") -> bool:
        if cond:
            self.passed += 1
            print(f"  {PASS}  {label}")
        else:
            self.failed += 1
            print(f"  {FAIL}  {label}")
            if detail:
                print(f"       → {detail}")
        return cond

    def section(self, title: str) -> None:
        print(f"\n{'─' * 60}")
        print(f"  {title}")
        print('─' * 60)

    # ── Tests ──────────────────────────────────────────────────────────────

    def test_health(self) -> bool:
        self.section("0. Health check")
        code, resp = get(self.base, "/health")
        if code == 200:
            print(f"  {PASS}  Server is up: {resp}")
            return True
        # Try root
        code2, _ = get(self.base, "/")
        ok = code2 < 500
        self.check("Server reachable", ok,
                   f"GET /health → {code}, GET / → {code2}")
        return ok

    def test_order_created(self) -> bool:
        self.section("1. Shopify order/create webhook")
        now_iso = datetime.now(timezone.utc).isoformat()
        order = {
            "id": 5001234567890,
            "order_number": 1042,
            "name": "#1042",
            "email": "priya.nair@example.com",
            "created_at": now_iso,
            "total_price": "750.00",
            "billing_address": {"phone": self.phone},
            "customer": {
                "id": 7001234567890,
                "first_name": "Priya",
                "last_name": "Nair",
                "email": "priya.nair@example.com",
                "phone": self.phone,
            },
            "shipping_address": {"phone": self.phone},
            "line_items": [
                {"product_id": 101, "handle": "kerala-black-pepper-200gm", "title": "Kerala Black Pepper 200g"}
            ],
        }
        body_bytes = json.dumps(order, ensure_ascii=True).encode()
        sig = _shopify_hmac(body_bytes, SHOPIFY_SECRET)
        code, resp = post(
            self.base, "/api/shopify/webhook/order-created", order,
            headers={"X-Shopify-Hmac-Sha256": sig, "X-Shopify-Shop-Domain": self.shop},
        )
        ok = self.check("Order webhook accepted (2xx)", 200 <= code < 300,
                        f"HTTP {code}: {str(resp)[:100]}")
        if ok:
            cid = resp.get("customer_id") or resp.get("id")
            if cid:
                self.customer_id = str(cid)
                print(f"       customer_id = {self.customer_id}")
            msg_sent = resp.get("day1_sent") or resp.get("message_sent") or resp.get("status")
            self.check("Day 1 message triggered", bool(msg_sent), str(resp)[:80])
        return ok

    def test_inspect_customer(self) -> bool:
        self.section("2. Inspect journey customer")
        code, resp = get(self.base, f"/api/journey/customers/{self.phone}",
                         params={"shop_domain": self.shop})
        ok = self.check("Customer found in journey", code == 200, f"HTTP {code}: {str(resp)[:80]}")
        if ok:
            self.customer_id = self.customer_id or str(resp.get("id", ""))
            orders = resp.get("orders", [{}])
            first = orders[0] if orders else {}
            self.check("Phone matches",
                       self.phone in str(first.get("phone", "")))
            self.check("journey_stage set",
                       bool(first.get("journey_stage")),
                       f"stage={first.get('journey_stage')}")
            score = first.get("engagement_score", 0)
            print(f"  {INFO}  engagement_score = {score}")
            print(f"  {INFO}  customer_id      = {self.customer_id}")
        return ok

    def test_order_fulfilled(self) -> bool:
        self.section("3. Shopify order/fulfilled webhook (sets waybill)")
        order = {
            "id": 5001234567890,
            "order_number": 1042,
            "customer": {"id": 7001234567890, "phone": self.phone},
            "billing_address": {"phone": self.phone},
            "fulfillments": [
                {
                    "tracking_number": "AWB9876543210",
                    "tracking_company": "Delhivery",
                }
            ],
        }
        body_bytes = json.dumps(order, ensure_ascii=True).encode()
        sig = _shopify_hmac(body_bytes, SHOPIFY_SECRET)
        code, resp = post(
            self.base, "/api/shopify/webhook/order-fulfilled", order,
            headers={"X-Shopify-Hmac-Sha256": sig, "X-Shopify-Shop-Domain": self.shop},
        )
        self.check("Fulfilled webhook accepted (2xx)", 200 <= code < 300,
                   f"HTTP {code}: {str(resp)[:100]}")
        return True

    def test_delhivery_in_transit(self) -> bool:
        self.section("4. Delhivery webhook — in_transit (status=2)")
        payload = {
            "packages": [
                {
                    "waybill":        "AWB9876543210",
                    "status_code":    2,
                    "status":         "In Transit",
                    "location":       "Bangalore Hub",
                    "timestamp":      datetime.now(timezone.utc).isoformat(),
                }
            ]
        }
        body_bytes = json.dumps(payload, ensure_ascii=True).encode()
        sig = _delhivery_hmac(body_bytes, DELHIVERY_SECRET)
        code, resp = post(
            self.base, "/api/delhivery/webhook", payload,
            headers={"X-Delhivery-Signature": sig, "Content-Type": "application/json"},
        )
        self.check("Delhivery webhook accepted (2xx)", 200 <= code < 300,
                   f"HTTP {code}: {str(resp)[:100]}")

        # Check customer delivery_status
        time.sleep(0.3)
        _, cust = get(self.base, f"/api/journey/customers/{self.phone}",
                      params={"shop_domain": self.shop})
        orders = cust.get("orders", [{}])
        delivery_status = orders[0].get("delivery_status") if orders else None
        self.check("delivery_status updated",
                   "transit" in str(delivery_status or "").lower(),
                   f"delivery_status={delivery_status}")
        return True

    def test_delhivery_delivered(self) -> bool:
        self.section("5. Delhivery webhook — delivered (status=5)")
        payload = {
            "packages": [
                {
                    "waybill":        "AWB9876543210",
                    "status_code":    5,
                    "status":         "Delivered",
                    "location":       "Customer Address",
                    "timestamp":      datetime.now(timezone.utc).isoformat(),
                }
            ]
        }
        body_bytes = json.dumps(payload, ensure_ascii=True).encode()
        sig = _delhivery_hmac(body_bytes, DELHIVERY_SECRET)
        code, resp = post(
            self.base, "/api/delhivery/webhook", payload,
            headers={"X-Delhivery-Signature": sig},
        )
        self.check("Delivered webhook accepted (2xx)", 200 <= code < 300,
                   f"HTTP {code}: {str(resp)[:100]}")

        time.sleep(0.3)
        _, cust_resp = get(self.base, f"/api/journey/customers/{self.phone}",
                           params={"shop_domain": self.shop})
        orders = cust_resp.get("orders", [{}])
        first  = orders[0] if orders else {}
        self.check("delivery_status = delivered",
                   first.get("delivery_status") == "delivered",
                   f"delivery_status={first.get('delivery_status')}")
        self.check("delivered_at set",
                   bool(first.get("delivered_at")),
                   f"delivered_at={first.get('delivered_at')}")
        instant = resp.get("results", [{}])[0].get("instant_send", "")
        self.check("Day 5 instant send triggered",
                   instant not in ("", None),
                   f"instant_send={instant}")
        return True

    def test_whatsapp_click(self) -> bool:
        self.section("6. WhatsApp button click (tracking webhook)")
        code, resp = post(self.base, "/api/tracking/whatsapp-click", {
            "customer_phone": self.phone,
            "shop_domain":    self.shop,
            "template_name":  "delivered_review_request_v1",
            "journey_stage":  "delivered",
            "metadata":       {"button_text": "Write Review"},
        })
        self.check("Click tracked (2xx)", 200 <= code < 300,
                   f"HTTP {code}: {str(resp)[:80]}")

        time.sleep(0.3)
        _, cust_resp = get(self.base, f"/api/journey/customers/{self.phone}",
                           params={"shop_domain": self.shop})
        orders = cust_resp.get("orders", [{}])
        score = orders[0].get("engagement_score", 0) if orders else 0
        self.check("engagement_score > 0", float(score) > 0,
                   f"score={score}")
        print(f"  {INFO}  engagement_score after click = {score}")
        return True

    def test_whatsapp_reply(self) -> bool:
        self.section("7. WhatsApp reply (tracking webhook)")
        code, resp = post(self.base, "/api/tracking/whatsapp-reply", {
            "customer_phone": self.phone,
            "shop_domain":    self.shop,
            "template_name":  "delivered_review_request_v1",
            "journey_stage":  "delivered",
            "metadata":       {"reply_text": "Love it! ❤️"},
        })
        self.check("Reply tracked (2xx)", 200 <= code < 300,
                   f"HTTP {code}: {str(resp)[:80]}")

        time.sleep(0.3)
        _, cust_resp = get(self.base, f"/api/journey/customers/{self.phone}",
                           params={"shop_domain": self.shop})
        orders = cust_resp.get("orders", [{}])
        is_responsive = orders[0].get("is_responsive") if orders else None
        self.check("is_responsive = 1",
                   int(is_responsive or 0) == 1,
                   f"is_responsive={is_responsive}")
        return True

    def test_orchestrate_preview(self) -> bool:
        self.section("8. Orchestrate dry-run preview")
        code, resp = post(self.base, "/api/journey/orchestrate/preview", {},
                          params={"shop_domain": self.shop})
        self.check("Preview accepted (2xx)", 200 <= code < 300,
                   f"HTTP {code}: {str(resp)[:100]}")
        if 200 <= code < 300:
            print(f"  {INFO}  Cohort sizes:")
            cohorts = resp.get("cohorts", resp.get("stages", resp))
            if isinstance(cohorts, dict):
                for stage, size in cohorts.items():
                    print(f"       {stage}: {size}")
        return True

    def test_mark_reviewed(self) -> bool:
        self.section("9. Mark customer as reviewed")
        if not self.customer_id:
            print(f"  {WARN}  No customer_id, skipping")
            return True
        code, resp = post(
            self.base, f"/api/journey/customers/{self.customer_id}/mark-reviewed", {}
        )
        self.check("Mark reviewed (2xx)", 200 <= code < 300,
                   f"HTTP {code}: {str(resp)[:80]}")

        time.sleep(0.3)
        _, cust_resp = get(self.base, f"/api/journey/customers/{self.phone}",
                           params={"shop_domain": self.shop})
        orders = cust_resp.get("orders", [{}])
        score = orders[0].get("engagement_score", 0) if orders else 0
        self.check("engagement_score increased after review",
                   float(score) >= 50,
                   f"score={score}")
        print(f"  {INFO}  Final engagement_score = {score}")
        return True

    def test_stats(self) -> bool:
        self.section("10. Journey stats")
        code, resp = get(self.base, "/api/journey/stats",
                         params={"shop_domain": self.shop})
        self.check("Stats endpoint (2xx)", 200 <= code < 300,
                   f"HTTP {code}: {str(resp)[:100]}")
        if 200 <= code < 300:
            for key, val in resp.items():
                print(f"  {INFO}  {key}: {val}")
        return True

    def summary(self) -> bool:
        total = self.passed + self.failed
        print(f"\n{'═' * 60}")
        print(f"  Results: {self.passed}/{total} passed", end="")
        if self.failed:
            print(f"  |  {self.failed} FAILED ❌")
        else:
            print("  — all green ✅")
        print('═' * 60)
        return self.failed == 0


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="E2E WhatsApp journey test")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--phone",    default=DEFAULT_PHONE)
    parser.add_argument("--shop",     default=DEFAULT_SHOP)
    parser.add_argument("--cleanup",  action="store_true",
                        help="Delete test customer from DB after run")
    args = parser.parse_args()

    print(f"\n🧪  Pureleven WhatsApp Journey — E2E Test")
    print(f"    Server : {args.base_url}")
    print(f"    Phone  : {args.phone}")
    print(f"    Shop   : {args.shop}")

    if SHOPIFY_SECRET:
        print(f"    HMAC   : real (SHOPIFY_WEBHOOK_SECRET set)")
    else:
        print(f"    HMAC   : dev mode (no secret — server accepts all)")

    runner = TestRunner(args.base_url, args.phone, args.shop)

    if not runner.test_health():
        print(f"\n  ❌  Server not reachable at {args.base_url}")
        print(f"      Start it with: uvicorn app.main:app --reload --port 8000\n")
        sys.exit(1)

    runner.test_order_created()
    time.sleep(0.5)
    runner.test_inspect_customer()
    time.sleep(0.5)
    runner.test_order_fulfilled()     # sets waybill before Delhivery webhooks
    time.sleep(0.5)
    runner.test_delhivery_in_transit()
    time.sleep(0.5)
    runner.test_delhivery_delivered()
    time.sleep(0.5)
    runner.test_whatsapp_click()
    time.sleep(0.5)
    runner.test_whatsapp_reply()
    time.sleep(0.5)
    runner.test_orchestrate_preview()
    time.sleep(0.5)
    runner.test_mark_reviewed()
    time.sleep(0.5)
    runner.test_stats()

    if args.cleanup and runner.customer_id:
        print(f"\n  🧹  Cleanup: customer_id={runner.customer_id} (manual DB delete needed)")

    all_passed = runner.summary()
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
