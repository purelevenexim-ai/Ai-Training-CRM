"""
Basil Commerce OS — Phase 1
routes/capi.py

Server-side Meta CAPI + GA4 Measurement Protocol relay.
Called by the event gateway worker after storing the event.
Also exposed as a direct webhook endpoint for Razorpay/Shopify order hooks.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger("basil.capi")

META_CAPI_URL = "https://graph.facebook.com/v19.0/{pixel_id}/events"
GA4_MP_URL    = "https://www.google-analytics.com/mp/collect"


# ─── Hashing ─────────────────────────────────────────────────────────────────

def _sha256(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.strip().lower().encode()).hexdigest()


# ─── Meta CAPI ───────────────────────────────────────────────────────────────

def send_to_meta_capi(
    pixel_id: str,
    access_token: str,
    event_name: str,
    event_id: str,
    value: float | None,
    currency: str,
    email: str | None = None,
    phone: str | None = None,
    client_ip: str | None = None,
    client_user_agent: str | None = None,
    fbclid: str | None = None,
    order_id: str | None = None,
    items: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Send a single event to Meta Conversions API.
    Returns the API response dict or an error dict.
    """
    user_data: dict[str, Any] = {}
    if email:
        user_data["em"] = [_sha256(email)]
    if phone:
        user_data["ph"] = [_sha256(phone)]
    if client_ip:
        user_data["client_ip_address"] = client_ip
    if client_user_agent:
        user_data["client_user_agent"] = client_user_agent
    if fbclid:
        user_data["fbc"] = fbclid

    custom_data: dict[str, Any] = {"currency": currency}
    if value is not None:
        custom_data["value"] = value
    if order_id:
        custom_data["order_id"] = order_id
    if items:
        custom_data["contents"] = items
        custom_data["content_type"] = "product"
        custom_data["num_items"]    = len(items)

    payload = {
        "data": [
            {
                "event_name":    event_name,
                "event_time":    int(time.time()),
                "event_id":      event_id,
                "action_source": "website",
                "user_data":     user_data,
                "custom_data":   custom_data,
            }
        ],
        "test_event_code": os.getenv("META_CAPI_TEST_CODE", ""),  # blank in production
    }
    if not payload["test_event_code"]:
        del payload["test_event_code"]

    url  = META_CAPI_URL.format(pixel_id=pixel_id) + f"?access_token={access_token}"
    body = json.dumps(payload).encode()

    try:
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        logger.warning("Meta CAPI HTTP %s: %s", exc.code, exc.read())
        return {"error": str(exc)}
    except Exception as exc:
        logger.warning("Meta CAPI error: %s", exc)
        return {"error": str(exc)}


# ─── GA4 Measurement Protocol ────────────────────────────────────────────────

def send_to_ga4(
    measurement_id: str,
    api_secret: str,
    client_id: str,
    event_name: str,
    params: dict[str, Any],
    user_id: str | None = None,
) -> dict[str, Any]:
    """
    Send a server-side event to GA4 Measurement Protocol.
    """
    payload: dict[str, Any] = {
        "client_id": client_id or "server",
        "events": [{"name": event_name, "params": params}],
    }
    if user_id:
        payload["user_id"] = user_id

    url  = f"{GA4_MP_URL}?measurement_id={measurement_id}&api_secret={api_secret}"
    body = json.dumps(payload).encode()

    try:
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            text = resp.read()
            return json.loads(text) if text else {"status": "ok"}
    except urllib.error.HTTPError as exc:
        logger.warning("GA4 MP HTTP %s", exc.code)
        return {"error": str(exc)}
    except Exception as exc:
        logger.warning("GA4 MP error: %s", exc)
        return {"error": str(exc)}
