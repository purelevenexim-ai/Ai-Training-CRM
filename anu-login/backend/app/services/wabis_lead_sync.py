"""
Wabis Lead Sync Service

Fetches all subscribers from Wabis and upserts them into the CRM customer/audience
tables. Runs on a 30-minute schedule via wabis_sync_scheduler.py.

After syncing, also promotes any newly-synced contact that has existing orders
in the customers table (set by Shopify order syncs) to purchase_status=purchased.
"""

from __future__ import annotations

import json
import logging
import ssl
import urllib.parse
import urllib.request
from typing import Any

try:
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = ssl.create_default_context()

from app.config import settings
from app.storage import get_db_connection

logger = logging.getLogger(__name__)

_PAGE_SIZE = 500
_WABIS_BASE = "https://bot.wabis.in/api/v1/whatsapp"


# ─── Wabis API helpers ────────────────────────────────────────────────────────

def _fetch_subscriber_page(api_key: str, phone_number_id: str, page: int) -> list[dict]:
    params = urllib.parse.urlencode({
        "apiToken": api_key,
        "phone_number_id": phone_number_id,
        "limit": _PAGE_SIZE,
        "page": page,
    })
    url = f"{_WABIS_BASE}/subscriber/list?{params}"
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "curl/7.88.1"})
    with urllib.request.urlopen(req, context=_SSL_CONTEXT, timeout=30) as resp:  # noqa: S310
        data = json.loads(resp.read().decode())
    return data.get("message") or []


def _fetch_all_subscribers() -> list[dict]:
    api_key = settings.wabis_api_key
    phone_number_id = settings.wabis_phone_number_id
    if not api_key or not phone_number_id:
        logger.error("Wabis sync: WABIS_API_KEY or WABIS_PHONE_NUMBER_ID not set")
        return []

    all_subs: list[dict] = []
    page = 1
    while True:
        try:
            batch = _fetch_subscriber_page(api_key, phone_number_id, page)
        except Exception as exc:
            logger.error("Wabis subscriber fetch failed (page %d): %s", page, exc)
            break
        if not batch:
            break
        all_subs.extend(batch)
        if len(batch) < _PAGE_SIZE:
            break
        page += 1

    return all_subs


# ─── Data mapping ─────────────────────────────────────────────────────────────

def _map_subscriber(sub: dict) -> dict[str, Any]:
    """Map a Wabis subscriber record to a CRM-compatible contact dict."""
    chat_id = (sub.get("chat_id") or "").strip()
    first_name = (sub.get("first_name") or "").strip()
    last_name = (sub.get("last_name") or "").strip()

    # Wabis sets first_name = chat_id when name is unknown — treat as no name
    if first_name == chat_id or first_name.lstrip("+").isdigit():
        first_name = ""

    full_name = f"{first_name} {last_name}".strip() or None

    label_raw = sub.get("label_names") or ""
    label_tags = [t.strip() for t in label_raw.split(",") if t.strip()]

    tags = list(dict.fromkeys(["wabis", "lead"] + label_tags))

    return {
        "phone": chat_id,
        "name": full_name,
        "first_name": first_name or None,
        "last_name": last_name or None,
        "email": sub.get("email") or None,
        "tags": tags,
        "source_label": "wabis_sync",
    }


# ─── Lifecycle update ─────────────────────────────────────────────────────────

def _update_purchase_lifecycle() -> int:
    """
    For any customer in the CRM whose total_orders > 0 but purchase_status is
    not yet 'purchased', promote them: set purchase_status, update engagement_label,
    add the 'purchased' tag, and increase lead_score by 50.
    """
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, tags, lead_score
            FROM customers
            WHERE total_orders > 0
              AND (purchase_status IS NULL OR purchase_status != 'purchased')
              AND deleted_at IS NULL
            """
        ).fetchall()

        count = 0
        for row in rows:
            cust_id, tags_json, lead_score = row
            try:
                existing_tags: list[str] = json.loads(tags_json) if tags_json else []
            except (ValueError, TypeError):
                existing_tags = []

            if "purchased" not in existing_tags:
                existing_tags.append("purchased")

            new_score = (lead_score or 0) + 50
            conn.execute(
                """
                UPDATE customers
                SET purchase_status   = 'purchased',
                    engagement_label  = 'hot',
                    lead_score        = ?,
                    tags              = ?
                WHERE id = ?
                """,
                (new_score, json.dumps(existing_tags), cust_id),
            )
            count += 1

    return count


# ─── Main sync entry point ────────────────────────────────────────────────────

def sync_wabis_leads() -> dict[str, Any]:
    """
    Fetch all Wabis subscribers and upsert them into the CRM.
    Then promote any lead who already has orders to 'purchased'.
    Returns a summary dict.
    """
    logger.info("Wabis lead sync starting…")

    subscribers = _fetch_all_subscribers()
    if not subscribers:
        logger.warning("Wabis lead sync: no subscribers returned from API")
        return {"ok": True, "fetched": 0, "created": 0, "updated": 0, "purchase_updates": 0}

    logger.info("Wabis lead sync: fetched %d subscribers", len(subscribers))

    contacts = [_map_subscriber(s) for s in subscribers]

    # Import via the existing CRM import pipeline (normalise phones, dedup, upsert)
    from app.routes.crm_whatsapp import _import_contacts  # noqa: PLC0415
    result = _import_contacts(contacts, source="wabis_sync", default_tags=["wabis", "lead"])

    # Promote converted leads
    try:
        purchase_updates = _update_purchase_lifecycle()
    except Exception as exc:
        logger.error("Wabis lead sync: lifecycle update failed: %s", exc)
        purchase_updates = 0

    result["fetched"] = len(subscribers)
    result["purchase_updates"] = purchase_updates

    logger.info(
        "Wabis lead sync complete: fetched=%d created=%d updated=%d purchases_promoted=%d",
        len(subscribers), result.get("created", 0), result.get("updated", 0), purchase_updates,
    )
    return result
