"""
Basil Commerce OS — Phase 5
wabis_client.py

WhatsApp sender — uses Meta Graph API (primary) for correct {{1}} variable
substitution, falling back to Wabis form-encoded API when Meta is unavailable.

Meta API advantage: properly substitutes template variables from body_params.
Wabis pulls variables from subscriber DB, so a subscriber record must exist.
"""

from __future__ import annotations

import json
import logging
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

try:
    import certifi
    _SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CONTEXT = ssl.create_default_context()

from app.config import settings
from app.whatsapp_delivery_validator import validate_template_send

# Language codes for templates not using the "en" default
_TEMPLATE_LANGUAGES: dict[str, str] = {
    "shopify_abandonded_checkout_remainder_240": "en_US",
    "shopify_abandonaded_cart_remainder":         "en_GB",
    "order_management_1":                         "en_GB",
    "shopify_order_shipped":                      "en_US",
    "pl_shopify_order_create":                    "en_IN",
    "system_abandoned_cart_reminder_new":          "en_US",
    "system_abandoned_cart_reminder_coupon_new":   "en_US",
    "system_cod_order_verification_new":           "en_US",
    "system_order_success_notification_new":       "en_US",
    "hello_world":                                 "en_US",
}

logger = logging.getLogger(__name__)

# Correct Wabis base URL and phone number ID
WABIS_BASE_URL = "https://bot.wabis.in/api/v1/whatsapp"

# Cache for template list: {name -> id}, refreshed every 30 minutes
_template_cache: dict[str, int] = {}
_template_cache_ts: float = 0.0
_TEMPLATE_CACHE_TTL = 1800  # 30 minutes


# ─── Exceptions ───────────────────────────────────────────────────────────────

class WabisError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Wabis {status_code}: {detail}")


# ─── Template ID lookup ───────────────────────────────────────────────────────

def _get_template_id(api_key: str, template_name: str) -> int | None:
    """Look up a Wabis internal template_id by template name (cached)."""
    global _template_cache, _template_cache_ts

    if time.time() - _template_cache_ts < _TEMPLATE_CACHE_TTL and _template_cache:
        return _template_cache.get(template_name)

    phone_number_id = settings.wabis_phone_number_id
    if not phone_number_id:
        logger.warning("WABIS_PHONE_NUMBER_ID not set — cannot refresh Wabis template cache")
        return _template_cache.get(template_name)

    params = urllib.parse.urlencode({
        "apiToken": api_key,
        "phone_number_id": phone_number_id,
    })
    url = f"{WABIS_BASE_URL}/template/list?{params}"
    try:
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json", "User-Agent": "curl/7.88.1"},
        )
        with urllib.request.urlopen(req, timeout=10, context=_SSL_CONTEXT) as resp:  # noqa: S310
            data: dict[str, Any] = json.loads(resp.read())
        templates = data.get("message", [])
        if isinstance(templates, list):
            _template_cache = {
                t["template_name"]: t["id"]
                for t in templates
                if isinstance(t, dict) and t.get("template_name") and t.get("id")
            }
            _template_cache_ts = time.time()
            logger.info("Wabis template cache refreshed: %d templates", len(_template_cache))
    except Exception as exc:
        logger.warning("Wabis template list fetch failed: %s", exc)

    return _template_cache.get(template_name)


# ─── Core send ────────────────────────────────────────────────────────────────

def send_template_message(
    phone: str,
    template_name: str,
    body_params: list[str] | None = None,
    button_params: list[dict[str, Any]] | None = None,
    language_code: str = "en",
    template_id: int | None = None,
    shop_domain: str = "rwxtic-gz.myshopify.com",
) -> dict[str, Any]:
    """
    Send a WhatsApp template message.

    Tries Meta Graph API first (correct {{1}} substitution from body_params).
    Falls back to Wabis form-encoded API if Meta credentials are unavailable
    or Meta returns a non-recoverable error.

    Args:
        phone:         E.164 digits, e.g. "919876543210"
        template_name: Approved Meta/Wabis template name
        body_params:   Ordered text values for {{1}}, {{2}}, ...
        button_params: Button component overrides for dynamic URL buttons
        language_code: Override language; auto-detected from template name if "en"
        template_id:   Wabis internal template_id override (Wabis fallback only)
        shop_domain:   Shopify shop domain for customer lookup

    Returns:
        Parsed response dict with "messages", "status", ...
    """
    # ── Validate delivery eligibility ──────────────────────────────────────────
    can_send, reason = validate_template_send(phone, template_name, shop_domain)
    if not can_send:
        logger.warning(
            "❌ Marketing message blocked: phone=%s template=%s reason=%s",
            phone, template_name, reason,
        )
        return {
            "status": "delivery_blocked",
            "error": reason,
            "phone": phone,
            "template": template_name,
            "messages": [],
        }

    logger.info(
        "✅ Message eligible for delivery: phone=%s template=%s reason=%s",
        phone, template_name, reason,
    )

    # ── Try Meta Graph API first ──────────────────────────────────────────────
    if settings.meta_access_token and settings.meta_phone_number_id:
        from app.meta_client import MetaAPIError, send_template_message as meta_send  # noqa: PLC0415
        lang = language_code if language_code != "en" else _TEMPLATE_LANGUAGES.get(template_name, "en")
        try:
            return meta_send(
                phone=phone,
                template_name=template_name,
                language_code=lang,
                body_params=body_params,
                button_params=button_params,
            )
        except MetaAPIError as exc:
            logger.warning(
                "Meta API error (code=%s) for template=%s phone=%s — falling back to Wabis: %s",
                exc.status_code, template_name, phone, exc.detail[:120],
            )

    # ── Wabis fallback ────────────────────────────────────────────────────────
    api_key = settings.wabis_api_key
    if not api_key:
        logger.warning(
            "Neither META_ACCESS_TOKEN nor WABIS_API_KEY set — dev stub: phone=%s template=%s",
            phone, template_name,
        )
        return {
            "status": "dev_stub",
            "phone": phone,
            "template": template_name,
            "messages": [{"id": f"stub_{template_name}_{phone[-4:]}"}],
        }

    # Resolve template_id
    tid = template_id or _get_template_id(api_key, template_name)
    if not tid:
        raise WabisError(404, f"Template '{template_name}' not found in Wabis account")

    phone_number_id = settings.wabis_phone_number_id
    if not phone_number_id:
        raise WabisError(503, "WABIS_PHONE_NUMBER_ID not configured")

    # Build form-encoded payload
    send_params: dict[str, Any] = {
        "apiToken": api_key,
        "phone_number_id": phone_number_id,
        "phone_number": phone.lstrip("+"),
        "template_id": tid,
    }

    # Add body variable params as param1, param2, ...
    if body_params:
        for i, val in enumerate(body_params, 1):
            send_params[f"param{i}"] = str(val)

    form_data = urllib.parse.urlencode(send_params).encode()

    req = urllib.request.Request(
        f"{WABIS_BASE_URL}/send/template",
        data=form_data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "curl/7.88.1",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15, context=_SSL_CONTEXT) as resp:  # noqa: S310
            response_data: dict[str, Any] = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        logger.error("Wabis HTTP %s: %s", exc.code, body[:400])
        raise WabisError(exc.code, body) from exc
    except urllib.error.URLError as exc:
        logger.error("Wabis network error: %s", exc.reason)
        raise WabisError(503, str(exc.reason)) from exc

    # Wabis returns HTTP 200 even on logical failure; status "1" = success
    if str(response_data.get("status", "0")) != "1":
        err_msg = response_data.get("message", "Unknown Wabis error")
        logger.warning("Wabis logical failure: template=%s phone=%s error=%s", template_name, phone, err_msg)
        raise WabisError(400, err_msg)

    logger.info("Wabis sent: phone=%s template=%s wa_id=%s", phone, template_name,
                response_data.get("wa_message_id", ""))
    return {
        "messages": [{"id": response_data.get("wa_message_id", "")}],
        "status": "sent",
        **response_data,
    }


def extract_message_id(response: dict[str, Any]) -> str | None:
    """Pull message ID from Wabis API response."""
    return (
        response.get("wa_message_id")
        or next((str(m.get("id", "")) for m in response.get("messages", []) if m.get("id")), None)
        or response.get("message_id")
        or response.get("id")
        or None
    )
