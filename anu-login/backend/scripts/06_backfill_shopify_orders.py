#!/usr/bin/env python3
"""
scripts/06_backfill_shopify_orders.py

Fetches historical Shopify orders and seeds journey_customers so the daily
orchestrator can start messaging existing buyers immediately.

Usage (from anu-login/backend):
  python scripts/06_backfill_shopify_orders.py [--days 90] [--dry-run] [--limit 250]

Options:
  --days N    How many days back to import (default: 90)
  --dry-run   Print what would be imported, don't write to DB
  --limit N   Max orders per Shopify page (max 250, default: 250)

Requirements: SHOPIFY_SHOP_DOMAIN, SHOPIFY_ADMIN_API_TOKEN in environment.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import ssl
import sys
import uuid
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlencode, urlparse

try:
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = ssl.create_default_context()

# ── Allow running from backend root ─────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.storage import get_db_connection, init_database  # noqa: E402


# ── Shopify helpers ─────────────────────────────────────────────────────────

def _next_page_info(link_header: str | None) -> str | None:
    if not link_header:
        return None

    for part in link_header.split(","):
        if 'rel="next"' not in part:
            continue
        match = re.search(r"<([^>]+)>", part)
        if not match:
            continue
        page_values = parse_qs(urlparse(match.group(1)).query).get("page_info") or []
        if page_values:
            return page_values[0]
    return None


def shopify_get(path: str, params: dict) -> tuple[dict, str | None]:
    shop   = os.environ["SHOPIFY_SHOP_DOMAIN"]
    token  = os.environ["SHOPIFY_ADMIN_API_TOKEN"]
    ver    = os.getenv("ANU_LOGIN_SHOPIFY_API_VERSION", "2026-07")
    qs     = urlencode(params)
    url    = f"https://{shop}/admin/api/{ver}/{path}?{qs}"
    req    = Request(url, headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"})
    with urlopen(req, timeout=30, context=_SSL_CONTEXT) as resp:
        data = json.loads(resp.read())
        return data, _next_page_info(resp.headers.get("Link"))


def normalize_phone(raw: str | None) -> str:
    if not raw:
        return ""
    digits = "".join(c for c in raw if c.isdigit())
    if len(digits) == 10:
        digits = "91" + digits
    return digits


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Delivery status inference ────────────────────────────────────────────────

def infer_delivery_status(order: dict) -> tuple[str, str | None, str | None]:
    """Return (delivery_status, delivered_at, waybill_id)."""
    fulfillments = order.get("fulfillments") or []
    if not fulfillments:
        return "pending", None, None

    latest = fulfillments[-1]
    shopify_status = latest.get("shipment_status") or latest.get("status") or ""
    delivered_at = None
    waybill_id = None

    tracking_numbers = latest.get("tracking_numbers") or []
    if tracking_numbers:
        waybill_id = tracking_numbers[0]

    if shopify_status in ("delivered",):
        delivery_status = "delivered"
        delivered_at = latest.get("updated_at") or order.get("updated_at")
    elif shopify_status in ("in_transit", "out_for_delivery", "confirmed"):
        delivery_status = "in_transit"
    elif latest.get("status") == "success":
        # Shopify shows "success" when fulfilled; treat as delivered if older than 5 days
        created = order.get("created_at") or ""
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(created.replace("Z", "+00:00"))).days
        except (ValueError, TypeError):
            age = 0
        if age >= 5:
            delivery_status = "delivered"
            delivered_at = latest.get("updated_at") or order.get("updated_at")
        else:
            delivery_status = "in_transit"
    else:
        delivery_status = "pending"

    return delivery_status, delivered_at, waybill_id


# ── Segment inference ────────────────────────────────────────────────────────

def infer_segment(purchase_count: int, total_spent_paise: int, last_purchase_iso: str) -> str:
    try:
        age_days = (datetime.now(timezone.utc) - datetime.fromisoformat(
            last_purchase_iso.replace("Z", "+00:00")
        )).days
    except (ValueError, TypeError):
        age_days = 0

    spent = total_spent_paise / 100  # to rupees
    if spent >= 5000 and purchase_count >= 5 and age_days < 30:
        return "vip"
    if purchase_count >= 2 and age_days < 60:
        return "repeat_buyer"
    if age_days > 120 and purchase_count < 2:
        return "dormant"
    if age_days > 90:
        return "at_risk"
    return "new"


# ── Upsert one order ─────────────────────────────────────────────────────────

def upsert_order(conn, order: dict, shop: str, dry_run: bool) -> str:
    """Insert or skip a journey_customer row. Returns 'inserted'|'skipped'|'exists'."""
    order_id     = str(order.get("id") or "")
    customer_rec = order.get("customer") or {}
    cust_id      = str(customer_rec.get("id") or "")
    name         = ((customer_rec.get("first_name") or "") + " " + (customer_rec.get("last_name") or "")).strip()
    email        = customer_rec.get("email") or ""
    phone        = normalize_phone(
        (order.get("shipping_address") or {}).get("phone")
        or customer_rec.get("phone")
        or order.get("phone")
    )

    if not phone:
        return "skipped"   # Can't WhatsApp without a phone number

    # Already imported?
    existing = conn.execute(
        "SELECT id FROM journey_customers WHERE shop_domain = ? AND shopify_order_id = ?",
        (shop, order_id),
    ).fetchone()
    if existing:
        return "exists"

    # Financials
    try:
        order_value_paise = int(float(str(order.get("total_price") or "0")) * 100)
    except (ValueError, TypeError):
        order_value_paise = 0

    try:
        total_spent_paise = int(float(str(customer_rec.get("total_spent") or "0")) * 100)
    except (ValueError, TypeError):
        total_spent_paise = order_value_paise

    purchase_count = int(customer_rec.get("orders_count") or 1)
    last_purchase  = order.get("created_at") or now_iso()

    # Delivery
    delivery_status, delivered_at, waybill_id = infer_delivery_status(order)

    # Journey stage — where in the funnel are they?
    if delivery_status == "delivered":
        journey_stage = "delivered"
    elif delivery_status == "in_transit":
        journey_stage = "in_transit"
    else:
        journey_stage = "order_confirmed"

    # Segment
    segment = infer_segment(purchase_count, total_spent_paise, last_purchase)

    customer_id = str(uuid.uuid4())
    now = now_iso()

    if dry_run:
        return "dry_run"

    conn.execute(
        """
        INSERT INTO journey_customers (
            id, shop_domain, phone, name, email,
            shopify_customer_id, shopify_order_id,
            waybill_id, delivery_status, delivered_at,
            order_value_paise, journey_stage, journey_started_at,
            customer_segment, total_spent_paise, purchase_count, last_purchase_at,
            created_at, updated_at
        ) VALUES (
            ?,?,?,?,?,
            ?,?,
            ?,?,?,
            ?,?,?,
            ?,?,?,?,
            ?,?
        )
        """,
        (
            customer_id, shop, phone, name, email,
            cust_id, order_id,
            waybill_id, delivery_status, delivered_at,
            order_value_paise, journey_stage, last_purchase,
            segment, total_spent_paise, purchase_count, last_purchase,
            now, now,
        ),
    )
    return "inserted"


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill Shopify orders into journey_customers")
    parser.add_argument("--days",    type=int, default=90,  help="Days of history to import (default: 90)")
    parser.add_argument("--limit",   type=int, default=250, help="Orders per page (max 250)")
    parser.add_argument("--dry-run", action="store_true",   help="Print only, don't write to DB")
    args = parser.parse_args()

    shop = os.getenv("SHOPIFY_SHOP_DOMAIN", "")
    if not shop or not os.getenv("SHOPIFY_ADMIN_API_TOKEN"):
        print("❌  SHOPIFY_SHOP_DOMAIN and SHOPIFY_ADMIN_API_TOKEN must be set in environment")
        sys.exit(1)

    since = (datetime.now(timezone.utc) - timedelta(days=args.days)).isoformat()

    print(f"\n── Backfill Shopify Orders ── {'(DRY RUN)' if args.dry_run else ''}")
    print(f"   Shop : {shop}")
    print(f"   Since: {since[:10]} ({args.days} days)")
    print()

    init_database()

    inserted = exists = skipped = errors = 0
    page_info = None
    page = 1

    while True:
        params: dict = {"limit": min(args.limit, 250), "status": "any",
                        "created_at_min": since, "fields":
                        "id,order_number,created_at,updated_at,total_price,"
                        "customer,phone,shipping_address,fulfillments"}
        if page_info:
            params = {"limit": params["limit"], "page_info": page_info}

        try:
            data, next_page_info = shopify_get("orders.json", params)
        except HTTPError as exc:
            print(f"❌  Shopify API error: {exc.code} — {exc.read().decode()}")
            break
        except Exception as exc:
            print(f"❌  Request failed: {exc}")
            break

        orders = data.get("orders") or []
        if not orders:
            break

        print(f"   Page {page}: {len(orders)} orders …", end=" ")

        with get_db_connection() as conn:
            for order in orders:
                try:
                    result = upsert_order(conn, order, shop, args.dry_run)
                except Exception as exc:
                    errors += 1
                    print(f"\n   ⚠️   order {order.get('id')}: {exc}")
                    continue

                if result == "inserted":
                    inserted += 1
                elif result == "exists":
                    exists += 1
                elif result in ("skipped", "dry_run"):
                    skipped += 1

            if not args.dry_run:
                conn.commit()

        print(f"+{inserted} new so far")

        if not next_page_info:
            break
        page += 1
        page_info = next_page_info

    print()
    print("── Summary ──────────────────────────────────────────────────────────")
    print(f"   Inserted : {inserted}")
    print(f"   Skipped  : {skipped}  (no phone / dry-run)")
    print(f"   Already  : {exists}   (already in journey_customers)")
    print(f"   Errors   : {errors}")
    print()
    if not args.dry_run and inserted > 0:
        print(f"   ✅  {inserted} customers seeded. Daily orchestrator will pick them up at 4:30am UTC.")
    if args.dry_run:
        print("   ℹ️   Dry run — nothing written. Re-run without --dry-run to import.")


if __name__ == "__main__":
    main()
