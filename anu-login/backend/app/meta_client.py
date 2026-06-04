"""
Basil Commerce OS — Phase 5
meta_client.py

Direct Meta Graph API WhatsApp sender.
Bypasses Wabis's subscriber-DB variable lookup bug by calling Meta directly.
Properly substitutes {{1}}, {{2}}, ... from body_params.

Requires in .env:
  META_ACCESS_TOKEN=<system-user token with whatsapp_business_messaging scope>
  META_PHONE_NUMBER_ID=<phone number id>
"""

from __future__ import annotations

import json
import logging
import ssl
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

logger = logging.getLogger(__name__)

META_GRAPH_API_VERSION = "v20.0"
META_GRAPH_BASE = f"https://graph.facebook.com/{META_GRAPH_API_VERSION}"


# ─── Exception ────────────────────────────────────────────────────────────────

class MetaAPIError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Meta API {status_code}: {detail}")


# ─── Core send ────────────────────────────────────────────────────────────────

def send_template_message(
    phone: str,
    template_name: str,
    language_code: str = "en",
    body_params: list[str] | None = None,
    button_params: list[dict[str, Any]] | None = None,
    shop_domain: str = "rwxtic-gz.myshopify.com",
) -> dict[str, Any]:
    """
    Send a WhatsApp template message directly via Meta Graph API.

    Properly substitutes {{1}}, {{2}}, ... from body_params.
    Button params: list of {sub_type, index, parameters} dicts for dynamic URL buttons.

    Args:
        phone:         Digits only, e.g. "919876543210"
        template_name: Approved Meta template name (e.g. "order_confirmed_v1")
        language_code: Meta language code (default "en")
        body_params:   Text values for {{1}}, {{2}}, ... in template body
        button_params: Button component overrides for dynamic URL suffix buttons
        shop_domain:   Shopify shop domain for customer lookup

    Returns:
        {"messages": [{"id": wamid}], "status": "sent", "contacts": [...]}
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

    # ── Build Meta API request ────────────────────────────────────────────────
    access_token = settings.meta_access_token
    phone_number_id = settings.meta_phone_number_id

    if not access_token:
        logger.warning(
            "META_ACCESS_TOKEN not set — dev stub: phone=%s template=%s",
            phone, template_name,
        )
        return {
            "status": "dev_stub",
            "phone": phone,
            "template": template_name,
            "messages": [{"id": f"stub_{template_name}_{phone[-4:]}"}],
        }
    if not phone_number_id:
        return {
            "status": "error",
            "error": "META_PHONE_NUMBER_ID not configured",
            "phone": phone,
            "template": template_name,
            "messages": [],
        }

    # Build component list
    components: list[dict[str, Any]] = []

    if body_params:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": str(v)} for v in body_params],
        })

    if button_params:
        for btn in button_params:
            components.append({
                "type": "button",
                **btn,
            })

    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": phone.lstrip("+"),
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
        },
    }
    if components:
        payload["template"]["components"] = components

    url = f"{META_GRAPH_BASE}/{phone_number_id}/messages"
    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "PurelevenBot/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15, context=_SSL_CONTEXT) as resp:  # noqa: S310
            response_data: dict[str, Any] = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
            detail = err_json.get("error", {}).get("message", err_body)
        except json.JSONDecodeError:
            detail = err_body[:300]
        logger.error("Meta API HTTP %s for template=%s phone=%s: %s", exc.code, template_name, phone, detail[:200])
        raise MetaAPIError(exc.code, detail) from exc
    except urllib.error.URLError as exc:
        logger.error("Meta API network error: %s", exc.reason)
        raise MetaAPIError(503, str(exc.reason)) from exc

    wamid = ""
    msgs = response_data.get("messages", [])
    if msgs:
        wamid = msgs[0].get("id", "")

    logger.info(
        "Meta API sent: phone=%s template=%s lang=%s wamid=%s",
        phone, template_name, language_code, wamid,
    )
    return {
        "messages": [{"id": wamid}],
        "status": "sent",
        **response_data,
    }


def send_image_message(
    phone: str,
    image_url: str,
    caption: str = "",
) -> dict[str, Any]:
    """Send a WhatsApp image message directly via Meta Graph API."""
    access_token = settings.meta_access_token
    phone_number_id = settings.meta_phone_number_id

    if not access_token:
        logger.warning(
            "META_ACCESS_TOKEN not set — dev stub image send: phone=%s url=%s",
            phone,
            image_url,
        )
        return {
            "status": "dev_stub",
            "phone": phone,
            "image_url": image_url,
            "messages": [{"id": f"stub_image_{phone[-4:]}"}],
        }
    if not phone_number_id:
        return {
            "status": "error",
            "error": "META_PHONE_NUMBER_ID not configured",
            "phone": phone,
            "image_url": image_url,
            "messages": [],
        }

    payload: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "to": phone.lstrip("+"),
        "type": "image",
        "image": {
            "link": image_url,
        },
    }
    if caption.strip():
        payload["image"]["caption"] = caption.strip()

    url = f"{META_GRAPH_BASE}/{phone_number_id}/messages"
    body = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "PurelevenBot/1.0",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=15, context=_SSL_CONTEXT) as resp:  # noqa: S310
            response_data: dict[str, Any] = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        try:
            err_json = json.loads(err_body)
            detail = err_json.get("error", {}).get("message", err_body)
        except json.JSONDecodeError:
            detail = err_body[:300]
        logger.error("Meta API HTTP %s for image phone=%s: %s", exc.code, phone, detail[:200])
        raise MetaAPIError(exc.code, detail) from exc
    except urllib.error.URLError as exc:
        logger.error("Meta API network error (image): %s", exc.reason)
        raise MetaAPIError(503, str(exc.reason)) from exc

    wamid = ""
    msgs = response_data.get("messages", [])
    if msgs:
        wamid = msgs[0].get("id", "")

    logger.info(
        "Meta API image sent: phone=%s url=%s wamid=%s",
        phone,
        image_url,
        wamid,
    )
    return {
        "messages": [{"id": wamid}],
        "status": "sent",
        **response_data,
    }


def extract_message_id(response: dict[str, Any]) -> str | None:
    """Pull wamid from Meta API response."""
    msgs = response.get("messages", [])
    if msgs:
        return msgs[0].get("id") or None
    return None
