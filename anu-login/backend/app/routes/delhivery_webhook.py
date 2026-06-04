"""
Basil Commerce OS — Phase 5
routes/delhivery_webhook.py

Receives real-time delivery status webhooks from Delhivery B2C.
On delivery confirmation, updates journey_customers and emits journey trigger.

Security: validates HMAC-SHA256 signature from X-Delhivery-Signature header.

Delhivery status codes:
  0 = Manifested / picked up
  1 = In transit
  2 = In transit (hub)
  3 = Out for delivery
  4 = Pending COD/payment
  5 = Delivered
  6 = Delivery rescheduled
  7 = RTO initiated
  8 = RTO in transit
  9 = RTO delivered
  10 = Delivery failed / returned
  11 = Lost

Journey triggers emitted (stored in journey_customers.journey_stage):
  in_transit  → update delivery status, no message (Day 2 N8N workflow picks up)
  out_for_delivery → update delivery status
  delivered   → set delivered_at, trigger Day 5 review request
  failed      → pause journey, flag for review
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.journey_engine import send_journey_message
from app.services.email_service import send_and_record_journey_email
from app.storage import get_db_connection

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Status mappings ─────────────────────────────────────────────────────────

STATUS_CODE_MAP: dict[int, str] = {
    0: "manifested",
    1: "in_transit",
    2: "in_transit",
    3: "out_for_delivery",
    4: "pending_cod",
    5: "delivered",
    6: "rescheduled",
    7: "rto_initiated",
    8: "rto_in_transit",
    9: "rto_delivered",
    10: "delivery_failed",
    11: "lost",
}

# Status codes that advance the journey
JOURNEY_ADVANCE_CODES: set[int] = {2, 3, 5, 10}

# Stage name to write into journey_customers.journey_stage
JOURNEY_STAGE_MAP: dict[int, str] = {
    2: "in_transit",
    3: "out_for_delivery",
    5: "delivered",
    10: "delivery_failed",
}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """
    Delhivery signs the request body with HMAC-SHA256 using the API token as secret.
    Header format: X-Delhivery-Signature: sha256=<hex_digest>
    """
    secret = settings.delhivery_webhook_secret
    if not secret:
        # Webhook secret not configured — skip validation (dev mode only)
        logger.warning("DELHIVERY_WEBHOOK_SECRET not set; skipping signature validation")
        return True

    if not signature_header:
        return False

    if not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    provided = signature_header[len("sha256="):]
    return hmac.compare_digest(expected, provided)


def _normalize_phone(phone: str | None) -> str:
    """Strip non-digit characters; return empty string if None."""
    if not phone:
        return ""
    return "".join(c for c in phone if c.isdigit())


def _find_customer_by_waybill(conn: Any, waybill_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM journey_customers WHERE waybill_id = ? ORDER BY created_at DESC LIMIT 1",
        (waybill_id,),
    ).fetchone()
    return dict(row) if row else None


def _find_customer_by_order(conn: Any, shop_domain: str, order_id: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM journey_customers WHERE shop_domain = ? AND shopify_order_id = ? LIMIT 1",
        (shop_domain, order_id),
    ).fetchone()
    return dict(row) if row else None


# ─── Main webhook route ───────────────────────────────────────────────────────

@router.post(
    "/delhivery/webhook",
    summary="Receive delivery status update from Delhivery",
    status_code=status.HTTP_200_OK,
    include_in_schema=True,
)
async def delhivery_webhook(
    request: Request,
    x_delhivery_signature: str | None = Header(default=None),
) -> JSONResponse:
    raw_body = await request.body()

    # ── Signature validation ─────────────────────────────────────────────────
    if not _validate_signature(raw_body, x_delhivery_signature):
        logger.warning("Delhivery webhook: invalid signature, rejecting")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    # ── Parse body ───────────────────────────────────────────────────────────
    try:
        payload = json.loads(raw_body)
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    # Delhivery sends either a single shipment or a list under "packages"
    packages = payload if isinstance(payload, list) else payload.get("packages", [payload])

    now = _now_iso()
    results: list[dict[str, Any]] = []

    with get_db_connection() as conn:
        for pkg in packages:
            result = _process_package(conn, pkg, now)
            results.append(result)

    return JSONResponse(
        content={"status": "ok", "processed": len(results), "results": results},
        status_code=status.HTTP_200_OK,
    )


def _process_package(conn: Any, pkg: dict[str, Any], now: str) -> dict[str, Any]:
    """Process a single shipment update from the Delhivery payload."""
    waybill_id: str = str(pkg.get("waybill", "") or pkg.get("awb", "") or "").strip()
    if not waybill_id:
        return {"status": "skip", "reason": "no waybill_id"}

    # Extract status
    status_code_raw = pkg.get("status_code", pkg.get("Status", -1))
    try:
        status_code = int(status_code_raw)
    except (TypeError, ValueError):
        status_code = -1

    status_label = STATUS_CODE_MAP.get(status_code, "unknown")
    location: str = str(pkg.get("city", "") or pkg.get("location", "") or "").strip()
    event_ts: str = str(pkg.get("timestamp", "") or pkg.get("updated_at", "") or now).strip()

    # Map Delhivery order reference to Shopify order id (Delhivery sends it as
    # "refnum" or "order_id" in most integrations)
    shopify_order_id: str = str(
        pkg.get("refnum", "") or pkg.get("order_id", "") or pkg.get("reference_no", "") or ""
    ).strip()
    customer_phone: str = _normalize_phone(
        pkg.get("consignee_phone") or pkg.get("phone") or pkg.get("mobile")
    )
    shop_domain: str = str(pkg.get("shop_domain", settings.default_shop_domain or "")).strip()

    # ── Store raw delivery event ─────────────────────────────────────────────
    tracking_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO delivery_tracking
          (id, waybill_id, shop_domain, shopify_order_id, customer_phone,
           status_code, status_label, location, event_timestamp, raw_payload_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            tracking_id,
            waybill_id,
            shop_domain,
            shopify_order_id or None,
            customer_phone or None,
            status_code,
            status_label,
            location or None,
            event_ts,
            json.dumps(pkg, ensure_ascii=True),
            now,
        ),
    )

    # ── Find journey customer ─────────────────────────────────────────────────
    customer = _find_customer_by_waybill(conn, waybill_id)
    if not customer and shopify_order_id and shop_domain:
        customer = _find_customer_by_order(conn, shop_domain, shopify_order_id)

    if not customer:
        logger.info("Delhivery webhook: no journey customer found for waybill %s", waybill_id)
        return {"status": "no_customer", "waybill_id": waybill_id, "status_label": status_label}

    # ── Update customer delivery state ───────────────────────────────────────
    update: dict[str, Any] = {
        "delivery_status": status_label,
        "waybill_id": waybill_id,
        "updated_at": now,
    }

    if status_code in JOURNEY_ADVANCE_CODES:
        new_stage = JOURNEY_STAGE_MAP.get(status_code)
        if new_stage:
            update["journey_stage"] = new_stage

    if status_code == 5:  # delivered
        update["delivered_at"] = event_ts
        update["journey_stage"] = "delivered"

    set_clause = ", ".join(f"{k} = ?" for k in update)
    conn.execute(
        f"UPDATE journey_customers SET {set_clause} WHERE id = ?",
        [*update.values(), customer["id"]],
    )

    logger.info(
        "Delhivery webhook: waybill=%s status=%s customer=%s",
        waybill_id, status_label, customer["id"],
    )

    # ── Instant send for key delivery milestones ─────────────────────────────
    send_status = "skipped"
    send_stage = None
    if status_code == 2:   # in_transit
        send_stage = "in_transit"
    elif status_code == 5: # delivered
        send_stage = "delivered"

    if send_stage:
        # Fetch fresh customer (state was just updated above)
        fresh_row = conn.execute(
            "SELECT * FROM journey_customers WHERE id = ?", (customer["id"],)
        ).fetchone()
        if fresh_row:
            result = send_journey_message(conn, dict(fresh_row), send_stage)
            send_status = result.status
            if result.status == "sent":
                email_result = send_and_record_journey_email(conn, dict(fresh_row), send_stage, result.message_id)
                if not email_result.success:
                    logger.info("Delivery milestone email skipped for %s: %s", customer["id"], email_result.error)
            logger.info("Instant send stage=%s status=%s", send_stage, send_status)

    return {
        "status": "updated",
        "waybill_id": waybill_id,
        "customer_id": customer["id"],
        "delivery_status": status_label,
        "journey_stage": update.get("journey_stage", customer.get("journey_stage")),
        "instant_send": send_status,
    }


# ─── Fallback: manual status sync ─────────────────────────────────────────────

@router.get(
    "/delhivery/sync/{waybill_id}",
    summary="Manually sync a single waybill status (cron fallback)",
    status_code=status.HTTP_200_OK,
)
def sync_waybill(waybill_id: str) -> dict[str, Any]:
    """
    Cron-triggered fallback in case the real-time webhook misses an event.
    Calls Delhivery Tracking API directly.
    """
    import urllib.request
    import urllib.error

    token = settings.delhivery_api_token
    if not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Delhivery API token not configured",
        )

    url = f"https://track.delhivery.com/api/v1/packages/json/?waybill={waybill_id}&token={token}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        raise HTTPException(status_code=exc.code, detail=f"Delhivery API error: {exc.reason}")
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=503, detail=f"Delhivery API unreachable: {exc.reason}")

    packages = data.get("ShipmentData", [])
    if not packages:
        return {"status": "not_found", "waybill_id": waybill_id}

    pkg_raw = packages[0].get("Shipment", {})
    status_code_raw = pkg_raw.get("Status", {}).get("Status", "")

    # Map Delhivery text status to numeric code for consistent handling
    _TEXT_TO_CODE = {
        "In Transit": 2,
        "Out For Delivery": 3,
        "Delivered": 5,
        "Failed Delivery": 10,
        "RTO Initiated": 7,
        "RTO": 9,
    }
    status_code = _TEXT_TO_CODE.get(status_code_raw, -1)
    status_label = STATUS_CODE_MAP.get(status_code, status_code_raw.lower().replace(" ", "_"))

    now = _now_iso()
    tracking_id = str(uuid.uuid4())
    shop_domain = settings.default_shop_domain or ""

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO delivery_tracking
              (id, waybill_id, shop_domain, shopify_order_id, customer_phone,
               status_code, status_label, location, event_timestamp, raw_payload_json, created_at)
            VALUES (?, ?, ?, NULL, NULL, ?, ?, NULL, ?, ?, ?)
            """,
            (
                tracking_id,
                waybill_id,
                shop_domain,
                status_code,
                status_label,
                now,
                json.dumps(pkg_raw, ensure_ascii=True),
                now,
            ),
        )

        customer = _find_customer_by_waybill(conn, waybill_id)
        if customer and status_code in JOURNEY_ADVANCE_CODES:
            update: dict[str, Any] = {
                "delivery_status": status_label,
                "updated_at": now,
            }
            new_stage = JOURNEY_STAGE_MAP.get(status_code)
            if new_stage:
                update["journey_stage"] = new_stage
            if status_code == 5:
                update["delivered_at"] = now
            set_clause = ", ".join(f"{k} = ?" for k in update)
            conn.execute(
                f"UPDATE journey_customers SET {set_clause} WHERE id = ?",
                [*update.values(), customer["id"]],
            )

    return {
        "status": "synced",
        "waybill_id": waybill_id,
        "status_label": status_label,
        "raw_status": status_code_raw,
    }
