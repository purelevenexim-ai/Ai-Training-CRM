"""
app/services/email_service.py

Google Workspace SMTP email delivery service.

Usage:
    from app.services.email_service import send_journey_email, send_email

All calls are synchronous (smtplib). Called from journey_orchestrator.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import smtplib
import ssl
import time
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

import certifi

from app.config import settings

logger = logging.getLogger(__name__)


def _generate_unsubscribe_token(customer_id: Any) -> str:
    payload = f"email-unsub:{customer_id}".encode()
    return hmac.new(settings.admin_secret.encode(), payload, hashlib.sha256).hexdigest()[:32]


def _display_name(customer: dict[str, Any]) -> str:
    full_name = " ".join(
        part for part in [customer.get("first_name"), customer.get("last_name")] if str(part or "").strip()
    ).strip()
    return (
        str(customer.get("customer_name") or "").strip()
        or str(customer.get("name") or "").strip()
        or full_name
        or "there"
    )


def _normalized_customer_context(customer: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(customer)
    customer_id = customer.get("id") or customer.get("customer_id") or "anon"
    normalized["email_address"] = (
        str(customer.get("email_address") or "").strip()
        or str(customer.get("email") or "").strip()
    )
    normalized["customer_name"] = _display_name(customer)
    normalized["order_id"] = (
        str(customer.get("order_id") or "").strip()
        or str(customer.get("shopify_order_id") or "").strip()
    )
    normalized["tracking_id"] = (
        str(customer.get("tracking_id") or "").strip()
        or str(customer.get("waybill_id") or "").strip()
    )
    normalized["carrier"] = str(customer.get("carrier") or "").strip() or "Delhivery"
    normalized["customer_segment"] = (
        str(customer.get("customer_segment") or "").strip()
        or str(customer.get("segment") or "").strip()
        or "new"
    )
    normalized["unsubscribe_token"] = (
        str(customer.get("unsubscribe_token") or "").strip()
        or _generate_unsubscribe_token(customer_id)
    )
    return normalized


# ─── Result dataclass ─────────────────────────────────────────────────────────

class EmailResult:
    def __init__(
        self,
        success: bool,
        to_email: str,
        subject: str = "",
        error: str | None = None,
        attempt: int = 1,
    ) -> None:
        self.success = success
        self.to_email = to_email
        self.subject = subject
        self.error = error
        self.attempt = attempt
        self.sent_at = datetime.now(timezone.utc).isoformat()

    @property
    def status(self) -> str:
        return "sent" if self.success else "failed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status,
            "to_email": self.to_email,
            "subject": self.subject,
            "error": self.error,
            "attempt": self.attempt,
            "sent_at": self.sent_at,
        }


# ─── Error classification ─────────────────────────────────────────────────────

def classify_smtp_error(error_str: str | None) -> str:
    """Classify an SMTP error string into: hard | soft | transient."""
    if not error_str:
        return "transient"
    err = error_str.lower()
    # Hard bounce — permanent address failure
    if any(kw in err for kw in [
        "recipient refused", "no such user", "user unknown", "does not exist",
        "invalid recipient", "mailbox not found", "address rejected",
        "550", "551", "552", "553", "554",
    ]):
        return "hard"
    # Soft bounce — temporary mailbox issue
    if any(kw in err for kw in [
        "mailbox full", "over quota", "insufficient storage", "452",
        "temporarily unavailable", "try again later",
    ]):
        return "soft"
    # Everything else is transient (network, auth, timeout)
    return "transient"


# ─── Core sender ─────────────────────────────────────────────────────────────

def _build_smtp_connection() -> smtplib.SMTP:
    """Open an authenticated SMTP TLS connection to Google Workspace."""
    host = settings.google_smtp_host
    port = settings.google_smtp_port
    ctx = ssl.create_default_context(cafile=certifi.where())

    smtp = smtplib.SMTP(host, port, timeout=15)
    smtp.ehlo()
    smtp.starttls(context=ctx)
    smtp.ehlo()
    smtp.login(settings.google_workspace_email, settings.google_workspace_app_password)
    return smtp


def _send_raw(to_email: str, subject: str, html_body: str, text_body: str = "", campaign_id: str = "") -> None:
    """Build MIME message and dispatch over SMTP. Raises on failure."""
    from_addr = settings.google_workspace_email
    from_name = settings.google_workspace_sender_name
    domain = from_addr.split("@")[-1] if "@" in from_addr else "pureleven.com"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{from_addr}>"
    msg["To"] = to_email
    msg["Reply-To"] = from_addr
    msg["Message-ID"] = f"<{uuid.uuid4().hex}@{domain}>"

    # RFC 2369 / RFC 2919 bulk/list compliance headers
    unsubscribe_url = f"{settings.public_base_url}/api/email/unsubscribe"
    msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"
    msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    list_id_slug = f"promotions.{domain}"
    if campaign_id:
        list_id_slug = f"{campaign_id}.{domain}"
    msg["List-ID"] = f"PureLeven Promotions <{list_id_slug}>"
    msg["Precedence"] = "bulk"
    msg["X-Mailer"] = "PureLeven-CRM/1.0"

    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    with _build_smtp_connection() as smtp:
        smtp.sendmail(from_addr, [to_email], msg.as_string())


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str = "",
    retries: int = 2,
    campaign_id: str = "",
) -> EmailResult:
    """
    Send an email with retry logic and error classification.
    Hard/soft bounce errors are not retried.
    """
    last_error: str | None = None

    for attempt in range(1, retries + 1):
        try:
            _send_raw(to_email, subject, html_body, text_body, campaign_id=campaign_id)
            logger.info("Email sent to %s (attempt %d): %s", to_email, attempt, subject)
            return EmailResult(success=True, to_email=to_email, subject=subject, attempt=attempt)
        except smtplib.SMTPAuthenticationError as exc:
            logger.error("SMTP auth failed — check GOOGLE_WORKSPACE_APP_PASSWORD: %s", exc)
            return EmailResult(
                success=False, to_email=to_email, subject=subject,
                error=f"SMTP auth error: {exc}", attempt=attempt,
            )
        except smtplib.SMTPRecipientsRefused as exc:
            logger.warning("Recipient refused %s: %s", to_email, exc)
            return EmailResult(
                success=False, to_email=to_email, subject=subject,
                error=f"Recipient refused: {exc}", attempt=attempt,
            )
        except (smtplib.SMTPException, OSError, TimeoutError) as exc:
            last_error = str(exc)
            error_type = classify_smtp_error(last_error)
            logger.warning("Email attempt %d/%d failed for %s (%s): %s", attempt, retries, to_email, error_type, exc)
            # Hard bounces — do not retry, no point
            if error_type == "hard":
                return EmailResult(
                    success=False, to_email=to_email, subject=subject,
                    error=last_error, attempt=attempt,
                )
            if attempt < retries:
                time.sleep(5)

    return EmailResult(
        success=False, to_email=to_email, subject=subject,
        error=last_error, attempt=retries,
    )


# ─── Journey email dispatcher ─────────────────────────────────────────────────

def send_journey_email(
    customer: dict[str, Any],
    stage: str,
    template_vars: dict[str, Any] | None = None,
) -> EmailResult:
    """
    Send the journey-appropriate email for a customer at a given stage.

    Args:
        customer:      Row dict from journey_customers
        stage:         Journey stage key (day2, day5, day15, day30, day60, day75, day95)
        template_vars: Optional extra vars for template rendering

    Returns:
        EmailResult
    """
    customer_context = _normalized_customer_context(customer)
    email_address = customer_context["email_address"]

    if not email_address or "@" not in email_address:
        return EmailResult(
            success=False,
            to_email="",
            subject="",
            error="no_email_address",
        )

    if customer.get("do_not_email"):
        return EmailResult(
            success=False,
            to_email=email_address,
            subject="",
            error="unsubscribed",
        )

    # Import here to avoid circular deps
    from app.email_templates import build_email_for_stage

    try:
        subject, html_body, text_body = build_email_for_stage(stage, customer_context, template_vars or {})
    except Exception as exc:
        logger.error("Template build failed for stage %s customer %s: %s", stage, customer.get("id"), exc)
        return EmailResult(
            success=False,
            to_email=email_address,
            subject="",
            error=f"template_error: {exc}",
        )

    return send_email(to_email=email_address, subject=subject, html_body=html_body, text_body=text_body)


def send_and_record_journey_email(
    conn: Any,
    customer: dict[str, Any],
    stage: str,
    wabis_message_id: str = "",
    template_vars: dict[str, Any] | None = None,
) -> EmailResult:
    """Send the stage email and mirror the result onto the journey_messages row."""
    result = send_journey_email(customer, stage, template_vars=template_vars)

    if not wabis_message_id:
        return result

    if result.success:
        conn.execute(
            "UPDATE journey_messages SET email_status = ?, email_sent_at = ? WHERE wabis_message_id = ?",
            ("sent", result.sent_at, wabis_message_id),
        )
    elif result.error not in ("no_email_address", "unsubscribed"):
        conn.execute(
            "UPDATE journey_messages SET email_status = ? WHERE wabis_message_id = ?",
            ("failed", wabis_message_id),
        )

    return result
