"""
app/routes/email_webhooks.py

Email webhook endpoints:
  GET  /api/email/unsubscribe        — One-click unsubscribe link (email footer)
  POST /api/email/send-test          — Send a test email (admin only)
  GET  /api/email/status             — Email delivery configuration status
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.config import settings
from app.storage import get_db_connection

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── Token helpers ────────────────────────────────────────────────────────────

def _generate_unsubscribe_token(customer_id: Any) -> str:
    """Generate an HMAC-based unsubscribe token for a customer ID."""
    secret = settings.admin_secret.encode()
    payload = f"email-unsub:{customer_id}".encode()
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()[:32]


def _verify_unsubscribe_token(customer_id: Any, token: str) -> bool:
    """Verify an unsubscribe token is valid for this customer."""
    expected = _generate_unsubscribe_token(customer_id)
    # Constant-time compare
    return hmac.compare_digest(expected, token)


# ─── Unsubscribe endpoint ─────────────────────────────────────────────────────

@router.get(
    "/email/unsubscribe",
    response_class=HTMLResponse,
    include_in_schema=False,  # Not in API docs — direct link from email footer
)
def email_unsubscribe(
    customer_id: str = Query(..., min_length=1, max_length=100),
    token: str = Query(..., min_length=8, max_length=64),
) -> HTMLResponse:
    """
    Handle one-click email unsubscribe from email footer links.
    Sets do_not_email=1 for the customer.
    Returns a confirmation HTML page.
    """
    # Validate token first
    if not _verify_unsubscribe_token(customer_id, token):
        logger.warning("Invalid unsubscribe token for customer %s", customer_id)
        return HTMLResponse(
            _unsub_page(
                title="Invalid Link",
                message="This unsubscribe link is invalid or has expired. Please contact support if you need assistance.",
                success=False,
            ),
            status_code=400,
        )

    try:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT id, customer_name FROM journey_customers WHERE id = ?",
                (customer_id,),
            ).fetchone()

            if not row:
                logger.warning("Unsubscribe: customer not found %s", customer_id)
                # Still return success (avoids enumeration)
                return HTMLResponse(_unsub_page(
                    title="Unsubscribed",
                    message="You have been removed from our email list.",
                    success=True,
                ))

            name = row["customer_name"] or "there"
            conn.execute(
                "UPDATE journey_customers SET do_not_email = 1, updated_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), customer_id),
            )
            logger.info("Customer %s unsubscribed from email", customer_id)

    except Exception as exc:
        logger.error("Unsubscribe DB error for %s: %s", customer_id, exc)
        return HTMLResponse(
            _unsub_page(
                title="Error",
                message="Something went wrong. Please try again or contact support.",
                success=False,
            ),
            status_code=500,
        )

    return HTMLResponse(_unsub_page(
        title="You've been unsubscribed",
        message=f"Hi {name}, you've been removed from our email list. You won't receive any more marketing emails from PureLeven.",
        success=True,
    ))


def _unsub_page(title: str, message: str, success: bool = True) -> str:
    color = "#2E7D32" if success else "#C62828"
    icon = "✅" if success else "❌"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} — PureLeven</title>
</head>
<body style="margin:0;padding:0;background:#F9FBF9;font-family:Arial,sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;">
  <div style="max-width:480px;width:100%;margin:32px auto;background:#fff;border-radius:12px;box-shadow:0 2px 12px rgba(0,0,0,0.08);overflow:hidden;">
    <div style="background:{color};padding:32px;text-align:center;">
      <span style="font-size:48px;">{icon}</span>
      <h1 style="color:#fff;margin:16px 0 0;font-size:22px;">{title}</h1>
    </div>
    <div style="padding:32px;text-align:center;">
      <p style="font-size:16px;color:#374151;line-height:1.6;margin:0 0 24px;">{message}</p>
      <a href="https://pureleven.com" style="display:inline-block;background:{color};color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-size:15px;font-weight:bold;">
        Visit PureLeven
      </a>
    </div>
  </div>
</body>
</html>"""


# ─── Test email endpoint ──────────────────────────────────────────────────────

class TestEmailRequest(BaseModel):
    to_email: str
    admin_secret: str
    stage: str = "delivered"


@router.post("/email/send-test")
def send_test_email(payload: TestEmailRequest) -> dict[str, Any]:
    """
    Send a test email to a given address. Requires admin secret.
    Useful for validating Google Workspace SMTP credentials.
    """
    if not hmac.compare_digest(payload.admin_secret, settings.admin_secret):
        raise HTTPException(status_code=403, detail="Invalid admin secret")

    from app.services.email_service import send_journey_email

    # Fake customer for template render
    test_customer: dict[str, Any] = {
        "id": "test-001",
        "customer_name": "Test Customer",
        "email_address": payload.to_email,
        "do_not_email": 0,
        "order_id": "PL-TEST-9999",
        "tracking_id": "DEL123456789",
        "carrier": "Delhivery",
        "customer_segment": "vip",
        "unsubscribe_token": _generate_unsubscribe_token("test-001"),
    }

    result = send_journey_email(test_customer, payload.stage)
    return result.to_dict()


# ─── Email config status ──────────────────────────────────────────────────────

@router.get("/email/status")
def email_status() -> dict[str, Any]:
    """Returns email configuration status (without exposing credentials)."""
    email = settings.google_workspace_email or ""
    has_password = bool(settings.google_workspace_app_password)

    return {
        "configured": bool(email and has_password),
        "sender_email": email,
        "sender_name": settings.google_workspace_sender_name,
        "smtp_host": settings.google_smtp_host,
        "smtp_port": settings.google_smtp_port,
        "has_app_password": has_password,
        "status": "ready" if (email and has_password) else "not_configured",
    }
