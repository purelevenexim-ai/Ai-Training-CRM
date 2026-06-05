"""Shared WhatsApp delivery helpers with template fallback.

Freeform text replies work only inside the customer care window. When Wabis
rejects a freeform send because the session is outside the 24-hour window, we
fall back to an approved template so the customer still gets a useful reply.
"""

from __future__ import annotations

import logging
from typing import Any

from app.ai.pricing_formatter import PricingFormatter
from app.ai.response_quality_guard import guard_whatsapp_reply
from app.meta_client import MetaAPIError, send_image_message as send_meta_image_message
from app.ai.wabis_api_client import WabisAPIClient
from app.url_config import URLConfig
from app.wabis_client import send_template_message as send_template_via_provider
from app.services.product_media_service import to_public_url

logger = logging.getLogger(__name__)

_PRODUCT_URLS: dict[str, str] = {
    "cardamom": "https://pureleven.com/products/green-cardamom-100g",
    "pepper": "https://pureleven.com/products/kerala-black-pepper-200gm",
    "cinnamon": "https://pureleven.com/products/premium-cassia-cinnamon-200g",
    "clove": "https://pureleven.com/products/premium-cloves-100g",
    "turmeric": "https://pureleven.com/products/kerala-turmeric-100g",
    "combo": "https://pureleven.com/products/spice-combo-pack",
}


def _looks_like_session_window_block(error_text: str) -> bool:
    lowered = (error_text or "").lower()
    return any(
        phrase in lowered
        for phrase in (
            "outside 24 hour window",
            "outside 24-hour window",
            "24 hour window",
            "24-hour window",
            "only send template message",
            "template message",
        )
    )


def _extract_product_key(reply_result: dict[str, Any] | None) -> str | None:
    reply_result = reply_result or {}
    intent = str(reply_result.get("intent") or "").strip().lower()
    if intent.startswith("product_"):
        return intent.replace("product_", "", 1)

    understanding = reply_result.get("message_understanding") or {}
    product = str(understanding.get("product") or "").strip().lower()
    if product:
        return product
    return None


def _product_display_name(product_key: str | None) -> str:
    if not product_key:
        return "our products"
    catalog = PricingFormatter.get_product_catalog_entry(product_key) or {}
    return str(catalog.get("display_name") or product_key.title())


def _product_url(product_key: str | None) -> str:
    if not product_key:
        return URLConfig.get_product_link("spices", utm_source="whatsapp")
    return _PRODUCT_URLS.get(product_key, URLConfig.get_product_link("spices", utm_source="whatsapp"))


def _template_fallback_payload(
    reply_result: dict[str, Any] | None,
    customer_name: str,
) -> tuple[str, list[str]]:
    reply_result = reply_result or {}
    intent = str(reply_result.get("intent") or "").strip().lower()
    product_key = _extract_product_key(reply_result)
    customer_label = (customer_name or "there").strip() or "there"

    if intent == "wholesale_inquiry":
        return (
            "corporate_followup_v1",
            [
                customer_label,
                URLConfig.get_bulk_order_link(utm_source="whatsapp"),
            ],
        )

    if product_key == "turmeric":
        product_url = _product_url(product_key)
        return (
            "explore_products_v1",
            [
                customer_label,
                _product_display_name(product_key),
                product_url,
                "EXPLORE20",
            ],
        )

    if product_key:
        return (
            "explore_products_v1",
            [
                customer_label,
                _product_display_name(product_key),
                _product_url(product_key),
                "EXPLORE20",
            ],
        )

    return (
        "explore_products_v1",
        [
            customer_label,
            "Pureleven spices",
            URLConfig.get_product_link("spices", utm_source="whatsapp"),
            "EXPLORE20",
        ],
    )


def send_whatsapp_reply_with_fallback(
    phone_number: str,
    message_text: str,
    conversation_id: str = "",
    reply_result: dict[str, Any] | None = None,
    customer_name: str = "Customer",
    media_urls: list[str] | None = None,
    media_caption: str = "",
    media_only: bool = False,
) -> dict[str, Any]:
    """Send a WhatsApp reply, falling back to an approved template if needed."""
    guard = guard_whatsapp_reply(
        customer_id=phone_number,
        inbound_message=str((reply_result or {}).get("message_understanding", {}).get("normalized_message") or ""),
        generated_reply=message_text,
        reply_result=reply_result,
        final_reply=message_text,
        allow_empty=media_only and not message_text,
    )
    if guard.action == "blocked":
        logger.warning("[WHATSAPP-GUARD] %s blocked reply: %s", phone_number, guard.issues_found)
        return {
            "success": False,
            "mode": "guard_blocked",
            "error": guard.blocked_reason or "guard_blocked",
            "issues_found": guard.issues_found,
            "media_results": [],
            "media_urls": [],
        }

    message_text = guard.final_reply or message_text
    reply_media_urls = media_urls if media_urls is not None else (reply_result.get("image_urls") if reply_result else [])
    normalized_media_urls = [to_public_url(url) for url in (reply_media_urls or [])]
    media_results: list[dict[str, Any]] = []
    media_error: str | None = None

    def send_images_after_text() -> None:
        nonlocal media_error
        for index, media_url in enumerate(normalized_media_urls):
            if not media_url:
                continue
            try:
                image_result = send_meta_image_message(
                    phone=phone_number,
                    image_url=media_url,
                    caption=media_caption if index == 0 else "",
                )
                media_results.append(image_result)
            except MetaAPIError as exc:
                media_error = exc.detail
                logger.warning("[WHATSAPP-MEDIA] %s image send failed: %s", phone_number, exc.detail)
                break
            except Exception as exc:
                media_error = str(exc)
                logger.warning("[WHATSAPP-MEDIA] %s image send failed: %s", phone_number, exc)
                break

    if normalized_media_urls and media_only:
        send_images_after_text()
        if media_only and media_results:
            return {
                "success": True,
                "mode": "media",
                "message_id": media_results[-1].get("messages", [{}])[0].get("id"),
                "wabis_response": media_results[-1],
                "media_results": media_results,
                "media_urls": normalized_media_urls,
            }
        if media_only and not media_results:
            return {
                "success": False,
                "mode": "media_failed",
                "error": media_error or "Media send failed",
                "media_results": media_results,
                "media_urls": normalized_media_urls,
            }
    elif media_only:
        return {
            "success": False,
            "mode": "media_failed",
            "error": "No media URLs supplied",
            "media_results": media_results,
            "media_urls": normalized_media_urls,
        }

    text_result = WabisAPIClient.send_text_message(
        phone_number=phone_number,
        message_text=message_text,
        conversation_id=conversation_id,
    )
    if text_result.get("success"):
        if normalized_media_urls:
            send_images_after_text()
        return {
            **text_result,
            "mode": "media+freeform" if media_results else "freeform",
            "media_results": media_results,
            "media_urls": normalized_media_urls,
        }

    error_text = str(text_result.get("error") or "")
    if not _looks_like_session_window_block(error_text):
        if media_results:
            return {
                "success": True,
                "mode": "media_partial",
                "text_error": error_text,
                "media_results": media_results,
                "media_urls": normalized_media_urls,
                "media_error": media_error,
                "wabis_response": text_result,
            }
        return {
            **text_result,
            "mode": "freeform_failed",
            "media_results": media_results,
            "media_urls": normalized_media_urls,
            "media_error": media_error,
        }

    template_name, body_params = _template_fallback_payload(reply_result, customer_name)
    logger.warning(
        "[WHATSAPP-FALLBACK] %s blocked freeform reply; trying template=%s",
        phone_number,
        template_name,
    )

    template_result = send_template_via_provider(
        phone=phone_number,
        template_name=template_name,
        body_params=body_params,
    )
    if template_result.get("status") == "sent":
        if normalized_media_urls:
            send_images_after_text()
        return {
            "success": True,
            "mode": "template",
            "template_name": template_name,
            "message_id": (
                template_result.get("messages", [{}])[0].get("id")
                if isinstance(template_result.get("messages"), list)
                else None
            ),
            "wabis_response": template_result,
            "fallback_error": error_text,
            "media_results": media_results,
            "media_urls": normalized_media_urls,
        }

    return {
        "success": False,
        "mode": "template_failed",
        "error": template_result.get("error") or error_text,
        "template_name": template_name,
        "fallback_error": error_text,
        "wabis_response": template_result,
        "media_results": media_results,
        "media_urls": normalized_media_urls,
        "media_error": media_error,
    }
