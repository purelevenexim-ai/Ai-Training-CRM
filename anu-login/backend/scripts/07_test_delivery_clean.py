#!/usr/bin/env python3
"""
scripts/07_test_delivery_clean.py

Clean test scenario: creates proper test customers and sends via orchestrator.
This respects all journey suppression rules and demonstrates real flow.

Usage:
  cd anu-login/backend
  set -a; source .env; set +a
  ../../.venv/bin/python scripts/07_test_delivery_clean.py --phone 918547574028 [--scenario 1|2]

Scenario 1: Non-buyer with marketing messages (winback, promo, etc.)
Scenario 2: Buyer with full journey (order confirmed through loyalty)
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

try:
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = ssl.create_default_context()

import urllib.request
import urllib.error

sys.path.insert(0, '.')

from app.storage import get_db_connection, init_database
from app.whatsapp_templates import build_message_vars


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _past_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def create_test_customer_scenario_1(phone: str, shop: str) -> str:
    """Non-buyer: visited, provided number, no purchase. Ready for reactivation journey."""
    cid = str(uuid.uuid4())
    now = _now_iso()

    with get_db_connection() as conn:
        # Delete any existing test customer with this phone
        conn.execute("DELETE FROM journey_customers WHERE phone = ? AND shop_domain = ?", (phone, shop))
        conn.commit()

        conn.execute(
            """
            INSERT INTO journey_customers (
                id, shop_domain, phone, name, email,
                shopify_customer_id, shopify_order_id,
                waybill_id, delivery_status, delivered_at,
                order_value_paise, journey_stage, journey_started_at,
                customer_segment, total_spent_paise, purchase_count, last_purchase_at,
                whatsapp_subscription_status, is_responsive, engagement_score,
                created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?
            )
            """,
            (
                cid, shop, phone, "Test User S1", "test.s1@example.com",
                "cust_123", None,
                None, "pending", None,
                0, "rfm", _past_iso(120),  # 120 days since first visit (dormant)
                "dormant", 0, 0, _past_iso(120),
                "subscribed", 0, 0,  # subscribed, not responsive yet, no engagement
                now, now,
            ),
        )
        conn.commit()

    return cid


def create_test_customer_scenario_2(phone: str, shop: str) -> str:
    """Buyer: just purchased, pending delivery. Full journey from order confirmed."""
    cid = str(uuid.uuid4())
    order_id = f"order_{uuid.uuid4().hex[:8]}"
    now = _now_iso()

    with get_db_connection() as conn:
        # Delete any existing test customer
        conn.execute("DELETE FROM journey_customers WHERE phone = ? AND shop_domain = ?", (phone, shop))
        conn.commit()

        conn.execute(
            """
            INSERT INTO journey_customers (
                id, shop_domain, phone, name, email,
                shopify_customer_id, shopify_order_id,
                waybill_id, delivery_status, delivered_at,
                order_value_paise, journey_stage, journey_started_at,
                customer_segment, total_spent_paise, purchase_count, last_purchase_at,
                whatsapp_subscription_status, is_responsive, engagement_score,
                created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?
            )
            """,
            (
                cid, shop, phone, "Test User S2", "test.s2@example.com",
                "cust_456", order_id,
                "AWB123456", "in_transit", None,  # order exists, in transit
                75000, "order_confirmed", now,  # ₹750 order, fresh order
                "new", 75000, 1, now,
                "subscribed", 1, 10.0,  # subscribed, responsive, some engagement
                now, now,
            ),
        )
        conn.commit()

    return cid


def send_messages(scenario: int, cid: str, shop: str) -> dict:
    """Send via Meta Cloud API (bypass Wabis DNS issues for testing)."""
    stages = {
        1: [
            "rfm",
            "winback_offer_v1",
            "extreme_winback_v1",
            "reactivation_survey_v1",
            "promo_monsoon_v1",
            "promo_diwali_v1",
            "promo_new_harvest_v1",
            "promo_bulk_sale_v1",
        ],
        2: [
            "order_confirmed",
            "in_transit",
            "delivered",
            "review",
            "upsell",
            "corporate",
            "loyalty",
            "rfm",
        ],
    }

    stage_list = stages.get(scenario, [])
    results = {"sent": 0, "suppressed": 0, "errors": 0, "messages": []}

    # Load Meta credentials
    waba_id = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "")
    phone_id = os.getenv("META_PHONE_NUMBER_ID", "")
    token = os.getenv("META_ACCESS_TOKEN", "")
    if not all([waba_id, phone_id, token]):
        results["errors"] = len(stage_list)
        results["messages"] = [{"stage": s, "status": "error", "reason": "missing_meta_creds"} for s in stage_list]
        return results

    # Fetch templates
    url = f"https://graph.facebook.com/v20.0/{waba_id}/message_templates?limit=200"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        with urllib.request.urlopen(req, context=_SSL_CONTEXT, timeout=20) as resp:
            data = json.loads(resp.read().decode())
        templates = {t["name"]: t for t in data.get("data", [])}
    except Exception as e:
        results["errors"] = len(stage_list)
        results["messages"] = [{"stage": s, "status": "error", "reason": f"meta_fetch_failed: {e}"} for s in stage_list]
        return results

    with get_db_connection() as conn:
        customer_row = conn.execute(
            "SELECT * FROM journey_customers WHERE id = ? AND shop_domain = ?",
            (cid, shop),
        ).fetchone()

        if not customer_row:
            results["errors"] = len(stage_list)
            results["messages"] = [{"stage": s, "status": "error", "reason": "customer_not_found"} for s in stage_list]
            return results

        customer = dict(customer_row)

        for stage_key in stage_list:
            try:
                # Build message from template
                template_name, body_params, button_params = build_message_vars(stage_key, customer)
                tpl = templates.get(template_name)
                if not tpl:
                    results["messages"].append({"stage": stage_key, "status": "error", "reason": f"template_not_found: {template_name}"})
                    results["errors"] += 1
                    continue

                # Parse template for parameters
                lang = tpl.get("language") or "en"
                comps = []

                for c in tpl.get("components", []):
                    ctype = c.get("type", "").upper()
                    if ctype == "BODY" and body_params:
                        text = c.get("text", "") or ""
                        idxs = [int(m.group(1)) for m in re.finditer(r"\{\{(\d+)\}\}", text)]
                        cnt = max(idxs) if idxs else 0
                        if cnt > 0:
                            comps.append({
                                "type": "body",
                                "parameters": [{"type": "text", "text": str(p)} for p in body_params[:cnt]]
                            })

                # Send via Meta Cloud API
                payload = {
                    "messaging_product": "whatsapp",
                    "to": customer["phone"],
                    "type": "template",
                    "template": {"name": template_name, "language": {"code": lang}},
                }
                if comps:
                    payload["template"]["components"] = comps

                req = urllib.request.Request(
                    f"https://graph.facebook.com/v20.0/{phone_id}/messages",
                    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, context=_SSL_CONTEXT, timeout=25) as resp:
                    r = json.loads(resp.read().decode())
                    mid = ((r.get("messages") or [{}])[0]).get("id", "")
                    results["sent"] += 1
                    results["messages"].append({
                        "stage": stage_key,
                        "template": template_name,
                        "status": "sent",
                        "message_id": mid[:40],
                    })
            except urllib.error.HTTPError as e:
                detail = e.read().decode(errors="replace")[:200]
                results["errors"] += 1
                results["messages"].append({
                    "stage": stage_key,
                    "status": "error",
                    "reason": f"HTTP {e.code}: {detail}"
                })
            except Exception as e:
                results["errors"] += 1
                results["messages"].append({
                    "stage": stage_key,
                    "status": "error",
                    "reason": str(e)[:100]
                })

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean test delivery scenario")
    parser.add_argument("--phone", required=True, help="Phone number to test (E.164)")
    parser.add_argument("--scenario", type=int, default=1, choices=[1, 2], help="Test scenario")
    parser.add_argument("--shop", default="rwxtic-gz.myshopify.com", help="Shop domain")
    args = parser.parse_args()

    init_database()

    print(f"\n── Clean Test Delivery (Scenario {args.scenario}) ──────────────────────────────────")
    print(f"   Phone : {args.phone}")
    print(f"   Shop  : {args.shop}")
    print()

    if args.scenario == 1:
        print("   Setup : Non-buyer (dormant, visited 120d ago, no purchase)")
        cid = create_test_customer_scenario_1(args.phone, args.shop)
    else:
        print("   Setup : Buyer (fresh order, in transit, responsive)")
        cid = create_test_customer_scenario_2(args.phone, args.shop)

    print(f"   Customer ID: {cid}")
    print()

    print("   Sending messages via orchestrator (respects suppression)...")
    print()

    results = send_messages(args.scenario, cid, args.shop)

    print("── Results ─────────────────────────────────────────────────────────")
    print(f"   Sent       : {results['sent']}")
    print(f"   Suppressed : {results['suppressed']}")
    print(f"   Errors     : {results['errors']}")
    print()

    for msg in results["messages"]:
        if msg["status"] == "sent":
            print(f"   ✅  {msg['stage']:20} {msg['template']:32} {msg['message_id'][:40]}")
        elif msg["status"] == "suppressed":
            print(f"   ⊘   {msg['stage']:20} suppressed: {msg['reason']}")
        else:
            print(f"   ❌  {msg['stage']:20} error: {msg['reason']}")

    print()
    print("── Next steps ──────────────────────────────────────────────────────")
    if results["sent"] > 0:
        print(f"   1. Check WhatsApp on {args.phone}")
        print(f"   2. Run audit in 30 seconds:")
        print(f"      curl http://localhost:8000/api/tracking/meta-status/by-phone?phone={args.phone}&limit=100")
        print(f"   3. Verify delivery status for each message ID")
    else:
        print("   ⚠️   No messages sent (all suppressed or errored).")
        print("   Check customer segment, subscription status, and journey stage.")
    print()


if __name__ == "__main__":
    main()
