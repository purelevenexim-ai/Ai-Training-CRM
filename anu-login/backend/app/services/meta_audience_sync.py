#!/usr/bin/env python3
"""
Meta Custom Audience Sync Service

Syncs scored CRM customers into Meta Custom Audiences for retargeting.
Runs every 6 hours via APScheduler (or can be called directly).

Audience tiers (ad account 237007475595482):
  pl_warm_leads      → lead_score 50–79
  pl_purchase_intent → lead_score 80–89
  pl_buyers          → lead_score 90–100

Phone and email are SHA-256 hashed before upload per Meta CAPI spec.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from app.storage import get_connection

logger = logging.getLogger(__name__)

# ── Config ──────────────────────────────────────────────────────────────────
META_AD_ACCOUNT_ID = "237007475595482"
META_GRAPH_API_VERSION = "v21.0"
META_GRAPH_BASE = f"https://graph.facebook.com/{META_GRAPH_API_VERSION}"
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")

# Score tiers → audience name
AUDIENCE_TIERS: list[tuple[str, int, int]] = [
    ("pl_warm_leads",      50,  79),
    ("pl_purchase_intent", 80,  89),
    ("pl_buyers",          90, 100),
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _sha256(value: str) -> str:
    """Return lowercase hex SHA-256 of a normalised string."""
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()


def _normalise_phone_e164(raw: str | None) -> str | None:
    """Strip non-digits and ensure E.164 (leading +)."""
    if not raw:
        return None
    import re
    digits = re.sub(r"\D", "", str(raw))
    if not digits:
        return None
    if not digits.startswith("91") and len(digits) == 10:
        digits = "91" + digits
    return f"+{digits}"


def _meta_request(method: str, path: str, data: dict | None = None) -> dict[str, Any]:
    """Make a Graph API request and return parsed JSON."""
    url = f"{META_GRAPH_BASE}/{path}"
    headers = {"Content-Type": "application/json"}
    body = None
    if method == "GET":
        params = urllib.parse.urlencode({"access_token": META_ACCESS_TOKEN})
        url = f"{url}?{params}"
    else:
        payload = dict(data or {})
        payload["access_token"] = META_ACCESS_TOKEN
        body = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode(errors="replace")
        raise RuntimeError(f"Meta API {method} {path} → {exc.code}: {body_text}") from exc


def _get_or_create_audience(name: str) -> str:
    """Return the existing Meta custom audience ID for `name`, or create it."""
    # List existing audiences
    data = _meta_request(
        "GET",
        f"act_{META_AD_ACCOUNT_ID}/customaudiences",
    )
    for audience in data.get("data", []):
        if audience.get("name") == name:
            return str(audience["id"])

    # Create new audience
    result = _meta_request(
        "POST",
        f"act_{META_AD_ACCOUNT_ID}/customaudiences",
        {
            "name": name,
            "subtype": "CUSTOM",
            "description": f"PureLeven CRM auto-sync — {name}",
            "customer_file_source": "USER_PROVIDED_ONLY",
        },
    )
    audience_id = str(result["id"])
    logger.info("meta_audience_sync: created audience '%s' id=%s", name, audience_id)
    return audience_id


def _push_audience_members(audience_id: str, members: list[dict]) -> dict:
    """
    Push hashed members to a Meta custom audience.
    `members` is a list of dicts with keys: email, phone (both optional).
    Returns API response.
    """
    # Build schema + data arrays
    schema = ["EMAIL", "PHONE"]
    data_rows = []
    for m in members:
        email_hash = _sha256(m["email"]) if m.get("email") else ""
        phone_raw = _normalise_phone_e164(m.get("phone"))
        phone_hash = _sha256(phone_raw) if phone_raw else ""
        if email_hash or phone_hash:
            data_rows.append([email_hash, phone_hash])

    if not data_rows:
        return {"skipped": True, "reason": "no_valid_members"}

    # Meta allows max 10k per request
    results = []
    for i in range(0, len(data_rows), 10000):
        chunk = data_rows[i:i + 10000]
        payload = {
            "payload": {
                "schema": schema,
                "data": chunk,
            }
        }
        res = _meta_request("POST", f"{audience_id}/users", payload)
        results.append(res)
        logger.debug("meta_audience_sync: pushed %d members to %s", len(chunk), audience_id)

    return {"chunks": len(results), "total_pushed": len(data_rows)}


# ── Main sync ─────────────────────────────────────────────────────────────────

def sync_meta_audiences() -> dict[str, Any]:
    """
    Main entry point: fetch customers by score tier, hash, and push to Meta.
    Returns a summary dict.
    """
    if not META_ACCESS_TOKEN:
        logger.warning("meta_audience_sync: META_ACCESS_TOKEN not set — skipping")
        return {"ok": False, "reason": "no_access_token"}

    summary: dict[str, Any] = {"ok": True, "tiers": {}}

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT email, phone, whatsapp_number, lead_score
            FROM customers
            WHERE deleted_at IS NULL
              AND (email IS NOT NULL OR phone IS NOT NULL OR whatsapp_number IS NOT NULL)
            """,
        ).fetchall()

    customers = [dict(r) for r in rows]
    logger.info("meta_audience_sync: %d customers loaded", len(customers))

    for audience_name, min_score, max_score in AUDIENCE_TIERS:
        tier_members = [
            {
                "email": c["email"],
                "phone": c["whatsapp_number"] or c["phone"],
            }
            for c in customers
            if min_score <= int(c["lead_score"] or 0) <= max_score
        ]

        if not tier_members:
            summary["tiers"][audience_name] = {"count": 0, "skipped": True}
            continue

        try:
            audience_id = _get_or_create_audience(audience_name)
            result = _push_audience_members(audience_id, tier_members)
            summary["tiers"][audience_name] = {
                "audience_id": audience_id,
                "count": len(tier_members),
                **result,
            }
            logger.info(
                "meta_audience_sync: '%s' → %d members pushed",
                audience_name,
                len(tier_members),
            )
        except Exception as exc:
            logger.error("meta_audience_sync: tier '%s' failed: %s", audience_name, exc)
            summary["tiers"][audience_name] = {"error": str(exc)}
            summary["ok"] = False

    return summary
