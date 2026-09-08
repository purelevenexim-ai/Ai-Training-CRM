"""
Google Ads purchase conversion uploader for Pureleven.

Uses the official Google Ads API ClickConversion upload endpoint. Configuration
is read from environment variables so account IDs and conversion actions are
never hard-coded into application code.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger("pureleven.google_ads_conversion")


def _env_first(*names: str) -> str:
    for name in names:
        value = (os.getenv(name) or "").strip()
        if value:
            return value
    return ""


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _customer_id() -> str:
    value = _env_first("GOOGLE_ADS_CUSTOMER_ID", "GADS_CUSTOMER_ID")
    return _digits(value)


def _login_customer_id() -> str:
    value = _env_first("GOOGLE_ADS_LOGIN_CUSTOMER_ID", "GADS_LOGIN_CUSTOMER_ID")
    return _digits(value)


def _conversion_action_id(event_name: str) -> str:
    event = re.sub(r"[^A-Z0-9]+", "_", (event_name or "purchase").upper()).strip("_")

    if event == "PURCHASE":
        return _env_first(
            "GOOGLE_ADS_PURCHASE_CONVERSION_ACTION_ID",
            "GOOGLE_ADS_CONVERSION_ACTION_ID",
            "GADS_PURCHASE_CONVERSION_ACTION_ID",
            "GADS_CONVERSION_ACTION_ID",
        )

    # Non-purchase lifecycle events must have their own conversion action.
    # Never silently send COD-delivered or other events into the Purchase action.
    return _env_first(
        f"GOOGLE_ADS_{event}_CONVERSION_ACTION_ID",
        f"GADS_{event}_CONVERSION_ACTION_ID",
    )


def _credentials() -> dict[str, str]:
    return {
        "developer_token": _env_first(
            "GOOGLE_ADS_DEVELOPER_TOKEN", "GADS_DEVELOPER_TOKEN"
        ),
        "client_id": _env_first("GOOGLE_ADS_CLIENT_ID", "GADS_OAUTH_CLIENT_ID"),
        "client_secret": _env_first(
            "GOOGLE_ADS_CLIENT_SECRET", "GADS_OAUTH_CLIENT_SECRET"
        ),
        "refresh_token": _env_first(
            "GOOGLE_ADS_REFRESH_TOKEN", "GADS_OAUTH_REFRESH_TOKEN"
        ),
    }


def _configuration_errors(event_name: str) -> list[str]:
    errors: list[str] = []
    credentials = _credentials()
    for key, value in credentials.items():
        if not value:
            errors.append(f"missing_{key}")
    if not _customer_id():
        errors.append("missing_customer_id")
    if not _conversion_action_id(event_name):
        errors.append(f"missing_conversion_action_id_for_{event_name or 'purchase'}")
    return errors


def _get_google_ads_client():
    from google.ads.googleads.client import GoogleAdsClient

    config: dict[str, Any] = {
        **_credentials(),
        "use_proto_plus": True,
    }
    login_customer_id = _login_customer_id()
    if login_customer_id:
        config["login_customer_id"] = login_customer_id
    return GoogleAdsClient.load_from_dict(config)


def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value.strip():
        try:
            dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None

    if dt.tzinfo is None:
        # Shopify timestamps are timezone-aware in production, but UTC is the
        # safest explicit fallback for legacy/backfilled naive values.
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _format_conversion_datetime(value: Any) -> str:
    dt = _parse_datetime(value)
    if dt is None:
        raise ValueError("missing_or_invalid_conversion_datetime")
    # Google Ads requires: yyyy-mm-dd hh:mm:ss+|-hh:mm (space, not T).
    return dt.isoformat(sep=" ", timespec="seconds")


def _normalize_email(email: Optional[str]) -> str:
    return (email or "").strip().lower()


def _normalize_phone(phone: Optional[str]) -> str:
    raw = (phone or "").strip()
    if not raw:
        return ""

    digits = _digits(raw)
    if not digits:
        return ""

    # Pureleven primarily sells in India. Normalize common 10/12 digit Indian
    # forms to E.164 before hashing; preserve other already-international forms.
    if len(digits) == 10:
        return f"+91{digits}"
    if len(digits) == 12 and digits.startswith("91"):
        return f"+{digits}"
    if raw.startswith("+"):
        return f"+{digits}"
    return f"+{digits}"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _append_user_identifiers(client, conversion, email: Optional[str], phone: Optional[str]) -> int:
    count = 0
    normalized_email = _normalize_email(email)
    normalized_phone = _normalize_phone(phone)

    if normalized_email:
        identifier = client.get_type("UserIdentifier")
        identifier.hashed_email = _sha256(normalized_email)
        conversion.user_identifiers.append(identifier)
        count += 1

    if normalized_phone:
        identifier = client.get_type("UserIdentifier")
        identifier.hashed_phone_number = _sha256(normalized_phone)
        conversion.user_identifiers.append(identifier)
        count += 1

    return count


def _pick_click_identifier(
    gclid: Optional[str], gbraid: Optional[str], wbraid: Optional[str]
) -> tuple[str, str]:
    # Google expects the relevant click/braid identifier for click conversion
    # attribution. Keep exactly one on the conversion.
    for kind, value in (("gclid", gclid), ("gbraid", gbraid), ("wbraid", wbraid)):
        cleaned = (value or "").strip()
        if cleaned:
            return kind, cleaned
    return "", ""


def _partial_failure_message(response: Any) -> str:
    partial = getattr(response, "partial_failure_error", None)
    if partial is None:
        return ""
    message = (getattr(partial, "message", "") or "").strip()
    code = getattr(partial, "code", 0) or 0
    if message or code:
        return message or f"partial_failure_code_{code}"
    return ""


def upload_purchase_conversion(
    *,
    gclid: Optional[str] = None,
    gbraid: Optional[str] = None,
    wbraid: Optional[str] = None,
    order_id: str,
    value: float,
    currency: str = "INR",
    order_date: Any,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    event_name: str = "purchase",
) -> dict[str, Any]:
    """Upload one Google Ads click conversion.

    A structured dict is always returned. Any failure includes an ``error`` key
    so the CRM's TrackingEvent and per-destination status logic records a failed
    attempt instead of silently treating it as sent.
    """

    event_name = (event_name or "purchase").strip().lower()
    order_id = str(order_id or "").strip()

    errors = _configuration_errors(event_name)
    if errors:
        return {
            "error": "google_ads_configuration_error",
            "details": errors,
            "event_name": event_name,
            "order_id": order_id,
        }

    if not order_id:
        return {
            "error": "missing_order_id",
            "event_name": event_name,
        }

    click_id_type, click_id_value = _pick_click_identifier(gclid, gbraid, wbraid)
    if not click_id_value:
        # Do not claim a Google Ads purchase was uploaded when it cannot be tied
        # to an ad click. A future enhanced-conversions-only flow can be added
        # separately if desired.
        return {
            "error": "missing_google_click_identifier",
            "event_name": event_name,
            "order_id": order_id,
        }

    try:
        conversion_date_time = _format_conversion_datetime(order_date)
    except ValueError as exc:
        return {
            "error": str(exc),
            "event_name": event_name,
            "order_id": order_id,
        }

    customer_id = _customer_id()
    conversion_action_id = _digits(_conversion_action_id(event_name))
    if not conversion_action_id:
        return {
            "error": "invalid_conversion_action_id",
            "event_name": event_name,
            "order_id": order_id,
        }

    try:
        client = _get_google_ads_client()
        service = client.get_service("ConversionUploadService")
        conversion = client.get_type("ClickConversion")

        conversion.conversion_action = (
            f"customers/{customer_id}/conversionActions/{conversion_action_id}"
        )
        conversion.conversion_date_time = conversion_date_time
        conversion.conversion_value = float(value or 0)
        conversion.currency_code = (currency or "INR").upper()
        conversion.order_id = order_id
        setattr(conversion, click_id_type, click_id_value)

        user_identifier_count = _append_user_identifiers(
            client, conversion, email, phone
        )

        response = service.upload_click_conversions(
            customer_id=customer_id,
            conversions=[conversion],
            partial_failure=True,
        )

        partial_failure = _partial_failure_message(response)
        if partial_failure:
            return {
                "error": "google_ads_partial_failure",
                "details": partial_failure,
                "event_name": event_name,
                "order_id": order_id,
                "customer_id": customer_id,
                "conversion_action_id": conversion_action_id,
                "click_id_type": click_id_type,
            }

        results = list(getattr(response, "results", []) or [])
        if not results:
            return {
                "error": "google_ads_empty_upload_response",
                "event_name": event_name,
                "order_id": order_id,
                "customer_id": customer_id,
                "conversion_action_id": conversion_action_id,
                "click_id_type": click_id_type,
            }

        return {
            "ok": True,
            "status": "sent",
            "event_name": event_name,
            "order_id": order_id,
            "customer_id": customer_id,
            "conversion_action_id": conversion_action_id,
            "click_id_type": click_id_type,
            "user_identifier_count": user_identifier_count,
            "conversion_date_time": conversion_date_time,
        }
    except ImportError as exc:
        return {
            "error": "google_ads_package_missing",
            "details": str(exc),
            "event_name": event_name,
            "order_id": order_id,
        }
    except Exception as exc:
        return {
            "error": "google_ads_upload_exception",
            "details": str(exc)[:1000],
            "request_id": getattr(exc, "request_id", None),
            "event_name": event_name,
            "order_id": order_id,
        }


def health_check(event_name: str = "purchase") -> dict[str, Any]:
    """Validate local config and confirm the configured conversion action via API."""
    event_name = (event_name or "purchase").strip().lower()
    errors = _configuration_errors(event_name)
    if errors:
        return {
            "status": "error",
            "error": "google_ads_configuration_error",
            "details": errors,
            "event_name": event_name,
        }

    customer_id = _customer_id()
    conversion_action_id = _digits(_conversion_action_id(event_name))
    try:
        client = _get_google_ads_client()
        service = client.get_service("GoogleAdsService")
        query = (
            "SELECT conversion_action.id, conversion_action.name, "
            "conversion_action.status, conversion_action.type, "
            "conversion_action.category "
            "FROM conversion_action "
            f"WHERE conversion_action.id = {conversion_action_id}"
        )
        rows = list(service.search(customer_id=customer_id, query=query))
        if not rows:
            return {
                "status": "error",
                "error": "conversion_action_not_found",
                "customer_id": customer_id,
                "conversion_action_id": conversion_action_id,
                "event_name": event_name,
            }

        action = rows[0].conversion_action
        return {
            "status": "ok",
            "customer_id": customer_id,
            "conversion_action_id": str(action.id),
            "conversion_action_name": action.name,
            "conversion_action_status": str(action.status),
            "conversion_action_type": str(action.type),
            "conversion_action_category": str(action.category),
            "event_name": event_name,
        }
    except ImportError as exc:
        return {
            "status": "error",
            "error": "google_ads_package_missing",
            "details": str(exc),
            "event_name": event_name,
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": "google_ads_health_check_failed",
            "details": str(exc)[:1000],
            "request_id": getattr(exc, "request_id", None),
            "customer_id": customer_id,
            "conversion_action_id": conversion_action_id,
            "event_name": event_name,
        }
