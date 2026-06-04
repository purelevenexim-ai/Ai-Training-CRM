"""
Basil Commerce OS — Phase 5
routes/shopify_webhook.py

Handles Shopify Admin webhook events.

Registered webhooks (set up once in Shopify Admin or via API):
  orders/create   → POST /api/shopify/webhook/order-created
  orders/paid     → POST /api/shopify/webhook/order-paid
  orders/fulfilled → POST /api/shopify/webhook/order-fulfilled

Security: validates X-Shopify-Hmac-Sha256 header (base64 HMAC-SHA256 of raw body
using SHOPIFY_WEBHOOK_SECRET). Requests without a valid signature are rejected 401.

Flow per webhook:
  order-created   → upsert journey_customer + immediately send order_confirmed_v1
  order-paid      → updates total_spent, purchase_count; triggers purchase engagement
  order-fulfilled → update waybill_id from fulfillment tracking; send delivery_begun_v1
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.journey_engine import send_journey_message, record_engagement
try:
    from app.services.email_service import send_and_record_journey_email
except ImportError:  # Live deployments before email-log helper existed.
    from app.services.email_service import send_journey_email

    def send_and_record_journey_email(conn, customer, stage, related_message_id=None):
        return send_journey_email(customer, stage, {"related_message_id": related_message_id})
from app.storage import get_db_connection

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Signature validation ────────────────────────────────────────────────────

def _validate_shopify_hmac(raw_body: bytes, hmac_header: str | None) -> bool:
    secret = settings.shopify_webhook_secret
    if not secret:
        logger.warning("SHOPIFY_WEBHOOK_SECRET not set — skipping HMAC validation (dev mode)")
        return True
    if not hmac_header:
        return False
    expected = base64.b64encode(
        hmac.new(secret.encode(), raw_body, hashlib.sha256).digest()
    ).decode()
    return hmac.compare_digest(expected, hmac_header)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_phone(raw: str | None) -> str:
    if not raw:
        return ""
    digits = "".join(c for c in raw if c.isdigit())
    # Ensure 91 country code prefix for Indian numbers
    if len(digits) == 10:
        digits = "91" + digits
    return digits


def _extract_tracking_context(order: dict[str, Any]) -> dict[str, str | None]:
    keys = [
        "gclid", "gbraid", "wbraid", "fbclid", "fbp", "fbc",
        "ga_client_id", "ga_session_id",
        "utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term",
    ]
    values: dict[str, str | None] = {key: None for key in keys}

    def put(key: str, value: Any) -> None:
        if key not in values or values[key]:
            return
        text = str(value or "").strip()
        if text:
            values[key] = text

    for attr in order.get("note_attributes") or []:
        if isinstance(attr, dict):
            put(str(attr.get("name") or attr.get("key") or "").strip(), attr.get("value"))

    for key in keys:
        put(key, order.get(key))

    for url_key in ("landing_site", "referring_site"):
        raw_url = str(order.get(url_key) or "")
        if not raw_url:
            continue
        try:
            parsed = urlparse(raw_url)
            query = parse_qs(parsed.query)
        except Exception:
            continue
        for key in keys:
            if query.get(key):
                put(key, query[key][0])

    return values


# ─── Order Created ───────────────────────────────────────────────────────────

@router.post(
    "/shopify/webhook/order-created",
    include_in_schema=True,
    status_code=status.HTTP_200_OK,
)
async def order_created(
    request: Request,
    x_shopify_hmac_sha256: str | None = Header(default=None),
    x_shopify_shop_domain: str | None = Header(default=None),
) -> JSONResponse:
    raw = await request.body()
    if not _validate_shopify_hmac(raw, x_shopify_hmac_sha256):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid HMAC")

    try:
        order = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid JSON")

    shop = x_shopify_shop_domain or settings.default_shop_domain or ""
    now = _now_iso()

    # Extract fields
    order_id     = str(order.get("id", "") or order.get("order_number", ""))
    customer_rec = order.get("customer") or {}
    cust_id      = str(customer_rec.get("id", ""))
    name         = (customer_rec.get("first_name") or "") + " " + (customer_rec.get("last_name") or "")
    name         = name.strip() or customer_rec.get("name", "")
    email        = customer_rec.get("email", "")
    phone        = _normalize_phone(
        order.get("shipping_address", {}).get("phone")
        or customer_rec.get("phone")
        or order.get("phone")
    )
    total_price_str = str(order.get("total_price", "0") or "0")
    try:
        order_value_paise = int(float(total_price_str) * 100)
    except (ValueError, TypeError):
        order_value_paise = 0

    total_spent_str = str(customer_rec.get("total_spent", "0") or "0")
    try:
        total_spent_paise = int(float(total_spent_str) * 100)
    except (ValueError, TypeError):
        total_spent_paise = order_value_paise

    purchase_count = int(customer_rec.get("orders_count", 1) or 1)
    tracking_context = _extract_tracking_context(order)

    if not phone:
        logger.warning("order-created: no phone for order %s — skipping journey", order_id)
        return JSONResponse({"status": "skipped", "reason": "no_phone"})

    customer_id = str(uuid.uuid4())
    result = {"status": "created", "customer_id": customer_id}

    with get_db_connection() as conn:
        # Upsert journey customer
        existing = conn.execute(
            "SELECT id FROM journey_customers WHERE shop_domain = ? AND shopify_order_id = ? LIMIT 1",
            (shop, order_id),
        ).fetchone()

        if existing:
            customer_id = existing["id"]
            conn.execute(
                """
                UPDATE journey_customers SET
                    name = COALESCE(NULLIF(?, ''), name),
                    email = COALESCE(NULLIF(?, ''), email),
                    order_value_paise = ?,
                    total_spent_paise = ?,
                    purchase_count = ?,
                          gclid = COALESCE(NULLIF(?, ''), gclid),
                          gbraid = COALESCE(NULLIF(?, ''), gbraid),
                          wbraid = COALESCE(NULLIF(?, ''), wbraid),
                          fbclid = COALESCE(NULLIF(?, ''), fbclid),
                          fbp = COALESCE(NULLIF(?, ''), fbp),
                          fbc = COALESCE(NULLIF(?, ''), fbc),
                          ga_client_id = COALESCE(NULLIF(?, ''), ga_client_id),
                          ga_session_id = COALESCE(NULLIF(?, ''), ga_session_id),
                          utm_source = COALESCE(NULLIF(?, ''), utm_source),
                          utm_medium = COALESCE(NULLIF(?, ''), utm_medium),
                          utm_campaign = COALESCE(NULLIF(?, ''), utm_campaign),
                          utm_content = COALESCE(NULLIF(?, ''), utm_content),
                          utm_term = COALESCE(NULLIF(?, ''), utm_term),
                    updated_at = ?
                WHERE id = ?
                """,
                (name or None, email or None, order_value_paise,
                      total_spent_paise, purchase_count,
                      tracking_context.get("gclid"), tracking_context.get("gbraid"), tracking_context.get("wbraid"),
                      tracking_context.get("fbclid"), tracking_context.get("fbp"), tracking_context.get("fbc"),
                      tracking_context.get("ga_client_id"), tracking_context.get("ga_session_id"),
                      tracking_context.get("utm_source"), tracking_context.get("utm_medium"), tracking_context.get("utm_campaign"),
                      tracking_context.get("utm_content"), tracking_context.get("utm_term"),
                      now, customer_id),
            )
            result = {"status": "updated", "customer_id": customer_id}
        else:
            conn.execute(
                """
                INSERT INTO journey_customers (
                    id, shop_domain, phone, name, email,
                    shopify_customer_id, shopify_order_id,
                    order_value_paise, delivery_status, journey_stage,
                    journey_started_at, engagement_score, is_responsive,
                    do_not_message, whatsapp_subscription_status,
                    google_review_status, customer_segment,
                    total_spent_paise, purchase_count,
                    gclid, gbraid, wbraid, fbclid, fbp, fbc,
                    ga_client_id, ga_session_id,
                    utm_source, utm_medium, utm_campaign, utm_content, utm_term,
                    created_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?,
                    ?, 'pending', 'order_confirmed',
                    ?, 0.0, 0,
                    0, 'subscribed',
                    'not_submitted', 'new',
                    ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?,
                    ?, ?, ?, ?, ?,
                    ?, ?
                )
                """,
                (
                    customer_id, shop, phone, name or None, email or None,
                    cust_id or None, order_id,
                    order_value_paise,
                    now,
                    total_spent_paise, purchase_count,
                    tracking_context.get("gclid"), tracking_context.get("gbraid"), tracking_context.get("wbraid"),
                    tracking_context.get("fbclid"), tracking_context.get("fbp"), tracking_context.get("fbc"),
                    tracking_context.get("ga_client_id"), tracking_context.get("ga_session_id"),
                    tracking_context.get("utm_source"), tracking_context.get("utm_medium"), tracking_context.get("utm_campaign"),
                    tracking_context.get("utm_content"), tracking_context.get("utm_term"),
                    now, now,
                ),
            )

        # Fetch fresh customer record for send
        customer_row = conn.execute(
            "SELECT * FROM journey_customers WHERE id = ?", (customer_id,)
        ).fetchone()
        customer = dict(customer_row)

        # Immediately send Day 1 order confirmation
        send_result = send_journey_message(conn, customer, "order_confirmed")
        if send_result.status == "sent":
            email_result = send_and_record_journey_email(conn, customer, "order_confirmed", send_result.message_id)
            if not email_result.success:
                logger.info("Order confirmation email skipped for %s: %s", customer_id, email_result.error)

    result["send_status"] = send_result.status
    result["template"] = send_result.template_name
    result["message_id"] = send_result.message_id
    return JSONResponse(result)


# ─── Order Paid ──────────────────────────────────────────────────────────────

@router.post(
    "/shopify/webhook/order-paid",
    include_in_schema=True,
    status_code=status.HTTP_200_OK,
)
async def order_paid(
    request: Request,
    x_shopify_hmac_sha256: str | None = Header(default=None),
    x_shopify_shop_domain: str | None = Header(default=None),
) -> JSONResponse:
    raw = await request.body()
    if not _validate_shopify_hmac(raw, x_shopify_hmac_sha256):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid HMAC")

    try:
        order = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid JSON")

    shop     = x_shopify_shop_domain or settings.default_shop_domain or ""
    order_id = str(order.get("id", "") or order.get("order_number", ""))

    total_price_str = str(order.get("total_price", "0") or "0")
    try:
        order_value_paise = int(float(total_price_str) * 100)
    except (ValueError, TypeError):
        order_value_paise = 0

    now = _now_iso()
    tracking_context = _extract_tracking_context(order)

    with get_db_connection() as conn:
        customer_row = conn.execute(
            "SELECT * FROM journey_customers WHERE shop_domain = ? AND shopify_order_id = ? LIMIT 1",
            (shop, order_id),
        ).fetchone()

        if not customer_row:
            return JSONResponse({"status": "no_customer", "order_id": order_id})

        customer = dict(customer_row)
        customer_id = customer["id"]

        # Update LTV data
        conn.execute(
            """
            UPDATE journey_customers SET
                total_spent_paise = total_spent_paise + ?,
                purchase_count = purchase_count + 1,
                last_purchase_at = ?,
                gclid = COALESCE(NULLIF(?, ''), gclid),
                gbraid = COALESCE(NULLIF(?, ''), gbraid),
                wbraid = COALESCE(NULLIF(?, ''), wbraid),
                fbclid = COALESCE(NULLIF(?, ''), fbclid),
                fbp = COALESCE(NULLIF(?, ''), fbp),
                fbc = COALESCE(NULLIF(?, ''), fbc),
                ga_client_id = COALESCE(NULLIF(?, ''), ga_client_id),
                ga_session_id = COALESCE(NULLIF(?, ''), ga_session_id),
                utm_source = COALESCE(NULLIF(?, ''), utm_source),
                utm_medium = COALESCE(NULLIF(?, ''), utm_medium),
                utm_campaign = COALESCE(NULLIF(?, ''), utm_campaign),
                utm_content = COALESCE(NULLIF(?, ''), utm_content),
                utm_term = COALESCE(NULLIF(?, ''), utm_term),
                updated_at = ?
            WHERE id = ?
            """,
            (
                order_value_paise, now,
                tracking_context.get("gclid"), tracking_context.get("gbraid"), tracking_context.get("wbraid"),
                tracking_context.get("fbclid"), tracking_context.get("fbp"), tracking_context.get("fbc"),
                tracking_context.get("ga_client_id"), tracking_context.get("ga_session_id"),
                tracking_context.get("utm_source"), tracking_context.get("utm_medium"), tracking_context.get("utm_campaign"),
                tracking_context.get("utm_content"), tracking_context.get("utm_term"),
                now, customer_id,
            ),
        )

        # Award purchase engagement points (50 pts = massive signal)
        record_engagement(
            conn, customer_id, "purchase", 50.0,
            template_name="shopify_order",
            stage="order_paid",
            meta={"order_id": order_id, "value_paise": order_value_paise},
        )

    return JSONResponse({
        "status": "ok",
        "customer_id": customer_id,
        "purchase_points_awarded": 50,
    })


# ─── Order Fulfilled ─────────────────────────────────────────────────────────

@router.post(
    "/shopify/webhook/order-fulfilled",
    include_in_schema=True,
    status_code=status.HTTP_200_OK,
)
async def order_fulfilled(
    request: Request,
    x_shopify_hmac_sha256: str | None = Header(default=None),
    x_shopify_shop_domain: str | None = Header(default=None),
) -> JSONResponse:
    """
    Shopify sends this when a fulfillment is created (shipment dispatched).
    We extract the tracking number (waybill_id) and immediately send Day 2 in-transit message.
    """
    raw = await request.body()
    if not _validate_shopify_hmac(raw, x_shopify_hmac_sha256):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid HMAC")

    try:
        order = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid JSON")

    shop     = x_shopify_shop_domain or settings.default_shop_domain or ""
    order_id = str(order.get("id", "") or order.get("order_number", ""))

    # Extract waybill from fulfillments list
    waybill_id = ""
    fulfillments = order.get("fulfillments") or []
    for f in fulfillments:
        tracking_numbers = f.get("tracking_numbers") or []
        if tracking_numbers:
            waybill_id = str(tracking_numbers[0]).strip()
            break
        tracking = f.get("tracking_number")
        if tracking:
            waybill_id = str(tracking).strip()
            break

    now = _now_iso()

    with get_db_connection() as conn:
        customer_row = conn.execute(
            "SELECT * FROM journey_customers WHERE shop_domain = ? AND shopify_order_id = ? LIMIT 1",
            (shop, order_id),
        ).fetchone()

        if not customer_row:
            return JSONResponse({"status": "no_customer", "order_id": order_id})

        customer = dict(customer_row)
        customer_id = customer["id"]

        # Update waybill
        if waybill_id:
            conn.execute(
                "UPDATE journey_customers SET waybill_id = ?, delivery_status = 'in_transit', updated_at = ? WHERE id = ?",
                (waybill_id, now, customer_id),
            )
            customer["waybill_id"] = waybill_id

        # Send in-transit message if not already sent
        send_result = send_journey_message(conn, customer, "in_transit")
        if send_result.status == "sent":
            email_result = send_and_record_journey_email(conn, customer, "in_transit", send_result.message_id)
            if not email_result.success:
                logger.info("In-transit email skipped for %s: %s", customer_id, email_result.error)

    return JSONResponse({
        "status": "ok",
        "customer_id": customer_id,
        "waybill_id": waybill_id,
        "send_status": send_result.status,
        "template": send_result.template_name,
    })


# ─── Phase 5: Unified Customer + Order Webhooks ───────────────────────────────

@router.post(
    "/shopify/webhooks/customers/create",
    include_in_schema=True,
    status_code=status.HTTP_200_OK,
    summary="Phase 5 — Shopify customer created webhook → unified customers table",
)
async def shopify_customer_created(
    request: Request,
    x_shopify_hmac_sha256: str | None = Header(default=None),
) -> JSONResponse:
    raw = await request.body()
    if not _validate_shopify_hmac(raw, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="Invalid HMAC")
    payload = json.loads(raw)
    from app.services.shopify_sync_service import sync_customer_webhook
    result = sync_customer_webhook(payload)
    return JSONResponse(result)


@router.post(
    "/shopify/webhooks/customers/update",
    include_in_schema=True,
    status_code=status.HTTP_200_OK,
    summary="Phase 5 — Shopify customer updated webhook → unified customers table",
)
async def shopify_customer_updated(
    request: Request,
    x_shopify_hmac_sha256: str | None = Header(default=None),
) -> JSONResponse:
    raw = await request.body()
    if not _validate_shopify_hmac(raw, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="Invalid HMAC")
    payload = json.loads(raw)
    from app.services.shopify_sync_service import sync_customer_webhook
    result = sync_customer_webhook(payload)
    return JSONResponse(result)


@router.post(
    "/shopify/webhooks/orders/create",
    include_in_schema=True,
    status_code=status.HTTP_200_OK,
    summary="Phase 5 — Shopify order created → sync shopify_orders + enroll in journey",
)
async def shopify_order_created_unified(
    request: Request,
    x_shopify_hmac_sha256: str | None = Header(default=None),
) -> JSONResponse:
    raw = await request.body()
    if not _validate_shopify_hmac(raw, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="Invalid HMAC")
    payload = json.loads(raw)
    from app.services.shopify_sync_service import sync_order_webhook
    result = sync_order_webhook(payload, trigger_journeys=True)
    return JSONResponse(result)


@router.post(
    "/shopify/webhooks/orders/fulfilled",
    include_in_schema=True,
    status_code=status.HTTP_200_OK,
    summary="Phase 5 — Shopify order fulfilled → trigger order_delivered journey",
)
async def shopify_order_fulfilled_unified(
    request: Request,
    x_shopify_hmac_sha256: str | None = Header(default=None),
) -> JSONResponse:
    raw = await request.body()
    if not _validate_shopify_hmac(raw, x_shopify_hmac_sha256):
        raise HTTPException(status_code=401, detail="Invalid HMAC")
    payload = json.loads(raw)
    from app.services.shopify_sync_service import sync_fulfillment_webhook
    result = sync_fulfillment_webhook(payload)
    return JSONResponse(result)


@router.post(
    "/shopify/webhooks/fulfillments/create",
    include_in_schema=True,
    status_code=status.HTTP_200_OK,
    summary="Shopify fulfillment created — tracking number assigned, send tracking WhatsApp",
)
async def shopify_fulfillment_created(
    request: Request,
    x_shopify_hmac_sha256: str | None = Header(default=None),
    x_shopify_shop_domain: str | None = Header(default=None),
) -> JSONResponse:
    """
    Shopify fires fulfillments/create when a fulfillment is first created and a
    tracking number is assigned.  Payload is the fulfillment object (not the order).
    We locate the journey_customer by order_id, update the waybill, and send the
    in-transit WhatsApp notification.
    """
    raw = await request.body()
    if not _validate_shopify_hmac(raw, x_shopify_hmac_sha256):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid HMAC")
    try:
        fulfillment = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid JSON")

    shop = x_shopify_shop_domain or settings.default_shop_domain or ""
    order_id = str(fulfillment.get("order_id", "") or "")

    # Extract tracking number from fulfillment payload
    waybill_id = ""
    tracking_numbers = fulfillment.get("tracking_numbers") or []
    if tracking_numbers:
        waybill_id = str(tracking_numbers[0]).strip()
    if not waybill_id:
        tracking = fulfillment.get("tracking_number")
        if tracking:
            waybill_id = str(tracking).strip()

    tracking_url = ""
    tracking_urls = fulfillment.get("tracking_urls") or []
    if tracking_urls:
        tracking_url = str(tracking_urls[0]).strip()
    if not tracking_url:
        tracking_url = str(fulfillment.get("tracking_url") or "").strip()

    now = _now_iso()

    with get_db_connection() as conn:
        customer_row = conn.execute(
            "SELECT * FROM journey_customers WHERE shop_domain = ? AND shopify_order_id = ? LIMIT 1",
            (shop, order_id),
        ).fetchone()

        if not customer_row:
            return JSONResponse({"status": "no_customer", "order_id": order_id})

        customer = dict(customer_row)
        customer_id = customer["id"]

        if waybill_id:
            conn.execute(
                "UPDATE journey_customers SET waybill_id = ?, delivery_status = 'in_transit', updated_at = ? WHERE id = ?",
                (waybill_id, now, customer_id),
            )
            customer["waybill_id"] = waybill_id

        send_result = send_journey_message(conn, customer, "in_transit")
        if send_result.status == "sent":
            email_result = send_and_record_journey_email(conn, customer, "in_transit", send_result.message_id)
            if not email_result.success:
                logger.info("Fulfillment email skipped for %s: %s", customer_id, email_result.error)

    return JSONResponse({
        "status": "ok",
        "customer_id": customer_id,
        "order_id": order_id,
        "waybill_id": waybill_id,
        "tracking_url": tracking_url,
        "send_status": send_result.status,
        "template": send_result.template_name,
    })


@router.post(
    "/shopify/backfill/customers",
    include_in_schema=True,
    status_code=status.HTTP_200_OK,
    summary="Phase 5 — Trigger historical customer backfill from Shopify Admin API",
)
async def shopify_backfill_customers(
    request: Request,
    admin_secret: str = "",
) -> JSONResponse:
    from fastapi import Query as Q
    from app.config import settings as _s
    body = await request.json()
    if body.get("admin_secret") != _s.admin_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")
    shop_url = body.get("shop_url")
    access_token = body.get("access_token")
    if not shop_url or not access_token:
        raise HTTPException(status_code=400, detail="shop_url and access_token required")
    from app.services.shopify_sync_service import backfill_customers
    result = backfill_customers(shop_url, access_token)
    return JSONResponse(result)


@router.post(
    "/shopify/backfill/orders",
    include_in_schema=True,
    status_code=status.HTTP_200_OK,
    summary="Phase 5 — Trigger historical orders backfill from Shopify Admin API",
)
async def shopify_backfill_orders(
    request: Request,
) -> JSONResponse:
    body = await request.json()
    from app.config import settings as _s
    if body.get("admin_secret") != _s.admin_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")
    shop_url = body.get("shop_url")
    access_token = body.get("access_token")
    days = int(body.get("days", 90))
    if not shop_url or not access_token:
        raise HTTPException(status_code=400, detail="shop_url and access_token required")
    from app.services.shopify_sync_service import backfill_orders
    result = backfill_orders(shop_url, access_token, days=days)
    return JSONResponse(result)


@router.get(
    "/shopify/sync/log",
    include_in_schema=True,
    summary="Phase 5 — View recent Shopify sync log entries",
)
def shopify_sync_log(
    admin_secret: str = "",
    limit: int = 100,
) -> JSONResponse:
    from app.config import settings as _s
    if admin_secret != _s.admin_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")
    from app.services.shopify_sync_service import get_sync_log
    return JSONResponse(get_sync_log(limit=limit))

