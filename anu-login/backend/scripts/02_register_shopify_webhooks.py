#!/usr/bin/env python3
"""
scripts/02_register_shopify_webhooks.py

Register 3 Shopify order webhooks that trigger the WhatsApp journey.
Idempotent: checks existing webhooks first, skips already-registered ones.

Usage:
  cd anu-login/backend
  python scripts/02_register_shopify_webhooks.py

Required env vars:
  SHOPIFY_SHOP_DOMAIN      - e.g. rwxtic-gz.myshopify.com
  SHOPIFY_ADMIN_API_TOKEN  - <SHOPIFY_ADMIN_TOKEN>  (Staff Token, not Shopify API key)
  PUBLIC_BASE_URL          - e.g. https://your-tunnel.loca.lt
  ANU_LOGIN_SHOPIFY_API_VERSION - e.g. 2026-07  (defaults to 2026-07)

How to get SHOPIFY_ADMIN_API_TOKEN:
  Shopify Admin → Settings → Apps & sales channels → Develop apps
  → Create app → Configure Admin API scopes: read_orders, write_orders
  → Install app → Copy Admin API access token
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

# ─── Config ──────────────────────────────────────────────────────────────────

SHOP_DOMAIN   = os.getenv("SHOPIFY_SHOP_DOMAIN", "").strip()
API_TOKEN     = os.getenv("SHOPIFY_ADMIN_API_TOKEN", "").strip()
API_VERSION   = os.getenv("ANU_LOGIN_SHOPIFY_API_VERSION", "2026-07").strip()
PUBLIC_BASE   = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

WEBHOOKS_TO_REGISTER = [
    {
        "topic":   "orders/create",
        "address": f"{PUBLIC_BASE}/api/shopify/webhook/order-created",
        "format":  "json",
        "note":    "Triggers Day 1 order_confirmed_v1 message",
    },
    {
        "topic":   "orders/paid",
        "address": f"{PUBLIC_BASE}/api/shopify/webhook/order-paid",
        "format":  "json",
        "note":    "Awards +50 engagement points on payment",
    },
    {
        "topic":   "orders/fulfilled",
        "address": f"{PUBLIC_BASE}/api/shopify/webhook/order-fulfilled",
        "format":  "json",
        "note":    "Links waybill + triggers Day 2 delivery_begun_v1 message",
    },
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _base_url() -> str:
    return f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}"


def _headers() -> dict:
    return {
        "X-Shopify-Access-Token": API_TOKEN,
        "Content-Type": "application/json",
    }


def _get(path: str) -> dict:
    req = urllib.request.Request(f"{_base_url()}{path}", headers=_headers(), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return {"error": exc.code, "detail": exc.read().decode("utf-8", errors="replace")}


def _post(path: str, body: dict) -> dict:
    data = json.dumps(body, ensure_ascii=True).encode()
    req  = urllib.request.Request(
        f"{_base_url()}{path}", data=data, headers=_headers(), method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return {"error": exc.code, "detail": exc.read().decode("utf-8", errors="replace")}


def _delete(path: str) -> int:
    req = urllib.request.Request(f"{_base_url()}{path}", headers=_headers(), method="DELETE")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    # Preflight checks
    errors = []
    if not SHOP_DOMAIN:
        errors.append("SHOPIFY_SHOP_DOMAIN is not set")
    if not API_TOKEN:
        errors.append("SHOPIFY_ADMIN_API_TOKEN is not set")
    if not PUBLIC_BASE:
        errors.append("PUBLIC_BASE_URL is not set")
    if errors:
        print("❌  Missing required env vars:")
        for e in errors:
            print(f"    • {e}")
        sys.exit(1)

    print(f"\n🛍️   Shop     : {SHOP_DOMAIN}")
    print(f"🌐  Callback  : {PUBLIC_BASE}")
    print(f"📅  API ver   : {API_VERSION}\n")

    # ── Step 1: List existing webhooks ────────────────────────────────────────
    print("── Existing webhooks ─────────────────────────────────────────────")
    resp = _get("/webhooks.json")
    if "error" in resp:
        print(f"  ❌  Cannot list webhooks: {resp}")
        sys.exit(1)

    existing = resp.get("webhooks", [])
    existing_by_topic: dict[str, dict] = {}
    for w in existing:
        existing_by_topic[w["topic"]] = w
        print(f"  id={w['id']}  {w['topic']:25s}  {w['address']}")
    if not existing:
        print("  (none registered)")

    # ── Step 2: Register / update each webhook ───────────────────────────────
    print("\n── Registering webhooks ──────────────────────────────────────────")
    for wh in WEBHOOKS_TO_REGISTER:
        topic = wh["topic"]
        addr  = wh["address"]
        note  = wh["note"]

        if topic in existing_by_topic:
            existing_addr = existing_by_topic[topic]["address"]
            if existing_addr == addr:
                print(f"  ✅  {topic:25s}  already registered  ({addr})")
                continue
            else:
                # Delete old one and re-register
                old_id = existing_by_topic[topic]["id"]
                print(f"  🔄  {topic:25s}  replacing old webhook (id={old_id})")
                _delete(f"/webhooks/{old_id}.json")

        result = _post("/webhooks.json", {"webhook": {"topic": topic, "address": addr, "format": "json"}})
        if "error" in result:
            print(f"  ❌  {topic:25s}  FAILED: {result['detail'][:120]}")
        else:
            wid = result.get("webhook", {}).get("id", "?")
            print(f"  ✅  {topic:25s}  id={wid}  ({note})")

    # ── Step 3: Retrieve SHOPIFY_WEBHOOK_SECRET ───────────────────────────────
    print("\n── Retrieving webhook secret ─────────────────────────────────────")
    print("  After your first real order webhook fires, Shopify sends an")
    print("  X-Shopify-Hmac-Sha256 header. You can also find the secret:")
    print()
    print("  1. Shopify Admin → Settings → Notifications → Webhooks")
    print("  2. Copy the 'Secret' shown at the bottom of the page")
    print("  3. Add to your .env: SHOPIFY_WEBHOOK_SECRET=<secret>")
    print()
    print("  ⚠️  Without this, HMAC validation is DISABLED (dev mode only!)")
    print("      Set SHOPIFY_WEBHOOK_SECRET before going live.\n")


if __name__ == "__main__":
    main()
