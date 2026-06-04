"""
Phase 5 — Shopify Sync Service

Handles:
1. Real-time webhook payloads (customers/create, customers/update,
   orders/create, orders/paid, orders/fulfilled)
2. Historical backfill via Shopify Admin REST API
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from typing import Any

from app.storage import get_connection
from app.services.customer_unification_service import upsert_customer, sync_order_stats
from app.services.event_tracking_service import log_event

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_sync(sync_type: str, event_type: str | None, shopify_id: str | None,
              customer_email: str | None, status: str, payload: dict,
              error_reason: str | None = None):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO shopify_sync_log
                (id, sync_type, event_type, shopify_id, customer_email,
                 status, error_reason, payload_json, created_at)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                str(uuid.uuid4()), sync_type, event_type, shopify_id, customer_email,
                status, error_reason,
                json.dumps({k: v for k, v in payload.items() if k not in ("line_items",)})[:4000],
                _now(),
            ),
        )


# ─── Webhook Handlers ────────────────────────────────────────────────────────

def sync_customer_webhook(payload: dict) -> dict:
    """Process customers/create or customers/update webhook."""
    email = (payload.get("email") or "").strip().lower()
    if not email:
        return {"status": "skipped", "reason": "no email"}
    phone = payload.get("phone") or (payload.get("default_address") or {}).get("phone")
    first_name = payload.get("first_name") or ""
    last_name = payload.get("last_name") or ""
    shopify_customer_id = str(payload.get("id", ""))
    tags = [t.strip() for t in (payload.get("tags") or "").split(",") if t.strip()]
    email_opted = payload.get("email_marketing_consent", {}).get("state") in ("subscribed", "implicit")

    try:
        customer = upsert_customer(
            email=email,
            phone=phone,
            name=f"{first_name} {last_name}".strip() or None,
            first_name=first_name or None,
            last_name=last_name or None,
            shopify_customer_id=shopify_customer_id,
            tags=tags,
            source="shopify_webhook",
            email_opted_in=email_opted,
        )
        _log_sync("webhook", "customer", shopify_customer_id, email, "ok", payload)
        return {"status": "ok", "customer_id": customer["id"]}
    except Exception as exc:
        _log_sync("webhook", "customer", shopify_customer_id, email, "error", payload, str(exc))
        raise


def sync_order_webhook(payload: dict, trigger_journeys: bool = True) -> dict:
    """Process orders/create or orders/paid webhook."""
    customer_info = payload.get("customer") or {}
    email = (
        payload.get("email") or customer_info.get("email") or ""
    ).strip().lower()
    if not email:
        return {"status": "skipped", "reason": "no email"}

    shopify_order_id = str(payload.get("id", ""))
    order_name = payload.get("name", "")
    total_price = float(payload.get("total_price") or 0)
    financial_status = payload.get("financial_status", "")
    fulfillment_status = payload.get("fulfillment_status") or "unfulfilled"
    shopify_customer_id = str(customer_info.get("id", "") or payload.get("customer_id", "") or "")
    line_items = payload.get("line_items", [])
    created_at_shopify = payload.get("created_at", _now())
    updated_at_shopify = payload.get("updated_at", _now())

    # Upsert to shopify_orders
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO shopify_orders
                (id, shopify_order_id, customer_email, shopify_customer_id,
                 order_name, total_price, financial_status, fulfillment_status,
                 line_items_json, created_at_shopify, updated_at_shopify, synced_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(shopify_order_id) DO UPDATE SET
                financial_status = excluded.financial_status,
                fulfillment_status = excluded.fulfillment_status,
                updated_at_shopify = excluded.updated_at_shopify,
                synced_at = excluded.synced_at
            """,
            (
                str(uuid.uuid4()), shopify_order_id, email, shopify_customer_id,
                order_name, total_price, financial_status, fulfillment_status,
                json.dumps([{"title": li.get("title"), "quantity": li.get("quantity"),
                             "price": li.get("price")} for li in line_items]),
                created_at_shopify, updated_at_shopify, _now(),
            ),
        )

    # Update customer aggregate stats
    try:
        with get_connection() as conn:
            agg = conn.execute(
                """
                SELECT COUNT(*) as total_orders,
                       COALESCE(SUM(total_price), 0) as total_spent,
                       MAX(created_at_shopify) as last_order_date
                FROM shopify_orders WHERE customer_email = ?
                """,
                (email,),
            ).fetchone()
        sync_order_stats(
            email,
            total_orders=agg["total_orders"],
            total_spent=agg["total_spent"],
            last_order_date=agg["last_order_date"],
        )
    except Exception as exc:
        logger.warning("sync_order_stats failed for %s: %s", email, exc)

    # Trigger journey on order_created
    if trigger_journeys and financial_status in ("paid", "pending"):
        _maybe_trigger_journey("order_created", email, {
            "order_name": order_name, "total_price": total_price,
        })

    _log_sync("webhook", "order", shopify_order_id, email, "ok", payload)
    return {"status": "ok", "order_id": shopify_order_id}


def sync_fulfillment_webhook(payload: dict) -> dict:
    """Process orders/fulfilled / fulfillment_events webhook."""
    order_id = str(payload.get("order_id") or payload.get("id", ""))

    with get_connection() as conn:
        row = conn.execute(
            "SELECT customer_email FROM shopify_orders WHERE shopify_order_id = ?", (order_id,)
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE shopify_orders SET fulfillment_status = 'fulfilled', synced_at = ? WHERE shopify_order_id = ?",
                (_now(), order_id),
            )

    if row:
        email = row["customer_email"]
        _maybe_trigger_journey("order_delivered", email, {"order_id": order_id})
        _log_sync("webhook", "fulfillment", order_id, email, "ok", payload)
        return {"status": "ok", "email": email}

    _log_sync("webhook", "fulfillment", order_id, None, "skipped", payload, "order not found")
    return {"status": "skipped", "reason": "order not found locally"}


def _maybe_trigger_journey(trigger_event: str, customer_email: str, context: dict):
    try:
        from app.services.journey_engine_v2 import list_journeys, enroll_customer
        journeys = list_journeys(status="active")
        for j in journeys:
            if j.get("trigger_event") == trigger_event:
                enroll_customer(j["id"], customer_email, context)
    except Exception as exc:
        logger.warning("Journey trigger failed for %s/%s: %s", trigger_event, customer_email, exc)


# ─── Historical Backfill ──────────────────────────────────────────────────────

def backfill_customers(
    shop_url: str,
    access_token: str,
    limit_pages: int = 50,
) -> dict:
    """Fetch all Shopify customers and upsert into unified customers table."""
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    }
    created = updated = skipped = errors = 0
    page_url = f"https://{shop_url}/admin/api/2024-01/customers.json?limit=250"

    for _ in range(limit_pages):
        if not page_url:
            break
        try:
            req = urllib.request.Request(page_url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                link_header = resp.headers.get("Link", "")
        except Exception as exc:
            logger.error("Shopify backfill HTTP error: %s", exc)
            break

        for c in data.get("customers", []):
            try:
                email = (c.get("email") or "").strip().lower()
                if not email:
                    skipped += 1
                    continue
                existing = None
                with get_connection() as conn:
                    existing = conn.execute(
                        "SELECT id FROM customers WHERE email = ?", (email,)
                    ).fetchone()
                phone = c.get("phone") or (c.get("default_address") or {}).get("phone")
                tags = [t.strip() for t in (c.get("tags") or "").split(",") if t.strip()]
                upsert_customer(
                    email=email,
                    phone=phone,
                    name=f"{c.get('first_name','')} {c.get('last_name','')}".strip() or None,
                    first_name=c.get("first_name"),
                    last_name=c.get("last_name"),
                    shopify_customer_id=str(c.get("id", "")),
                    tags=tags,
                    source="shopify_backfill",
                    email_opted_in=c.get("email_marketing_consent", {}).get("state") in ("subscribed", "implicit"),
                )
                sync_order_stats(
                    email,
                    total_orders=int(c.get("orders_count") or 0),
                    total_spent=float(c.get("total_spent") or 0),
                    last_order_date=c.get("last_order_updated_at"),
                )
                if existing:
                    updated += 1
                else:
                    created += 1
            except Exception as exc:
                logger.warning("Backfill customer error: %s", exc)
                errors += 1

        # Parse next page from Link header
        page_url = _parse_next_link(link_header)
        time.sleep(0.5)  # Shopify rate limit

    return {"created": created, "updated": updated, "skipped": skipped, "errors": errors}


def backfill_orders(
    shop_url: str,
    access_token: str,
    days: int = 90,
    limit_pages: int = 50,
) -> dict:
    """Fetch recent Shopify orders and upsert."""
    from datetime import timedelta
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    }
    synced = errors = 0
    page_url = (
        f"https://{shop_url}/admin/api/2024-01/orders.json"
        f"?limit=250&status=any&created_at_min={since}"
    )

    for _ in range(limit_pages):
        if not page_url:
            break
        try:
            req = urllib.request.Request(page_url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                link_header = resp.headers.get("Link", "")
        except Exception as exc:
            logger.error("Shopify orders backfill error: %s", exc)
            break
        for order in data.get("orders", []):
            try:
                result = sync_order_webhook(order, trigger_journeys=False)
                if result.get("status") == "ok":
                    synced += 1
            except Exception as exc:
                logger.warning("Order sync error: %s", exc)
                errors += 1
        page_url = _parse_next_link(link_header)
        time.sleep(0.5)

    return {"synced": synced, "errors": errors}


def _parse_next_link(link_header: str) -> str | None:
    """Parse Shopify pagination Link header for the 'next' URL."""
    for part in link_header.split(","):
        part = part.strip()
        if 'rel="next"' in part:
            url = part.split(";")[0].strip().strip("<>")
            return url
    return None


def get_sync_log(limit: int = 100) -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM shopify_sync_log ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        try:
            d["payload"] = json.loads(d.pop("payload_json", "{}"))
        except Exception:
            d["payload"] = {}
        items.append(d)
    return items
