from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.config import settings
from app.storage import get_db_connection

logger = logging.getLogger(__name__)
router = APIRouter()


class _SyncOptions:
    def __init__(
        self,
        lookback_hours: int,
        limit: int,
        offset: int,
        trigger_tracking: bool,
        dry_run: bool,
    ) -> None:
        self.lookback_hours = max(1, min(lookback_hours, 24 * 30))
        self.limit = max(1, min(limit, 500))
        self.offset = max(0, offset)
        self.trigger_tracking = trigger_tracking
        self.dry_run = dry_run


def _require_admin_secret(admin_secret: str) -> None:
    expected = (os.getenv("ANU_LOGIN_ADMIN_SECRET") or settings.admin_secret or "basil").strip()
    if not expected or admin_secret != expected:
        raise HTTPException(status_code=403, detail="Forbidden")


def _row_to_order_payload(row: dict[str, Any]) -> dict[str, Any]:
    order_ref = str(row.get("shopify_order_id") or "").strip()
    phone_raw = str(row.get("phone") or "")
    phone_digits = re.sub(r"\D", "", phone_raw)
    if phone_digits and not phone_digits.startswith("91"):
        phone_digits = f"91{phone_digits}"

    order_value_inr = 0.0
    try:
        order_value_inr = round((row.get("order_value_paise") or 0) / 100.0, 2)
    except Exception:
        order_value_inr = 0.0

    order_date = row.get("delivered_at") or row.get("journey_started_at") or row.get("created_at")
    return {
        "order_id": order_ref,
        "order_date": order_date,
        "email": row.get("email"),
        "phone": phone_digits,
        "name": row.get("name"),
        "total_amount": order_value_inr,
        "currency": "INR",
        "status": "paid",
        "source": "anu_review_journey",
        "payment_method": "whatsapp_bridge",
        "gclid": row.get("gclid"),
        "gbraid": row.get("gbraid"),
        "wbraid": row.get("wbraid"),
        "fbclid": row.get("fbclid"),
        "fbp": row.get("fbp"),
        "fbc": row.get("fbc"),
        "ga_client_id": row.get("ga_client_id"),
        "ga_session_id": row.get("ga_session_id"),
        "utm_source": row.get("utm_source"),
        "utm_medium": row.get("utm_medium"),
        "utm_campaign": row.get("utm_campaign"),
        "utm_content": row.get("utm_content"),
        "utm_term": row.get("utm_term"),
        "metadata": {
            "delivery_status": row.get("delivery_status"),
            "review_submitted_at": row.get("review_submitted_at"),
            "customer_status": row.get("customer_status"),
        },
    }


def _load_recent_delivered_rows(options: _SyncOptions) -> list[dict[str, Any]]:
    since_iso = (datetime.now(timezone.utc) - timedelta(hours=options.lookback_hours)).isoformat()
    shop_domain = (getattr(settings, "default_shop_domain", "") or "").strip()
    where = [
        "delivery_status = 'delivered'",
        "shopify_order_id IS NOT NULL",
        "TRIM(shopify_order_id) != ''",
        "COALESCE(updated_at, created_at) >= ?",
    ]
    params: list[Any] = [since_iso]
    if shop_domain:
        where.insert(0, "shop_domain = ?")
        params.insert(0, shop_domain)

    sql = f"""
        SELECT
            shopify_order_id,
            name,
            phone,
            email,
            order_value_paise,
            delivery_status,
            delivered_at,
            journey_started_at,
            created_at,
            updated_at,
            review_submitted_at,
            customer_status,
            gclid,
            gbraid,
            wbraid,
            fbclid,
            fbp,
            fbc,
            ga_client_id,
            ga_session_id,
            utm_source,
            utm_medium,
            utm_campaign,
            utm_content,
            utm_term
        FROM journey_customers
        WHERE {' AND '.join(where)}
        ORDER BY COALESCE(updated_at, created_at) DESC
        LIMIT ? OFFSET ?
    """
    with get_db_connection() as conn:
        rows = conn.execute(sql, [*params, options.limit, options.offset]).fetchall()
    return [dict(r) for r in rows]


def _post_to_root(payload: dict[str, Any]) -> dict[str, Any]:
    root_url = (
        os.getenv("ROOT_TRACKING_SYNC_URL")
        or "https://track.pureleven.com/api/crm/admin/tracking/upsert-anu-orders"
    ).strip()
    root_secret = (os.getenv("ROOT_TRACKING_ADMIN_SECRET") or "basil").strip()
    separator = "&" if "?" in root_url else "?"
    url = f"{root_url}{separator}admin_secret={urllib.parse.quote(root_secret)}"

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", errors="ignore")
        return json.loads(body or "{}")


@router.post("/integrations/root-tracking/sync")
def sync_review_journey_to_root_tracking(
    admin_secret: str = Query(default=""),
    lookback_hours: int = Query(default=24, ge=1, le=24 * 30),
    limit: int = Query(default=200, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    trigger_tracking: bool = Query(default=True),
    dry_run: bool = Query(default=False),
) -> dict[str, Any]:
    _require_admin_secret(admin_secret)
    options = _SyncOptions(
        lookback_hours=lookback_hours,
        limit=limit,
        offset=offset,
        trigger_tracking=trigger_tracking,
        dry_run=dry_run,
    )

    rows = _load_recent_delivered_rows(options)
    orders = [_row_to_order_payload(row) for row in rows if row.get("shopify_order_id")]
    if not orders:
        return {
            "status": "ok",
            "message": "No delivered journey orders in selected window",
            "lookback_hours": options.lookback_hours,
            "limit": options.limit,
            "offset": options.offset,
            "orders": 0,
        }

    payload = {
        "orders": orders,
        "trigger_tracking": options.trigger_tracking,
        "dry_run": options.dry_run,
    }

    try:
        result = _post_to_root(payload)
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="ignore")
        logger.warning("Root tracking sync HTTP %s: %s", exc.code, err)
        raise HTTPException(status_code=502, detail=f"Root sync HTTP {exc.code}: {err}")
    except Exception as exc:
        logger.warning("Root tracking sync failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Root sync failed: {exc}")

    return {
        "status": "ok",
        "sent_orders": len(orders),
        "lookback_hours": options.lookback_hours,
        "trigger_tracking": options.trigger_tracking,
        "dry_run": options.dry_run,
        "root_result": result,
    }
