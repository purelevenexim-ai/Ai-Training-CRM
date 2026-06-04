"""
WhatsApp message delivery validator.

Enforces Meta's messaging rules for pre-approved template (HSM) messages:
  - ALL template categories (MARKETING, TRANSACTIONAL, UTILITY, AUTHENTICATION):
    Can be sent at ANY time — the 24-hour window only applies to free-form
    session messages, NOT to approved templates.
  - Only hard blocks: customer explicitly unsubscribed (STOP) from this business.

The 24-hour conversation window is irrelevant for template messages because
Meta approves them in advance to allow anytime delivery to opted-in users.
"""

from __future__ import annotations

import logging

from app.storage import get_db_connection
from app.whatsapp_templates import REGISTRY

logger = logging.getLogger(__name__)


def _is_unsubscribed(phone: str, shop_domain: str) -> tuple[bool, str]:
    """
    Return (True, reason) if the customer has explicitly unsubscribed.
    All other cases return (False, '') — including unknown customers.
    """
    try:
        conn = get_db_connection()
        normalized = "".join(c for c in phone if c.isdigit()).lstrip("+")
        row = conn.execute(
            """
            SELECT whatsapp_unsubscribed_at
            FROM customers
            WHERE phone LIKE ? OR phone LIKE ?
            LIMIT 1
            """,
            (f"%{normalized[-10:]}", f"%{normalized}"),
        ).fetchone()

        if row and row[0]:
            return True, f"Customer unsubscribed from WhatsApp messages ({row[0]})"

        return False, ""

    except Exception as exc:
        logger.error("Unsubscribe check failed for %s: %s", phone, exc)
        # Fail open — don't silently block messages due to a DB error
        return False, ""


def validate_template_send(
    phone: str,
    template_name: str,
    shop_domain: str = "rwxtic-gz.myshopify.com",
) -> tuple[bool, str]:
    """
    Check if a pre-approved template message can be sent.

    All template categories (MARKETING, TRANSACTIONAL, UTILITY) are allowed
    at any time. The only block is an explicit customer unsubscribe.

    Returns:
        (can_send: bool, reason: str)
    """
    spec = REGISTRY.get(template_name)
    if not spec:
        return False, f"Template '{template_name}' not found in registry"

    unsubscribed, reason = _is_unsubscribed(phone, shop_domain)
    if unsubscribed:
        return False, reason

    return True, f"{spec.category} template — delivery allowed"


# Retained for backwards compatibility — not used for blocking decisions
def can_send_marketing_message(phone: str, shop_domain: str) -> tuple[bool, str]:
    """Deprecated: 24-hour window check is not applicable to template messages."""
    return validate_template_send(phone, "repeat_buyer_exclusive_v1", shop_domain)


def get_template_category(template_name: str) -> str | None:
    """Get template category (MARKETING, TRANSACTIONAL, etc.)."""
    spec = REGISTRY.get(template_name)
    return spec.category if spec else None
