#!/usr/bin/env python3
"""
Shopify Setup Script for Pure Leven CRM
- Registers all required webhooks
- Imports historical orders/customers into CRM

Usage:
  python3 scripts/shopify_setup.py --token YOUR_ADMIN_API_TOKEN [--import-orders]

Get token from: Shopify Admin → Settings → Apps → Develop apps → 
  Create/select app → Configuration → Admin API access token
  Required scopes: read_orders, read_customers, read_checkouts, write_webhooks
"""
import argparse
import json
import urllib.request
import urllib.error
import urllib.parse
import time
import sys

STORE = "rwxtic-gz.myshopify.com"
API_VERSION = "2024-10"
WEBHOOK_BASE = "https://track.pureleven.com/api/crm/webhooks/shopify"
CRM_API_BASE = "https://track.pureleven.com/api/crm"
CRM_API_KEY = "9b1c4d602ff914762204dae7331174634c92445519aaaa95e2307107de09439e"

REQUIRED_WEBHOOKS = [
    {"topic": "orders/paid",        "address": f"{WEBHOOK_BASE}/order-paid"},
    {"topic": "orders/cancelled",   "address": f"{WEBHOOK_BASE}/order-cancelled"},
    {"topic": "orders/fulfilled",   "address": f"{WEBHOOK_BASE}/order-fulfilled"},
    {"topic": "carts/create",       "address": f"{WEBHOOK_BASE}/cart-create"},
    {"topic": "carts/update",       "address": f"{WEBHOOK_BASE}/cart-update"},
    {"topic": "checkouts/create",   "address": f"{WEBHOOK_BASE}/checkout-create"},
    {"topic": "checkouts/update",   "address": f"{WEBHOOK_BASE}/checkout-update"},
    {"topic": "customers/create",   "address": f"{WEBHOOK_BASE}/customer-create"},
    {"topic": "customers/update",   "address": f"{WEBHOOK_BASE}/customer-update"},
]


def shopify_request(token, path, method="GET", data=None):
    url = f"https://{STORE}/admin/api/{API_VERSION}/{path}"
    headers = {
        "X-Shopify-Access-Token": token,
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()[:500]}, e.code


def crm_shopify_event(topic, data):
    """Send a Shopify-format event to the CRM webhook endpoint."""
    url = f"{CRM_API_BASE}/webhooks/shopify"
    headers = {
        "Authorization": f"Bearer {CRM_API_KEY}",
        "Content-Type": "application/json",
        "X-Shopify-Topic": topic,
        "X-Shopify-Shop-Domain": f"{STORE}",
    }
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return {"error": e.read().decode()[:300]}, e.code


def register_webhooks(token):
    print("\n📡 Registering Shopify Webhooks...\n")

    # Get existing webhooks to avoid duplicates
    existing, _ = shopify_request(token, "webhooks.json?limit=250")
    existing_topics = set()
    if "webhooks" in existing:
        for wh in existing["webhooks"]:
            existing_topics.add(wh["topic"])
            print(f"  ℹ️  Already exists: {wh['topic']} → {wh['address']}")

    created = 0
    for wh in REQUIRED_WEBHOOKS:
        topic = wh["topic"]
        if topic in existing_topics:
            print(f"  ✓ Already registered: {topic}")
            continue

        result, status = shopify_request(token, "webhooks.json", method="POST", data={
            "webhook": {
                "topic": topic,
                "address": wh["address"],
                "format": "json",
            }
        })

        if status in (200, 201) and "webhook" in result:
            wh_id = result["webhook"]["id"]
            print(f"  ✅ Created: {topic} (ID: {wh_id})")
            created += 1
        else:
            print(f"  ❌ Failed: {topic} — {status}: {result.get('error', result)[:200]}")

    print(f"\n✅ Webhook registration complete: {created} new, {len(existing_topics)} existing\n")


def import_historical_orders(token, days=365):
    print(f"\n📦 Importing historical orders (last {days} days)...\n")

    from datetime import datetime, timedelta
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")

    result, status = shopify_request(
        token,
        f"orders.json?status=any&financial_status=paid&limit=250&created_at_min={since}"
    )
    if status != 200 or "orders" not in result:
        print(f"  ❌ Failed to fetch orders: {status} {result}")
        return

    orders = result["orders"]
    print(f"  Fetched {len(orders)} paid orders\n")

    imported = 0
    errors = 0
    for order in orders:
        # POST as Shopify webhook format
        resp, s = crm_shopify_event("orders/paid", order)
        if s == 200:
            imported += 1
            if imported % 10 == 0:
                print(f"  ... {imported}/{len(orders)} imported")
        else:
            errors += 1
            if errors <= 3:
                print(f"  Warning: order #{order.get('order_number')} → {s}: {resp.get('error', resp)[:100]}")

    print(f"\n  ✅ Imported {imported} orders ({errors} errors)")


def import_customers(token):
    print("\n👥 Importing Shopify customers...\n")

    result, status = shopify_request(
        token,
        "customers.json?limit=250&fields=id,email,phone,first_name,last_name,orders_count,created_at,tags,updated_at"
    )
    if status != 200 or "customers" not in result:
        print(f"  ❌ Failed: {status} {result}")
        return

    customers = result["customers"]
    print(f"  Found {len(customers)} customers")

    imported = 0
    for c in customers:
        resp, s = crm_shopify_event("customers/create", c)
        if s == 200:
            imported += 1
        else:
            print(f"    Warning: {c.get('email')} → {s}: {resp}")

    print(f"  ✅ Imported {imported}/{len(customers)} customers\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Shopify CRM Setup")
    parser.add_argument("--token", required=True, help="Shopify Admin API access token")
    parser.add_argument("--import-orders", action="store_true", help="Import historical orders")
    parser.add_argument("--import-customers", action="store_true", help="Import customers")
    parser.add_argument("--days", type=int, default=365, help="Days of history to import (default: 365)")
    args = parser.parse_args()

    print(f"\n🛍️  Pure Leven Shopify CRM Setup")
    print(f"Store: {STORE}")
    print(f"API Version: {API_VERSION}\n")

    # Test token
    me, s = shopify_request(args.token, "shop.json")
    if s != 200:
        print(f"❌ Invalid token or insufficient permissions: {s} {me}")
        sys.exit(1)
    shop_name = me.get("shop", {}).get("name", "Unknown")
    print(f"✅ Connected to Shopify store: {shop_name}\n")

    # Register webhooks
    register_webhooks(args.token)

    if args.import_orders:
        import_historical_orders(args.token, days=args.days)

    if args.import_customers:
        import_customers(args.token)

    print("\n🎉 Setup complete!")
    print("\nNext steps:")
    print("1. Webhooks are now registered — new orders/carts will flow into CRM automatically")
    print("2. Run with --import-orders --days 365 to import historical order data")
    print("3. After import, the replenishment and winback audiences will have data\n")
