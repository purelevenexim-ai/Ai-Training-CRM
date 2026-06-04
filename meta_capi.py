"""
Pureleven — Meta Conversions API (CAPI) Integration
Sends server-side purchase events to Meta Graph API v20.

Env vars required:
  META_CAPI_PIXEL_ID        — your pixel ID (e.g. 609256704464862)
  META_CAPI_ACCESS_TOKEN    — system-user access token (never expires unless revoked)

Optional:
  META_CAPI_TEST_CODE       — e.g. "TEST12345"; when set all events are sent as test
                              events so they appear in the Meta Pixel Test Events tab
                              but do NOT count as real conversions.  Remove this var
                              in production.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("pureleven.meta_capi")

PIXEL_ID     = os.getenv("META_CAPI_PIXEL_ID", "")
ACCESS_TOKEN = os.getenv("META_CAPI_ACCESS_TOKEN", "")
TEST_CODE    = os.getenv("META_CAPI_TEST_CODE", "")   # empty string = production mode

GRAPH_API_VERSION = "v20.0"
GRAPH_API_URL     = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PIXEL_ID}/events"


# ── helpers ───────────────────────────────────────────────────────────────────

def _sha256(value: str | None) -> str | None:
    """Return lowercase-stripped SHA-256 hex digest, or None if value is falsy."""
    if not value:
        return None
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


def _normalise_phone(raw: str | None) -> str | None:
    """Return E.164 Indian phone (+91XXXXXXXXXX) for hashing, or None."""
    if not raw:
        return None
    digits = "".join(c for c in str(raw) if c.isdigit())
    if len(digits) < 10:
        return None
    # Ensure country code
    if not digits.startswith("91") or len(digits) == 10:
        digits = "91" + digits[-10:]
    return "+" + digits


def _is_configured() -> bool:
    return bool(PIXEL_ID and ACCESS_TOKEN)


# ── core sender ───────────────────────────────────────────────────────────────

def send_event(
    event_name: str,
    event_id: str,
    event_time: int,
    event_source_url: str,
    user_data: dict[str, Any],
    custom_data: dict[str, Any],
    action_source: str = "website",
) -> dict[str, Any]:
    """
    Low-level: POST a single event to the Graph API.
    Returns the parsed JSON response dict, or {'error': '...'} on failure.
    """
    if not _is_configured():
        logger.info("Meta CAPI: not configured (missing PIXEL_ID or ACCESS_TOKEN)")
        return {"status": "skipped", "reason": "not_configured"}

    payload: dict[str, Any] = {
        "data": [
            {
                "event_name":       event_name,
                "event_id":         event_id,
                "event_time":       event_time,
                "event_source_url": event_source_url,
                "action_source":    action_source,
                "user_data":        {k: v for k, v in user_data.items() if v is not None},
                "custom_data":      custom_data,
            }
        ]
    }
    if TEST_CODE:
        payload["test_event_code"] = TEST_CODE

    body = json.dumps(payload).encode("utf-8")
    url = f"{GRAPH_API_URL}?access_token={ACCESS_TOKEN}"

    try:
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            logger.info("Meta CAPI event=%s id=%s result=%s", event_name, event_id, data)
            return data
    except urllib.error.HTTPError as exc:
        body_err = exc.read().decode("utf-8", errors="ignore")
        logger.warning("Meta CAPI HTTP %s event=%s id=%s: %s", exc.code, event_name, event_id, body_err)
        return {"error": f"HTTP {exc.code}", "detail": body_err}
    except Exception as exc:
        logger.warning("Meta CAPI request error event=%s id=%s: %s", event_name, event_id, exc)
        return {"error": str(exc)}


# ── public API ────────────────────────────────────────────────────────────────

def send_purchase(
    order_id: str,
    value: float,
    currency: str,
    *,
    email: str | None = None,
    phone: str | None = None,
    items: list[dict] | None = None,
    client_ip: str | None = None,
    client_user_agent: str | None = None,
    fbclid: str | None = None,
    fbp: str | None = None,
    fbc: str | None = None,
    event_name: str = "Purchase",
    event_source_url: str = "https://pureleven.com/",
    order_time: datetime | None = None,
) -> dict[str, Any]:
    """
    Send a Purchase (or other order-level) event to Meta CAPI.

    Parameters
    ----------
    order_id        Shopify order ID (used as external_id + event_id base).
    value           Order total (float).
    currency        ISO 4217, e.g. "INR".
    email           Customer email — will be SHA-256 hashed.
    phone           Raw phone number — normalised to E.164 then hashed.
    items           List of {id, quantity, item_price, title} dicts.
    client_ip       Browser IP at checkout time (from the Shopify webhook request).
    client_user_agent Browser user-agent string.
    fbclid          Facebook click ID captured at landing.
    fbp             _fbp cookie value (format: fb.1.<timestamp>.<random>).
    fbc             _fbc cookie value or constructed from fbclid.
    event_name      Defaults to "Purchase"; override with "InitiateCheckout" etc.
    event_source_url Full URL of the conversion page.
    order_time      Order creation datetime; defaults to now.
    """
    event_time = int((order_time or datetime.now(timezone.utc)).timestamp())

    # Build user_data — every identifier improves match quality
    user_data: dict[str, Any] = {}

    if email:
        user_data["em"] = _sha256(email)
    if phone:
        normalised_phone = _normalise_phone(phone)
        if normalised_phone:
            user_data["ph"] = _sha256(normalised_phone)
    if client_ip:
        user_data["client_ip_address"] = client_ip
    if client_user_agent:
        user_data["client_user_agent"] = client_user_agent
    if fbp:
        user_data["fbp"] = fbp
    if fbc:
        user_data["fbc"] = fbc
    elif fbclid:
        # Construct fbc from fbclid with the order timestamp as the click timestamp
        user_data["fbc"] = f"fb.1.{event_time * 1000}.{fbclid}"

    # external_id — stable customer identifier for cross-device stitching
    if email:
        user_data["external_id"] = _sha256(email)
    elif order_id:
        user_data["external_id"] = _sha256(f"order_{order_id}")

    # Build custom_data
    contents = [
        {
            "id":         str(item.get("id", "")),
            "quantity":   int(item.get("quantity", 1)),
            "item_price": float(item.get("item_price", 0)),
            "title":      str(item.get("title", "")),
        }
        for item in (items or [])
    ]

    custom_data: dict[str, Any] = {
        "value":        value,
        "currency":     currency,
        "content_type": "product",
        "order_id":     order_id,
    }
    if contents:
        custom_data["contents"] = contents
        custom_data["num_items"] = sum(c["quantity"] for c in contents)

    event_id = f"purchase_{order_id}"

    return send_event(
        event_name=event_name,
        event_id=event_id,
        event_time=event_time,
        event_source_url=event_source_url,
        user_data=user_data,
        custom_data=custom_data,
    )


def health_check() -> dict[str, Any]:
    """
    Non-destructive CAPI health check.
    Verifies credentials are set and the pixel ID resolves without sending a real event.
    """
    if not _is_configured():
        return {"status": "not_configured", "pixel_id": PIXEL_ID or "(missing)", "token_set": bool(ACCESS_TOKEN)}

    # Minimal test: call /debug_token to verify the access token is valid
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/debug_token?input_token={ACCESS_TOKEN}&access_token={ACCESS_TOKEN}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            token_data = data.get("data", {})
            return {
                "status": "ok" if token_data.get("is_valid") else "token_invalid",
                "pixel_id": PIXEL_ID,
                "token_valid": token_data.get("is_valid"),
                "app_id": token_data.get("app_id"),
                "expires_at": token_data.get("expires_at"),  # 0 = never expires (system user)
                "test_mode": bool(TEST_CODE),
            }
    except Exception as exc:
        return {"status": "check_failed", "error": str(exc)}
