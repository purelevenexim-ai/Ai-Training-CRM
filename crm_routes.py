"""
Pureleven CRM API Endpoints
Handles Shopify webhooks, GA4 events, Google Ads, Meta conversions, and Email/SMS tracking
"""

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks, Header
from pydantic import BaseModel, EmailStr
from sqlalchemy import create_engine, func, text
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import csv
import hashlib
import hmac
import io
import json
import logging
import os
import time
import sys
try:
    import redis
except ImportError:
    redis = None
from dotenv import load_dotenv

logger = logging.getLogger("pureleven.crm")

sys.path.insert(0, os.path.dirname(__file__))

# Lazy-import integration modules so missing deps don't crash startup
def _meta_capi():
    try:
        import sys, os as _os
        sys.path.insert(0, _os.path.dirname(__file__))
        import meta_capi as _m
        return _m
    except Exception as e:
        logger.warning("meta_capi import failed: %s", e)
        return None

def _gads():
    try:
        import sys, os as _os
        sys.path.insert(0, _os.path.dirname(__file__))
        import gads_conversion as _g
        return _g
    except Exception as e:
        logger.warning("gads_conversion import failed: %s", e)
        return None

# Load env from multiple possible locations (VPS, local dev, Docker)
env_paths = [
    "/opt/pureleven/ai-engine/.env",  # VPS Docker location
    os.path.join(os.path.dirname(__file__), "..", ".env"),  # Relative to app/crm_routes.py
    os.path.join(os.getcwd(), ".env"),  # Current working directory
]
for env_path in env_paths:
    if os.path.exists(env_path):
        load_dotenv(env_path)
        logger.info(f"✅ Loaded .env from {env_path}")
        break
else:
    load_dotenv()  # Fallback to default
    logger.info("⚠️ Loaded .env from default location")

# Debug: verify Google Ads credentials are loaded
ga_client_id = os.getenv("GOOGLE_ADS_CLIENT_ID")
ga_client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET")
logger.info(f"DEBUG: GOOGLE_ADS_CLIENT_ID={'***' + ga_client_id[-10:] if ga_client_id else 'NOT FOUND'}")
logger.info(f"DEBUG: GOOGLE_ADS_CLIENT_SECRET={'***' if ga_client_secret else 'NOT FOUND'}")

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL") or (
    f"postgresql+psycopg2://{os.getenv('POSTGRES_USER', 'pureleven')}:{os.getenv('POSTGRES_PASSWORD', '')}"
    f"@{os.getenv('POSTGRES_HOST', 'pureleven-postgres')}:{os.getenv('POSTGRES_PORT', 5432)}/{os.getenv('POSTGRES_DB', 'pureleven')}"
)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

router = APIRouter(prefix="/api/crm", tags=["crm"])


# ============= DEBUG ENDPOINT =============
@router.get("/debug/env")
def debug_env():
    """Debug endpoint to check if env vars are loaded"""
    return {
        "GOOGLE_ADS_CLIENT_ID": os.getenv("GOOGLE_ADS_CLIENT_ID", "NOT FOUND"),
        "GOOGLE_ADS_CLIENT_SECRET": "***" if os.getenv("GOOGLE_ADS_CLIENT_SECRET") else "NOT FOUND",
        "GOOGLE_ADS_DEVELOPER_TOKEN": "***" if os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN") else "NOT FOUND",
        "GOOGLE_ADS_CUSTOMER_ID": os.getenv("GOOGLE_ADS_CUSTOMER_ID", "NOT FOUND"),
        "cwd": os.getcwd(),
        "env_file_exists": os.path.exists("/opt/pureleven/ai-engine/.env"),
    }


# ============= PYDANTIC SCHEMAS =============

class CustomerCreate(BaseModel):
    shopify_customer_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    tags: Optional[List[str]] = None


class EventCreate(BaseModel):
    customer_id: Optional[str] = None
    email: Optional[str] = None
    event_type: str
    source: str  # shopify, ga4, google_ads, meta, email
    event_data: Dict[str, Any]
    timestamp: datetime


class ConversionCreate(BaseModel):
    source: str  # ga4, google_ads, meta
    external_id: str
    email: Optional[str] = None
    phone: Optional[str] = None
    conversion_type: str
    conversion_value: float
    currency: str = "INR"
    campaign_id: Optional[str] = None
    campaign_name: Optional[str] = None
    gclid: Optional[str] = None
    fbp: Optional[str] = None
    timestamp: datetime


class CustomerResponse(BaseModel):
    id: str
    shopify_customer_id: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    total_spent: float
    orders_count: int
    last_order_date: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============= HELPER FUNCTIONS =============

def get_or_create_customer(db: Session, email: Optional[str] = None, shopify_id: Optional[str] = None, phone: Optional[str] = None) -> Any:
    """Get or create customer by email/shopify_id/phone"""
    from crm_models import Customer
    
    # Try to find by shopify_id first
    if shopify_id:
        customer = db.query(Customer).filter(Customer.shopify_customer_id == shopify_id).first()
        if customer:
            return customer
    
    # Try by email
    if email:
        customer = db.query(Customer).filter(Customer.email == email).first()
        if customer:
            return customer
    
    # Create new if not found
    customer = Customer(
        email=email,
        shopify_customer_id=shopify_id,
        phone=phone
    )
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def match_conversions_to_customers(db: Session):
    """Background task: Match unmatched conversions to customers"""
    from crm_models import ConversionFeed, Customer
    
    unmatched = db.query(ConversionFeed).filter(ConversionFeed.is_matched == False).all()
    
    for conversion in unmatched:
        customer = None
        
        # Try email
        if conversion.email:
            customer = db.query(Customer).filter(Customer.email == conversion.email).first()
        
        # Try phone
        if not customer and conversion.phone:
            customer = db.query(Customer).filter(Customer.phone == conversion.phone).first()
        
        # Try shopify_id
        if not customer and conversion.shopify_customer_id:
            customer = db.query(Customer).filter(Customer.shopify_customer_id == conversion.shopify_customer_id).first()
        
        # Mark as matched
        if customer:
            conversion.is_matched = True
            conversion.matched_customer_id = customer.id
    
    db.commit()


def _run_conversion_match_task():
    """Background wrapper so matching does not reuse a closed request session."""
    db = SessionLocal()
    try:
        match_conversions_to_customers(db)
    except Exception as exc:
        logger.warning("Conversion match background task failed: %s", exc)
        db.rollback()
    finally:
        db.close()


def _reclassify_customer_segments_task(customer_id: str):
    """Background wrapper for audience recalculation."""
    try:
        from crm_audiences import AudienceEngine
    except Exception:
        return

    db = SessionLocal()
    try:
        AudienceEngine(db).upsert_customer_segments(customer_id)
    except Exception as exc:
        logger.warning("Audience reclassification failed for customer %s: %s", customer_id, exc)
        db.rollback()
    finally:
        db.close()


def _parse_shopify_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def _derive_payment_method(order_data: dict) -> str:
    gateways = order_data.get("payment_gateway_names") or []
    raw_gateway = " ".join(str(entry) for entry in gateways) or str(order_data.get("payment_gateway", ""))
    raw_gateway = raw_gateway.lower()
    if "cash" in raw_gateway or "cod" in raw_gateway:
        return "cod"
    if raw_gateway:
        return raw_gateway.split(",")[0].strip() or "prepaid"
    return "prepaid"


def _format_order_items(line_items: list[dict]) -> str:
    parts = []
    for item in line_items or []:
        title = item.get("title") or item.get("name") or "Item"
        quantity = item.get("quantity") or 1
        parts.append(f"{quantity} x {title}")
    return ", ".join(parts) or "your order"


def _format_shipping_address(address: Optional[dict]) -> str:
    if not address:
        return "your saved address"
    parts = [
        address.get("name"),
        address.get("address1"),
        address.get("address2"),
        address.get("city"),
        address.get("province"),
        address.get("zip"),
        address.get("country"),
    ]
    return ", ".join(str(part).strip() for part in parts if part)


def _build_transactional_email_substitutions(order_data: dict, template_name: str) -> dict:
    customer_data = order_data.get("customer") or {}
    shipping_address = order_data.get("shipping_address") or {}
    order_dt = _parse_shopify_datetime(order_data.get("created_at"))
    expected_delivery = order_dt + timedelta(days=5) if order_dt else None
    order_reference = (
        order_data.get("name")
        or order_data.get("order_number")
        or order_data.get("id")
        or ""
    )
    if isinstance(order_reference, str):
        order_reference = order_reference.lstrip("#")

    customer_name = (
        shipping_address.get("first_name")
        or customer_data.get("first_name")
        or order_data.get("first_name")
        or "there"
    )

    substitutions = {
        "customer_name": customer_name,
        "order_id": order_reference,
        "order_date": order_dt.strftime("%d %b %Y") if order_dt else "today",
        "total": f"{float(order_data.get('total_price', 0) or 0):.2f}",
        "items": _format_order_items(order_data.get("line_items") or []),
        "delivery_address": _format_shipping_address(shipping_address),
        "payment_method": _derive_payment_method(order_data).upper(),
        "delivery_date": expected_delivery.strftime("%d %b %Y") if expected_delivery else "3-5 business days",
        "tracking_url": order_data.get("order_status_url") or f"{os.getenv('SITE_URL', 'https://pureleven.com')}/account",
        "unsubscribe_url": f"{os.getenv('SITE_URL', 'https://pureleven.com')}/pages/contact",
        "shop_url": os.getenv("SITE_URL", "https://pureleven.com"),
        "cancel_reason": order_data.get("cancel_reason") or "If you did not request this cancellation, please reply and our team will help immediately.",
    }

    if template_name == "order_cancelled":
        substitutions["shop_url"] = os.getenv("SITE_URL", "https://pureleven.com")

    if template_name == "out_for_delivery":
        payment_method = substitutions.get("payment_method", "prepaid").lower()
        if payment_method == "cod":
            total_str = substitutions.get("total", "")
            substitutions["cod_reminder"] = (
                f"<p style=\"margin:8px 0 0;font-size:14px;color:#E65100\">"
                f"<strong>💰 Please keep ₹{total_str} ready in cash</strong> "
                f"to pay the delivery person.</p>"
            )
        else:
            substitutions["cod_reminder"] = ""

    return substitutions


def _build_welcome_substitutions(customer_data: dict) -> dict:
    """Build substitution variables for the welcome template from a Shopify customer payload."""
    first_name = (
        customer_data.get("first_name")
        or customer_data.get("name", "").split()[0] if customer_data.get("name") else "there"
    ) or "there"
    return {
        "customer_name": first_name,
        "shop_url": os.getenv("SITE_URL", "https://pureleven.com"),
        "unsubscribe_url": f"{os.getenv('SITE_URL', 'https://pureleven.com')}/pages/contact",
    }


def _send_welcome_email_task(customer_data: dict):
    """Background task: send welcome email to a new customer."""
    from sendgrid_handler import send_email

    to_email = (customer_data.get("email") or "").strip().lower()
    if not to_email:
        return

    db = SessionLocal()
    try:
        send_email(
            to_email=to_email,
            template_name="welcome",
            substitutions=_build_welcome_substitutions(customer_data),
            dedup_key=f"welcome:{to_email}",
            db=db,
        )
    except Exception as exc:
        logger.warning("Welcome email task failed recipient=%s: %s", to_email, exc)
        db.rollback()
    finally:
        db.close()


def _send_transactional_email_task(template_name: str, order_data: dict, dedup_key: Optional[str] = None):
    """Background task for transactional order emails."""
    from sendgrid_handler import send_email

    to_email = (order_data.get("email") or "").strip().lower()
    if not to_email:
        logger.info("Skipping transactional email %s — no recipient on order payload", template_name)
        return

    db = SessionLocal()
    try:
        # If order_data already contains pre-built substitution keys (e.g. from
        # the Shiprocket out_for_delivery path), use them directly.
        # Otherwise build substitutions from the full Shopify order payload.
        _SUBS_KEYS = {"customer_name", "order_id", "items", "delivery_address", "tracking_url"}
        if _SUBS_KEYS.issubset(order_data.keys()):
            substitutions = {k: v for k, v in order_data.items() if k != "email"}
        else:
            substitutions = _build_transactional_email_substitutions(order_data, template_name)

        send_email(
            to_email=to_email,
            template_name=template_name,
            substitutions=substitutions,
            dedup_key=dedup_key or str(order_data.get("id") or order_data.get("order_number") or ""),
            db=db,
        )
    except Exception as exc:
        logger.warning("Transactional email task failed template=%s recipient=%s: %s", template_name, to_email, exc)
        db.rollback()
    finally:
        db.close()


# ─── SERVER-SIDE ATTRIBUTION FAN-OUT ─────────────────────────────────────────

def _build_items_for_capi(line_items: list) -> list:
    """Normalise Shopify line_items into CAPI contents format."""
    return [
        {
            "id":         str(item.get("variant_id") or item.get("product_id") or ""),
            "quantity":   item.get("quantity", 1),
            "item_price": float(item.get("price", 0)),
            "title":      item.get("title") or item.get("name") or "",
        }
        for item in (line_items or [])
    ]


def fire_meta_capi(order_data: dict, client_ip: str, user_agent: str,
                   event_name: str = "Purchase", event_id_prefix: str = "purchase") -> None:
    """Background task: send order event to Meta Conversions API."""
    meta = _meta_capi()
    if meta is None:
        logger.warning("meta_capi module unavailable — skipping Meta CAPI")
        return

    order_id   = str(order_data.get("id", ""))
    email      = order_data.get("email")
    phone      = (order_data.get("billing_address") or {}).get("phone") or \
                 (order_data.get("customer") or {}).get("phone")
    value      = float(order_data.get("total_price", 0) or order_data.get("total_amount", 0) or 0)
    currency   = order_data.get("currency", "INR")
    fbclid     = order_data.get("_fbclid")  # stored earlier in order enrichment
    items      = _build_items_for_capi(order_data.get("line_items") or order_data.get("items") or [])

    fbp             = order_data.get("_fbp")
    fbc             = order_data.get("_fbc")
    event_source_url = order_data.get("order_status_url") or "https://pureleven.com/"

    result = meta.send_purchase(
        order_id=order_id,
        value=value,
        currency=currency,
        email=email,
        phone=phone,
        items=items,
        client_ip=client_ip,
        client_user_agent=user_agent,
        fbclid=fbclid,
        fbp=fbp,
        fbc=fbc,
        event_name=event_name,
        event_source_url=event_source_url,
    )
    logger.info("Meta CAPI %s order=%s result=%s", event_name, order_id, result)

    # Persist delivery result to TrackingEvent and crm_orders
    _log_tracking_event(order_id, "meta", event_name, result)
    _update_order_destination_status(order_id, "meta", result)


def _update_capi_status(shopify_order_id: str, result: dict) -> None:
    """Update legacy capi_status on crm_orders (kept for backward compat)."""
    from crm_models import Order
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.shopify_order_id == shopify_order_id).first()
        if not order:
            return
        is_error = bool(result.get("error"))
        order.capi_attempts = (order.capi_attempts or 0) + 1
        if is_error:
            order.capi_status = "failed"
            order.capi_last_error = str(result.get("error", ""))[:500]
        else:
            order.capi_status = "sent"
            order.capi_last_error = None
            order.capi_sent_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        logger.warning("_update_capi_status error for order %s: %s", shopify_order_id, exc)
        db.rollback()
    finally:
        db.close()


def _log_tracking_event(order_id: str, destination: str, event_name: str, result: dict) -> None:
    """Append a TrackingEvent row for one delivery attempt."""
    try:
        from crm_models import TrackingEvent
    except ImportError:
        return
    db = SessionLocal()
    try:
        is_error = bool(result.get("error"))
        db.add(TrackingEvent(
            order_id=str(order_id),
            destination=destination,
            event_name=event_name,
            status="failed" if is_error else "sent",
            response_body=json.dumps(result)[:2000],
            error=str(result.get("error", ""))[:500] if is_error else None,
        ))
        db.commit()
    except Exception as exc:
        logger.warning("_log_tracking_event error order=%s dest=%s: %s", order_id, destination, exc)
        db.rollback()
    finally:
        db.close()


def _update_order_destination_status(order_id: str, destination: str, result: dict) -> None:
    """Update destination-specific columns on crm_orders after a send attempt."""
    from crm_models import Order
    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.shopify_order_id == str(order_id)).first()
        if not order:
            return
        is_error = bool(result.get("error"))
        status_val = "failed" if is_error else "sent"
        response_str = json.dumps(result)[:500]
        error_str = str(result.get("error", ""))[:500] if is_error else None
        now = datetime.now(timezone.utc)
        if destination == "meta":
            order.meta_status = status_val
            order.meta_sent_at = None if is_error else now
            order.meta_response = response_str
            order.meta_error = error_str
        elif destination == "google":
            order.google_status = status_val
            order.google_sent_at = None if is_error else now
            order.google_response = response_str
            order.google_error = error_str
        elif destination == "ga4":
            order.ga4_status = status_val
            order.ga4_sent_at = None if is_error else now
            order.ga4_response = response_str
            order.ga4_error = error_str
        db.commit()
    except Exception as exc:
        logger.warning("_update_order_destination_status error order=%s dest=%s: %s", order_id, destination, exc)
        db.rollback()
    finally:
        db.close()


def fire_google_conversion(order_data: dict, event_name: str = "purchase") -> None:
    """Background task: send conversion to Google Ads Enhanced Conversions API."""
    gads = _gads()
    if gads is None:
        logger.warning("gads_conversion module unavailable — skipping Google Ads")
        return

    order_id   = str(order_data.get("id", ""))
    value      = float(order_data.get("total_price", 0))
    currency   = order_data.get("currency", "INR")
    email      = order_data.get("email")
    phone      = (order_data.get("billing_address") or {}).get("phone") or \
                 (order_data.get("customer") or {}).get("phone")
    gclid      = order_data.get("_gclid")
    order_date_str = order_data.get("created_at")
    try:
        order_date = datetime.fromisoformat(order_date_str.replace("Z", "+00:00")) \
            if order_date_str else None
    except Exception:
        order_date = None

    result = gads.upload_purchase_conversion(
        gclid=gclid,
        order_id=order_id,
        value=value,
        currency=currency,
        order_date=order_date,
        email=email,
        phone=phone,
        event_name=event_name,
    )
    logger.info("Google Ads conversion order=%s event=%s result=%s", order_id, event_name, result)

    _log_tracking_event(order_id, "google", event_name, result)
    _update_order_destination_status(order_id, "google", result)


def fire_ga4_purchase(order_data: dict) -> None:
    """Background task: send purchase event to GA4 Measurement Protocol."""
    measurement_id = os.getenv("GA4_MEASUREMENT_ID", "")
    api_secret     = os.getenv("GA4_API_SECRET", "")
    if not measurement_id or not api_secret:
        logger.info("GA4 MP credentials not set — skipping")
        return

    import urllib.request, urllib.error

    order_id = str(order_data.get("id", ""))
    value    = float(order_data.get("total_price", 0))
    currency = order_data.get("currency", "INR")
    items    = [
        {
            "item_id":   str(item.get("product_id") or ""),
            "item_name": item.get("title") or "",
            "price":     float(item.get("price", 0)),
            "quantity":  item.get("quantity", 1),
        }
        for item in order_data.get("line_items", [])
    ]
    client_id = (
        order_data.get("ga_client_id")
        or order_data.get("_ga_client_id")
        or order_data.get("client_id")
        or order_data.get("session_id")
        or "server"
    )
    session_id = order_data.get("ga_session_id") or order_data.get("_ga_session_id")

    params = {
        "transaction_id": order_id,
        "value":          value,
        "currency":       currency,
        "items":          items,
    }
    if session_id:
        params["session_id"] = session_id

    payload = {
        "client_id": client_id,
        "events": [{
            "name": "purchase",
            "params": params,
        }],
    }
    url  = f"https://www.google-analytics.com/mp/collect?measurement_id={measurement_id}&api_secret={api_secret}"
    body = json.dumps(payload).encode()
    try:
        req = urllib.request.Request(url, data=body,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=5):
            pass
        logger.info("GA4 MP purchase sent: order=%s", order_id)
    except Exception as exc:
        logger.warning("GA4 MP error: %s", exc)


# ─── PHASE 1: TRACKING INTEGRITY LAYER ───────────────────────────────────────

# Internal email addresses to exclude from conversion tracking
_INTERNAL_EMAILS = frozenset([
    "test@pureleven.com", "admin@pureleven.com", "team@pureleven.com",
    "staging@pureleven.com", "demo@pureleven.com",
])

# Known bot User-Agent fragments
_BOT_UA_FRAGMENTS = (
    "googlebot", "bingbot", "slurp", "duckduckbot", "baiduspider",
    "yandex", "facebookexternalhit", "twitterbot", "semrushbot",
    "ahrefsbot", "mj12bot", "dotbot", "scrapy", "python-requests",
    "curl/", "wget/", "go-http-client", "okhttp",
)


def calculate_fraud_score(order: dict) -> int:
    """
    Returns a fraud likelihood score 0-100.
    >50 = high risk, skip CAPI send.
    Lower is better (0 = clean).
    Handles both Shopify raw webhook format (total_price, line_items) and
    CRM internal format (total_amount, items) for CSV-imported orders.
    """
    score = 0
    email = (order.get("email") or "").strip().lower()
    phone_raw = (
        (order.get("billing_address") or {}).get("phone")
        or (order.get("customer") or {}).get("phone")
        or order.get("phone")
        or ""
    )
    phone = "".join(c for c in str(phone_raw) if c.isdigit())
    # Support both Shopify raw format (total_price) and CRM format (total_amount)
    total = float(order.get("total_price") or order.get("total_amount") or 0)
    # Support both Shopify raw format (line_items) and CRM format (items)
    items = order.get("line_items") or order.get("items") or []
    shipping = order.get("shipping_address") or {}
    has_click_attribution = bool(
        order.get("_gclid") or order.get("gclid")
        or order.get("_fbclid") or order.get("fbclid")
    )

    # Email checks
    # Missing email is common on COD/guest checkouts — low penalty unless combined with other signals
    if not email or "@" not in email or len(email) < 6:
        score += 5 if has_click_attribution else 10
    elif email in _INTERNAL_EMAILS or email.startswith("test"):
        score += 40  # Definitely skip internal/test orders

    # Phone checks — often absent on Shopify billing_address; very low penalty
    if not phone or len(phone) < 10:
        score += 3 if has_click_attribution else 5

    # Value checks
    if total < 50:
        score += 25  # Suspiciously low — likely test order
    elif total > 50000:
        score += 10  # Unusually large (lower confidence)

    # Item checks — no items means broken/test webhook payload
    if len(items) == 0:
        score += 25

    # Address check — missing city+zip is a weak signal, not a fraud signal
    # Shopify COD orders may have incomplete shipping on the paid event
    if not shipping.get("city") and not shipping.get("zip"):
        score += 5 if has_click_attribution else 10

    return min(score, 100)


def should_send_to_capi(order: dict) -> tuple[bool, str]:
    """
    3-level gate before sending purchase to Meta CAPI / Google Ads.
    Returns (approved: bool, reason: str)
    """
    # Level 1: Order must be paid
    fin_status = (order.get("financial_status") or order.get("status") or "").lower()
    if fin_status and fin_status not in ("paid", "partially_paid", "pending"):
        return False, "order_not_paid"

    # Level 2: Skip test/internal orders  
    email = (order.get("email") or "").strip().lower()
    if email in _INTERNAL_EMAILS:
        return False, "internal_email"

    # Level 3: Fraud score check
    fraud_score = calculate_fraud_score(order)
    if fraud_score > 50:
        logger.warning("Fraud score %d for order %s — skipping CAPI", fraud_score, order.get("id"))
        return False, f"fraud_score_{fraud_score}"

    return True, "approved"


def is_valid_request(email: str | None, user_agent: str, client_ip: str) -> bool:
    """
    Filter out bots, internal users, and suspicious traffic before tracking.
    Returns False if the request should NOT be counted as real.
    """
    ua = (user_agent or "").lower()
    # Bot user-agent detection
    if any(frag in ua for frag in _BOT_UA_FRAGMENTS):
        return False
    # Internal email
    if email and email.strip().lower() in _INTERNAL_EMAILS:
        return False
    return True


def _lookup_attribution_for_customer(db: Session, customer_id: str,
                                     email: str | None) -> dict:
    """
    Find the most recent gclid / fbclid stored in page_view events
    for this customer, to attach to the order conversion.
    """
    result = {"gclid": None, "fbclid": None, "fbp": None, "fbc": None, "ga_client_id": None, "ga_session_id": None}
    try:
        from crm_models import Event
        rows = (
            db.query(Event.event_data)
            .filter(
                Event.customer_id == customer_id,
                Event.event_type.in_(["page_view", "checkout_start",
                                       "checkout_initiated"]),
            )
            .order_by(Event.timestamp.desc())
            .limit(20)
            .all()
        )
        for (data,) in rows:
            if not data:
                continue
            if not result["gclid"] and data.get("gclid"):
                result["gclid"] = data["gclid"]
            if not result["fbclid"] and data.get("fbclid"):
                result["fbclid"] = data["fbclid"]
            if not result["fbp"] and data.get("fbp"):
                result["fbp"] = data["fbp"]
            if not result["fbc"] and data.get("fbc"):
                result["fbc"] = data["fbc"]
            if not result["ga_client_id"] and data.get("ga_client_id"):
                result["ga_client_id"] = data["ga_client_id"]
            if not result["ga_session_id"] and data.get("ga_session_id"):
                result["ga_session_id"] = data["ga_session_id"]
            if all(result.values()):
                break
    except Exception as exc:
        logger.warning("Attribution lookup failed: %s", exc)
    return result




@router.post("/webhooks/shopify")
async def shopify_webhook(request: Request, background_tasks: BackgroundTasks, x_shopify_hmac_sha256: Optional[str] = Header(None)):
    """
    Receive Shopify webhooks for customers, orders, checkouts
    
    Topics:
    - customers/create
    - customers/update
    - orders/create
    - orders/paid
    - orders/fulfilled
    - orders/cancelled
    - abandoned_checkouts/create
    - checkouts/create
    - checkouts/update
    """
    from crm_models import Customer, Order, Event
    
    db = SessionLocal()
    body = await request.json()
    topic = request.headers.get("X-Shopify-Topic", "unknown")
    
    try:
        if topic == "customers/create" or topic == "customers/update":
            customer_data = body.get("data", body)  # Handle wrapped or unwrapped payload
            
            customer = get_or_create_customer(
                db,
                email=customer_data.get("email"),
                shopify_id=str(customer_data.get("id")),
                phone=customer_data.get("phone")
            )
            
            customer.first_name = customer_data.get("first_name")
            customer.last_name = customer_data.get("last_name")
            customer.tags = customer_data.get("tags", [])
            customer.shopify_created_at = customer_data.get("created_at")
            customer.shopify_updated_at = customer_data.get("updated_at")
            
            db.commit()

            # Send welcome email only on account creation
            if topic == "customers/create" and customer_data.get("email"):
                background_tasks.add_task(_send_welcome_email_task, customer_data)
                # Journey orchestration: enroll new customer
                background_tasks.add_task(_background_assign_journeys, customer.id, "customer_create")
        
        elif topic == "orders/create" or topic == "orders/paid":
            order_data = body.get("data", body)
            shopify_order_id = str(order_data.get("id", ""))
            customer_shopify_id = str((order_data.get("customer") or {}).get("id") or "")
            existing_order = db.query(Order).filter(
                Order.shopify_order_id == shopify_order_id
            ).first()

            if existing_order and topic == "orders/create":
                logger.info("⚠️ Dedup: order %s already in DB — skipping insert", shopify_order_id)
                return {"status": "skipped_duplicate", "order_id": shopify_order_id}

            customer = get_or_create_customer(
                db,
                email=order_data.get("email"),
                shopify_id=customer_shopify_id
            )

            # Enrich attribution from prior page_view/checkout events
            attr = _lookup_attribution_for_customer(db, customer.id, customer.email)
            gclid  = attr["gclid"]
            fbclid = attr["fbclid"]

            payment_method = _derive_payment_method(order_data)

            # Build a copy of order_data with attribution for background tasks
            order_data_enriched = dict(order_data)
            order_data_enriched["_gclid"]  = gclid
            order_data_enriched["_fbclid"] = fbclid
            order_data_enriched["_fbp"] = attr.get("fbp")
            order_data_enriched["_fbc"] = attr.get("fbc")
            order_data_enriched["ga_client_id"] = attr.get("ga_client_id")
            order_data_enriched["ga_session_id"] = attr.get("ga_session_id")

            # ── PHASE 1: FRAUD SCORING ────────────────────────────────────────
            fraud_score = calculate_fraud_score(order_data_enriched)
            capi_approved, capi_reason = should_send_to_capi(order_data_enriched)
            logger.info("Order %s: fraud_score=%d capi_approved=%s (%s)",
                        shopify_order_id, fraud_score, capi_approved, capi_reason)

            order_date = _parse_shopify_datetime(order_data.get("created_at"))
            order_total = float(order_data.get("total_price", 0) or 0)
            order_items = [{
                "item_id": str(item.get("id")),
                "name": item.get("title"),
                "price": float(item.get("price", 0)),
                "quantity": item.get("quantity"),
                "item_category": item.get("product_type", "Unknown")
            } for item in order_data.get("line_items", [])]
            order_status = (
                order_data.get("financial_status")
                or order_data.get("fulfillment_status")
                or order_data.get("status")
            )

            if existing_order:
                order = existing_order
                order.customer_id = order.customer_id or customer.id
                order.email = order_data.get("email") or order.email
                order.order_date = order_date or order.order_date
                order.total_amount = order_total or order.total_amount
                order.currency = order_data.get("currency", order.currency or "INR")
                order.status = order_status or order.status
                order.payment_method = payment_method or order.payment_method
                order.gclid = order.gclid or gclid
                order.fbclid = order.fbclid or fbclid
                order.items = order_items or order.items
                order.shipping_address = order_data.get("shipping_address") or order.shipping_address
                order.fraud_score = fraud_score
                order.capi_suppressed = not capi_approved
            else:
                order = Order(
                    customer_id=customer.id,
                    shopify_order_id=shopify_order_id,
                    email=order_data.get("email"),
                    order_date=order_date,
                    total_amount=order_total,
                    currency=order_data.get("currency", "INR"),
                    status=order_status,
                    payment_method=payment_method,
                    gclid=gclid,
                    fbclid=fbclid,
                    items=order_items,
                    shipping_address=order_data.get("shipping_address"),
                    fraud_score=fraud_score,
                    capi_suppressed=not capi_approved,
                )

                db.add(order)
                customer.total_spent = float(customer.total_spent or 0) + order_total
                customer.orders_count = int(customer.orders_count or 0) + 1
                if order_date:
                    customer.last_order_date = order_date

            if gclid and not customer.gclid:
                customer.gclid = gclid
            if fbclid and not customer.fbclid:
                customer.fbclid = fbclid
            
            db.commit()

            client_ip  = request.client.host if request.client else ""
            user_agent = request.headers.get("user-agent", "")
            if topic == "orders/paid" and capi_approved:
                if not order.offline_conversion_sent:
                    background_tasks.add_task(
                        fire_meta_capi, order_data_enriched, client_ip, user_agent)
                    background_tasks.add_task(fire_google_conversion, order_data_enriched)
                    # GA4 purchase removed: Shopify Google & YouTube channel handles this via web+server pixels (avoids 4x duplicate counting)
                    order.offline_conversion_sent = True
                    db.commit()
                else:
                    logger.info("Order %s already sent to ad platforms — skipping duplicate paid fan-out", shopify_order_id)
            elif topic == "orders/paid" and not capi_approved:
                logger.warning("CAPI suppressed for order %s: %s", shopify_order_id, capi_reason)

            if not existing_order and order_data.get("email"):
                # Use COD-specific template so buyer knows to keep cash ready
                email_template = (
                    "order_confirmation_cod"
                    if payment_method == "cod"
                    else "order_confirmation"
                )
                background_tasks.add_task(
                    _send_transactional_email_task,
                    email_template,
                    order_data_enriched,
                    shopify_order_id,
                )

            # Audience reclassification
            background_tasks.add_task(_reclassify_customer_segments_task, customer.id)
            # Journey orchestration: enroll on order complete
            background_tasks.add_task(_background_assign_journeys, customer.id, "order_complete")
            # Phase 4.3: Attribution — link this order to the journey that drove it
            if topic == "orders/paid":
                background_tasks.add_task(
                    _background_backtrack_attribution,
                    customer.id, shopify_order_id, float(order_total or 0),
                )

        elif topic == "orders/fulfilled" or topic == "orders/cancelled":
            order_data = body.get("data", body)
            shopify_order_id = str(order_data.get("id", ""))
            order = db.query(Order).filter(Order.shopify_order_id == shopify_order_id).first()

            if order:
                if topic == "orders/fulfilled":
                    order.status = order_data.get("fulfillment_status") or "fulfilled"
                else:
                    order.status = order_data.get("cancel_reason") or "cancelled"
                db.commit()

            if order_data.get("email"):
                background_tasks.add_task(
                    _send_transactional_email_task,
                    "order_fulfilled" if topic == "orders/fulfilled" else "order_cancelled",
                    order_data,
                    shopify_order_id,
                )
        
        elif topic == "abandoned_checkouts/create" or topic == "checkouts/create" or topic == "checkouts/update":
            checkout_data = body.get("data", body)
            
            customer = get_or_create_customer(
                db,
                email=checkout_data.get("email"),
                phone=checkout_data.get("phone")
            )
            
            event = Event(
                customer_id=customer.id,
                email=customer.email,
                event_type="abandoned_checkout",
                source="shopify",
                event_data={
                    "checkout_id": checkout_data.get("id"),
                    "total": checkout_data.get("total_price"),
                    "items": checkout_data.get("line_items", [])
                },
                timestamp=datetime.utcnow()
            )
            
            db.add(event)
            db.commit()
        
        # Match conversions in background
        background_tasks.add_task(_run_conversion_match_task)
        
        return {"status": "received", "topic": topic}
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    
    finally:
        db.close()


@router.post("/webhooks/shopify/{legacy_topic_path}")
async def shopify_webhook_legacy_path(
    legacy_topic_path: str,
    request: Request,
    background_tasks: BackgroundTasks,
    x_shopify_hmac_sha256: Optional[str] = Header(None),
):
    return await shopify_webhook(request, background_tasks, x_shopify_hmac_sha256)


@router.post("/events/ga4")
async def ga4_event(event_create: EventCreate, background_tasks: BackgroundTasks):
    """
    Receive GA4 events forwarded via GTM Server container
    
    Event types: page_view, view_item, add_to_cart, begin_checkout, purchase
    """
    from crm_models import Event, Order
    
    db = SessionLocal()
    
    try:
        customer = get_or_create_customer(
            db,
            email=event_create.email
        )
        
        event = Event(
            customer_id=customer.id,
            email=event_create.email,
            event_type=event_create.event_type,
            source="ga4",
            event_data=event_create.event_data,
            timestamp=event_create.timestamp
        )
        
        db.add(event)
        
        # If purchase event, update customer
        if event_create.event_type == "purchase":
            transaction_id = event_create.event_data.get("transaction_id")
            value = event_create.event_data.get("value", 0)
            
            customer.total_spent += value
            customer.last_order_date = event_create.timestamp
            
            # Create order record if doesn't exist
            if transaction_id:
                order = db.query(Order).filter(Order.shopify_order_id == transaction_id).first()
                if not order:
                    order = Order(
                        customer_id=customer.id,
                        shopify_order_id=transaction_id,
                        email=event_create.email,
                        order_date=event_create.timestamp,
                        total_amount=value,
                        currency=event_create.event_data.get("currency", "INR"),
                        status="completed",
                        items=event_create.event_data.get("items", [])
                    )
                    db.add(order)
                    customer.orders_count += 1
        
        db.commit()
        background_tasks.add_task(_run_conversion_match_task)

        return {"status": "event_recorded", "event_type": event_create.event_type}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    finally:
        db.close()


@router.post("/events/google-ads")
async def google_ads_conversion(conversion: ConversionCreate, background_tasks: BackgroundTasks):
    """
    Receive Google Ads conversion confirmations
    """
    from crm_models import ConversionFeed
    
    db = SessionLocal()
    
    try:
        conversion_feed = ConversionFeed(
            source="google_ads",
            external_id=conversion.external_id,
            email=conversion.email,
            phone=conversion.phone,
            conversion_type=conversion.conversion_type,
            conversion_value=conversion.conversion_value,
            currency=conversion.currency,
            campaign_id=conversion.campaign_id,
            campaign_name=conversion.campaign_name,
            gclid=conversion.gclid,
            timestamp=conversion.timestamp
        )
        
        db.add(conversion_feed)
        db.commit()

        background_tasks.add_task(_run_conversion_match_task)

        return {"status": "conversion_recorded", "source": "google_ads"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    finally:
        db.close()


@router.post("/events/meta")
async def meta_conversion(conversion: ConversionCreate, background_tasks: BackgroundTasks):
    """
    Receive Meta Ads conversion confirmations
    """
    from crm_models import ConversionFeed
    
    db = SessionLocal()
    
    try:
        conversion_feed = ConversionFeed(
            source="meta",
            external_id=conversion.external_id,
            email=conversion.email,
            phone=conversion.phone,
            conversion_type=conversion.conversion_type,
            conversion_value=conversion.conversion_value,
            currency=conversion.currency,
            campaign_id=conversion.campaign_id,
            campaign_name=conversion.campaign_name,
            fbp=conversion.fbp,
            timestamp=conversion.timestamp
        )
        
        db.add(conversion_feed)
        db.commit()

        background_tasks.add_task(_run_conversion_match_task)

        return {"status": "conversion_recorded", "source": "meta"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))

    finally:
        db.close()


@router.get("/customers/{email}", response_model=CustomerResponse)
async def get_customer(email: str):
    """Get customer by email"""
    from crm_models import Customer
    
    db = SessionLocal()
    
    try:
        customer = db.query(Customer).filter(Customer.email == email).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        return customer
    
    finally:
        db.close()


@router.get("/customers")
async def list_customers(skip: int = 0, limit: int = 100, min_orders: int = 0, min_spent: float = 0):
    """List customers with filters"""
    from crm_models import Customer
    
    db = SessionLocal()
    
    try:
        query = db.query(Customer)
        
        if min_orders > 0:
            query = query.filter(Customer.orders_count >= min_orders)
        
        if min_spent > 0:
            query = query.filter(Customer.total_spent >= min_spent)
        
        customers = query.offset(skip).limit(limit).all()
        count = query.count()
        
        return {
            "total": count,
            "skip": skip,
            "limit": limit,
            "customers": [CustomerResponse.from_orm(c) for c in customers]
        }
    
    finally:
        db.close()


@router.post("/segments")
async def create_segment(name: str, description: str, rule_set: Dict[str, Any]):
    """Create a customer segment based on rules"""
    from crm_models import Segment
    
    db = SessionLocal()
    
    try:
        segment = Segment(
            name=name,
            description=description,
            rule_set=rule_set
        )
        
        db.add(segment)
        db.commit()
        db.refresh(segment)
        
        return segment
    
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    
    finally:
        db.close()


@router.get("/health")
async def crm_health():
    """CRM API health check"""
    return {"status": "healthy", "module": "crm"}


@router.get("/health/comprehensive")
async def comprehensive_health():
    """
    Comprehensive system health check.
    Returns detailed status of all critical components: database, Redis, WebSocket, background jobs.
    """
    from datetime import datetime
    from crm_models import Journey
    import psutil
    import redis
    
    db = SessionLocal()
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {
            "database": {"status": "unknown", "response_time_ms": 0},
            "redis": {"status": "unknown", "response_time_ms": 0},
            "websocket": {"status": "unknown", "active_connections": 0},
            "api_latency": {"p50": 0, "p95": 0, "p99": 0},
            "background_jobs": {"pending": 0, "running": 0, "failed": 0},
        }
    }
    
    try:
        # Check database connection
        start = time.time()
        try:
            journey_count = db.query(Journey).limit(1).count()
            db_latency = (time.time() - start) * 1000
            health_status["checks"]["database"] = {
                "status": "healthy",
                "response_time_ms": round(db_latency, 2),
            }
        except Exception as e:
            health_status["checks"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # Check Redis connection
        try:
            redis_url = os.environ.get("REDIS_URL", "redis://pureleven-redis:6379")
            r = redis.from_url(redis_url)
            start = time.time()
            r.ping()
            redis_latency = (time.time() - start) * 1000
            health_status["checks"]["redis"] = {
                "status": "healthy",
                "response_time_ms": round(redis_latency, 2),
            }
        except Exception as e:
            health_status["checks"]["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
        
        # WebSocket status (placeholder - would need active connection tracking)
        health_status["checks"]["websocket"] = {
            "status": "healthy",
            "active_connections": 0,  # Would come from realtime_routes
        }
        
        # API latency (placeholder - would be calculated from Prometheus metrics)
        health_status["checks"]["api_latency"] = {
            "p50": 120,
            "p95": 500,
            "p99": 1200,
        }
        
        # Background jobs (placeholder - would track scheduled jobs)
        health_status["checks"]["background_jobs"] = {
            "pending": 0,
            "running": 0,
            "failed": 0,
        }
        
    except Exception as e:
        logger.error("Comprehensive health check failed: %s", e)
        health_status["status"] = "unhealthy"
    finally:
        db.close()
    
    return health_status


# ─── PHASE 1: MICRO-CONVERSIONS ──────────────────────────────────────────────

_MICRO_EVENT_TYPES = frozenset([
    "email_capture",       # Newsletter / exit-intent email signup
    "delivery_check",      # User checked delivery to pincode
    "pincode_validation",  # Pincode lookup event
    "impulse_signal",      # High-intent on-page signal (30s on product, scroll-depth)
    "purchase_intent",     # Begin checkout / proceed to payment
    "wishlist_add",        # Added to wishlist
    "review_click",        # Clicked on review section
    "benefit_hover",       # Hovered on product benefits section
])


class MicroConversionEvent(BaseModel):
    type: str                        # one of _MICRO_EVENT_TYPES
    session_id: Optional[str] = None
    email: Optional[str] = None
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    pincode: Optional[str] = None
    page_url: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None


@router.post("/events/micro")
async def log_micro_conversion(payload: MicroConversionEvent):
    """
    Phase 1: Log high-intent micro-conversion signals.
    Used for propensity scoring and N8N trigger evaluation.
    """
    from crm_models import Event

    if payload.type not in _MICRO_EVENT_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown micro event type '{payload.type}'. Valid: {sorted(_MICRO_EVENT_TYPES)}"
        )

    db = SessionLocal()
    try:
        customer = None
        if payload.email:
            customer = get_or_create_customer(db, email=payload.email)

        event = Event(
            customer_id=customer.id if customer else None,
            email=payload.email,
            event_type=f"micro_{payload.type}",
            source="frontend",
            session_id=payload.session_id,
            event_data={
                "micro_type":   payload.type,
                "product_id":   payload.product_id,
                "product_name": payload.product_name,
                "pincode":      payload.pincode,
                "page_url":     payload.page_url,
                **(payload.extra or {}),
            },
            timestamp=payload.timestamp or datetime.now(timezone.utc),
        )
        db.add(event)
        db.commit()

        return {"status": "recorded", "micro_type": payload.type}

    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        db.close()


class PageViewEvent(BaseModel):
    session_id:   Optional[str] = None
    gclid:        Optional[str] = None
    fbclid:       Optional[str] = None
    fbp:          Optional[str] = None
    fbc:          Optional[str] = None
    ga_client_id: Optional[str] = None
    ga_session_id: Optional[str] = None
    utm_source:   Optional[str] = None
    utm_medium:   Optional[str] = None
    utm_campaign: Optional[str] = None
    utm_content:  Optional[str] = None
    utm_term:     Optional[str] = None
    page_type:    Optional[str] = None
    landing_page: Optional[str] = None
    page_url:     Optional[str] = None
    page_title:   Optional[str] = None
    referrer:     Optional[str] = None
    device_type:  Optional[str] = None
    email:        Optional[str] = None
    phone:        Optional[str] = None


@router.post("/events/page_view")
async def log_page_view(payload: PageViewEvent, request: Request):
    """
    Receive page view events from TRAFFIC_SOURCE_TRACKING.js on Shopify.
    Stores gclid/fbclid/UTM attribution data in crm_events for later order linkage.
    This is the primary mechanism for capturing ad attribution before purchase.
    """
    from crm_models import Event

    db = SessionLocal()
    try:
        customer = None
        if payload.email:
            customer = get_or_create_customer(db, email=payload.email)

        event = Event(
            customer_id=customer.id if customer else None,
            email=payload.email,
            event_type="page_view",
            source="shopify_frontend",
            session_id=payload.session_id,
            event_data={
                "gclid":        payload.gclid,
                "fbclid":       payload.fbclid,
                "fbp":          payload.fbp,
                "fbc":          payload.fbc,
                "ga_client_id": payload.ga_client_id,
                "ga_session_id": payload.ga_session_id,
                "utm_source":   payload.utm_source,
                "utm_medium":   payload.utm_medium,
                "utm_campaign": payload.utm_campaign,
                "utm_content":  payload.utm_content,
                "utm_term":     payload.utm_term,
                "page_type":    payload.page_type,
                "landing_page": payload.landing_page or payload.page_url,
                "page_url":     payload.page_url,
                "page_title":   payload.page_title,
                "referrer":     payload.referrer,
                "device_type":  payload.device_type,
                "client_ip":    request.headers.get("x-real-ip") or request.headers.get("x-forwarded-for", "").split(",")[0].strip(),
                "user_agent":   request.headers.get("user-agent", ""),
            },
            timestamp=datetime.now(timezone.utc),
        )
        db.add(event)
        db.commit()

        return {"status": "recorded", "session_id": payload.session_id}

    except Exception as exc:
        db.rollback()
        logger.warning("page_view event error: %s", exc)
        return {"status": "error"}  # never fail the browser
    finally:
        db.close()


@router.get("/tracking/status")
async def tracking_status():
    """
    Phase 1 health dashboard: Returns counts of events/orders processed today
    and flags any deduplication or fraud scoring stats.
    """
    db = SessionLocal()
    try:
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0)

        result = db.execute(text("""
            SELECT
              (SELECT COUNT(*) FROM crm_orders WHERE created_at >= :today)        AS orders_today,
              (SELECT COUNT(*) FROM crm_orders
               WHERE created_at >= :today AND rto = false)                         AS valid_orders,
              (SELECT COUNT(*) FROM crm_events WHERE created_at >= :today)         AS events_today,
              (SELECT COUNT(*) FROM crm_events
               WHERE created_at >= :today AND event_type LIKE 'micro_%')           AS micro_events_today,
              (SELECT COUNT(*) FROM crm_customers)                                 AS total_customers,
              (SELECT COUNT(*) FROM crm_customers WHERE orders_count > 0)          AS buyers_total
        """), {"today": today_start}).fetchone()

        return {
            "status": "ok",
            "date":   today_start.date().isoformat(),
            "phase1": {
                "orders_today":       result[0],
                "valid_orders_today": result[1],
                "events_today":       result[2],
                "micro_events_today": result[3],
                "total_customers":    result[4],
                "buyers_total":       result[5],
            },
        }
    finally:
        db.close()

class IdentifyPayload(BaseModel):
    session_id:  Optional[str] = None
    gclid:       Optional[str] = None
    fbclid:      Optional[str] = None
    fbp:         Optional[str] = None
    fbc:         Optional[str] = None
    ga_client_id: Optional[str] = None
    email:       Optional[str] = None
    phone:       Optional[str] = None
    utm_source:  Optional[str] = None


@router.post("/identify")
async def identify(payload: IdentifyPayload):
    """
    Resolve or create a unified_identity record for this visitor.
    Called by TRAFFIC_SOURCE_TRACKING.js on every page load.
    Returns {identity_id, is_new}.
    """
    from crm_identity import IdentityResolver
    db = SessionLocal()
    try:
        resolver = IdentityResolver(db)
        identity_id, is_new = resolver.resolve(payload.dict())
        return {"identity_id": identity_id, "is_new": is_new}
    except Exception as exc:
        logger.warning("identify error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        db.close()


# ─── PHASE 2: SHIPROCKET WEBHOOK ──────────────────────────────────────────────

@router.api_route("/webhooks/delivery-status", methods=["GET", "POST", "OPTIONS", "HEAD"])
@router.api_route("/webhooks/shiprocket", methods=["GET", "POST", "OPTIONS", "HEAD"])
async def shiprocket_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_shiprocket_hmac: Optional[str] = Header(None),
):
    """
    Receive Shiprocket delivery status webhooks.
    On 'Delivered': fire offline conversion to Meta CAPI + Google Ads.
    On 'RTO':       mark order as RTO and suppress from buyer audiences.
    """
    from crm_models import Order, Customer

    raw_body = await request.body()

    # Validate HMAC signature (if token is configured)
    shiprocket_token = os.getenv("SHIPROCKET_WEBHOOK_TOKEN", "")
    if shiprocket_token and x_shiprocket_hmac:
        expected = hmac.new(
            shiprocket_token.encode(), raw_body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, x_shiprocket_hmac or ""):
            raise HTTPException(status_code=401, detail="Invalid signature")

    if not raw_body:
        logger.warning("Shiprocket webhook received an empty body")
        return {"status": "ignored", "reason": "empty_body"}

    try:
        body = json.loads(raw_body)
    except Exception:
        logger.warning("Shiprocket webhook received non-JSON body")
        return {"status": "ignored", "reason": "invalid_json"}

    status   = (body.get("current_status") or body.get("status") or "").strip()
    order_id = str(body.get("order_id") or body.get("channel_order_id") or "")

    db = SessionLocal()
    try:
        # Find order in CRM
        crm_order = (
            db.query(Order)
            .filter(Order.shopify_order_id == order_id)
            .first()
        )
        if not crm_order:
            return {"status": "order_not_found", "order_id": order_id}

        if "delivered" in status.lower():
            crm_order.delivered_at = datetime.now(timezone.utc)
            crm_order.rto = False
            db.commit()

            # Build minimal order_data for fan-out
            customer = db.query(Customer).filter(
                Customer.id == crm_order.customer_id).first()
            order_data_enr = {
                "id":          order_id,
                "total_price": str(crm_order.total_amount),
                "currency":    crm_order.currency,
                "email":       crm_order.email or (customer.email if customer else None),
                "created_at":  crm_order.order_date.isoformat() if crm_order.order_date else None,
                "line_items":  crm_order.items or [],
                "_gclid":      crm_order.gclid,
                "_fbclid":     crm_order.fbclid,
                "billing_address": {"phone": customer.phone if customer else None},
            }

            if not crm_order.offline_conversion_sent:
                client_ip  = request.client.host if request.client else ""
                user_agent = request.headers.get("user-agent", "")
                # Meta: second Purchase event with delivery event_id for dedup
                background_tasks.add_task(
                    fire_meta_capi, order_data_enr, client_ip, user_agent,
                    "Purchase", "delivery"
                )
                # Google: cod_delivered conversion action
                background_tasks.add_task(fire_google_conversion, order_data_enr, "cod_delivered")
                crm_order.offline_conversion_sent = True
                db.commit()

            logger.info("Shiprocket delivered: order=%s", order_id)
            return {"status": "delivery_attributed", "order_id": order_id}

        elif "out for delivery" in status.lower() or "out_for_delivery" in status.lower():
            crm_order.status = "out_for_delivery"
            db.commit()

            # Send out-for-delivery email
            customer = db.query(Customer).filter(
                Customer.id == crm_order.customer_id).first()
            recipient = crm_order.email or (customer.email if customer else None)
            if recipient:
                payment_method = crm_order.payment_method or "prepaid"
                cod_reminder = (
                    "<p style=\"margin:8px 0 0;font-size:14px;color:#E65100\">"
                    "<strong>💰 Please keep ₹"
                    + str(int(crm_order.total_amount or 0))
                    + " ready in cash</strong> to pay the delivery person.</p>"
                    if payment_method == "cod" else ""
                )
                sub = {
                    "customer_name": (customer.first_name if customer else None) or "there",
                    "order_id": order_id,
                    "items": ", ".join(
                        f"{item.get('quantity', 1)} x {item.get('name') or item.get('title', 'Item')}"
                        for item in (crm_order.items or [])
                    ) or "your order",
                    "delivery_address": _format_shipping_address(crm_order.shipping_address),
                    "tracking_url": body.get("tracking_url") or f"{os.getenv('SITE_URL', 'https://pureleven.com')}/account",
                    "unsubscribe_url": f"{os.getenv('SITE_URL', 'https://pureleven.com')}/pages/contact",
                    "cod_reminder": cod_reminder,
                }
                background_tasks.add_task(
                    _send_transactional_email_task,
                    "out_for_delivery",
                    {"email": recipient, **{k: v for k, v in sub.items()}},
                    f"ofd:{order_id}",
                )

            logger.info("Shiprocket out-for-delivery: order=%s", order_id)
            return {"status": "out_for_delivery_notified", "order_id": order_id}

        elif "rto" in status.lower() or "return" in status.lower():
            crm_order.rto = True
            db.commit()
            logger.info("Shiprocket RTO: order=%s", order_id)
            return {"status": "rto_marked", "order_id": order_id}

        return {"status": "ignored", "received_status": status}

    except Exception as exc:
        db.rollback()
        logger.error("Shiprocket webhook error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        db.close()


# ─── PHASE 3: AUDIENCE EXPORT ─────────────────────────────────────────────────

@router.get("/audiences/{segment_name}/export")
async def export_audience(
    segment_name: str,
    format: str = "meta",
    request: Request = None,
):
    """
    Export a named audience segment for ad platform upload.
    format=meta  → JSON list of {em, ph} (hashed, for Meta Custom Audiences)
    format=google → CSV (Email Address,Phone Number,First Name,Last Name) for Google Customer Match
    Requires: Authorization: Bearer {INTERNAL_API_KEY} header.
    """
    internal_key = os.getenv("INTERNAL_API_KEY", "")
    if internal_key:
        auth = (request.headers.get("authorization") or "").replace("Bearer ", "").strip()
        if auth != internal_key:
            raise HTTPException(status_code=401, detail="Unauthorized")

    from crm_audiences import AudienceEngine
    from crm_models import Customer
    import hashlib as _h

    db = SessionLocal()
    try:
        engine = AudienceEngine(db)

        # Use audience engine logic to get matching customer IDs
        if segment_name == "all_buyers":
            rows = db.query(Customer).filter(Customer.orders_count > 0).all()
        elif segment_name == "high_ltv":
            rows = db.query(Customer).filter(
                Customer.orders_count > 0, Customer.total_spent > 2000).all()
        elif segment_name == "replenishment_due":
            cutoff_low  = datetime.now(timezone.utc) - timedelta(days=50)
            cutoff_high = datetime.now(timezone.utc) - timedelta(days=30)
            rows = db.query(Customer).filter(
                Customer.orders_count > 0,
                Customer.last_order_date.between(cutoff_low, cutoff_high),
            ).all()
        elif segment_name == "lapsed_buyer":
            cutoff = datetime.now(timezone.utc) - timedelta(days=60)
            rows = db.query(Customer).filter(
                Customer.orders_count > 0,
                Customer.last_order_date < cutoff,
            ).all()
        else:
            # Generic: classify all customers and filter by segment name
            all_customers = db.query(Customer).limit(2000).all()
            rows = []
            for c in all_customers:
                segs = engine.classify(c.id)
                if segment_name in segs:
                    rows.append(c)

        def _sha256_field(v: str | None) -> str | None:
            if not v:
                return None
            return _h.sha256(v.strip().lower().encode()).hexdigest()

        if format == "google":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["Email Address", "Phone Number", "First Name", "Last Name"])
            for c in rows:
                writer.writerow([
                    c.email or "",
                    c.phone or "",
                    c.first_name or "",
                    c.last_name or "",
                ])
            from fastapi.responses import PlainTextResponse
            return PlainTextResponse(
                output.getvalue(),
                media_type="text/csv",
                headers={"Content-Disposition": f'attachment; filename="{segment_name}.csv"'},
            )
        else:  # meta
            records = []
            for c in rows:
                rec: dict = {}
                if c.email:
                    rec["em"] = [_sha256_field(c.email)]
                if c.phone:
                    digits = "".join(x for x in c.phone if x.isdigit())
                    if len(digits) == 10:
                        digits = "91" + digits
                    rec["ph"] = [_sha256_field(digits)]
                if rec:
                    records.append(rec)
            return {"segment": segment_name, "count": len(records), "data": records}

    finally:
        db.close()


# ─── PHASE 3: ABANDONMENT POLLING (for N8N) ──────────────────────────────────

@router.get("/abandonment/checkout")
async def checkout_abandonment(window_minutes: int = 15, limit: int = 50):
    """
    Return checkout events that fired ≥ window_minutes ago with no purchase.
    N8N polls this on a schedule to trigger WhatsApp + retargeting.
    """
    from crm_audiences import AudienceEngine
    db = SessionLocal()
    try:
        engine = AudienceEngine(db)
        candidates = engine.checkout_abandonment_candidates(
            window_minutes=window_minutes, limit=limit)
        return {"count": len(candidates), "candidates": candidates}
    finally:
        db.close()


@router.get("/abandonment/cart")
async def cart_abandonment(window_minutes: int = 30, limit: int = 50):
    """
    Return cart events that fired ≥ window_minutes ago with no checkout.
    N8N polls this to trigger cart recovery messages.
    """
    from crm_audiences import AudienceEngine
    db = SessionLocal()
    try:
        engine = AudienceEngine(db)
        candidates = engine.cart_abandonment_candidates(
            window_minutes=window_minutes, limit=limit)
        return {"count": len(candidates), "candidates": candidates}
    finally:
        db.close()


@router.patch("/abandonment/{event_id}/mark_notified")
async def mark_abandonment_notified(event_id: str):
    """
    Mark an event as n8n_notified=true to prevent duplicate WhatsApp sends.
    Called by N8N immediately after dispatching a message.
    """
    from crm_models import Event
    db = SessionLocal()
    try:
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        event.n8n_notified = True
        db.commit()
        return {"status": "marked", "event_id": event_id}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        db.close()


@router.post("/audiences/refresh")
async def refresh_audiences(background_tasks: BackgroundTasks):
    """
    Trigger a full audience reclassification for all customers.
    Can be called by a cron job or N8N on a daily schedule.
    """
    from crm_audiences import AudienceEngine
    bg_db = SessionLocal()

    def _run():
        try:
            count = AudienceEngine(bg_db).refresh_all()
            logger.info("Audience refresh complete: %d customers", count)
        finally:
            bg_db.close()

    background_tasks.add_task(_run)
    return {"status": "refresh_queued"}


# ─── PHASE 3: BUDGET SAFEGUARDS ───────────────────────────────────────────────

# Hard daily spend caps (INR). Change via environment variables to avoid code deploys.
# Google: 3 campaigns × ~₹100/day = ₹300 normal, ₹350 max
# Meta  : 4 campaigns × ~₹90/day  = ₹360 normal, ₹400 max
_BUDGET_CAPS = {
    "google": int(os.getenv("BUDGET_CAP_GOOGLE_INR", "350")),
    "meta":   int(os.getenv("BUDGET_CAP_META_INR",   "400")),
    "total":  int(os.getenv("BUDGET_CAP_TOTAL_INR",  "950")),
}

# Campaign budget allocation (used by N8N and AI review)
CAMPAIGN_BUDGET_PLAN = {
    "google": [
        {"id": "highintent_search",  "name": "HighIntent_Search",  "daily_budget_inr": 150,
         "bidding": "target_cpa",    "target_cpa": 500,   "match_types": ["exact", "phrase"]},
        {"id": "category_search",    "name": "Category_Search",    "daily_budget_inr": 100,
         "bidding": "maximize_clicks","match_types": ["broad_modified", "phrase"]},
        {"id": "brand_pureleven",    "name": "Brand_PureLeven",    "daily_budget_inr": 50,
         "bidding": "target_cpa",    "target_cpa": 300,   "match_types": ["exact", "phrase"]},
    ],
    "meta": [
        {"id": "tof_video_cold",       "name": "TOF_Video_Cold",       "monthly_budget_inr": 4000,
         "daily_budget_inr": 133, "objective": "awareness",     "audience": "cold_lookalike_1pct"},
        {"id": "product_viewers",      "name": "ProductViewers_Retarget","monthly_budget_inr": 3500,
         "daily_budget_inr": 117, "objective": "conversions",   "audience": "product_viewers_30d"},
        {"id": "cart_abandon_recovery","name": "CartAbandon_Recovery", "monthly_budget_inr": 2000,
         "daily_budget_inr": 67,  "objective": "conversions",   "audience": "cart_abandoners_7d"},
        {"id": "checkout_recovery",    "name": "CheckoutRecovery",     "monthly_budget_inr": 1500,
         "daily_budget_inr": 50,  "objective": "conversions",   "audience": "checkout_abandoners_3d"},
    ],
}


@router.get("/budgets/status")
async def budget_status():
    """
    Phase 3: Return current daily budget caps and today's order-based spend estimate.
    Used by N8N to gate whether new campaigns can run.
    N8N workflow should check: if total_estimated_spend > cap → pause low-priority campaigns.
    """
    db = SessionLocal()
    try:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        # Count today's orders as a proxy for spend (real ad spend requires platform API)
        today_orders = db.execute(
            text("SELECT COUNT(*), COALESCE(SUM(total_amount), 0) FROM crm_orders WHERE created_at >= :today"),
            {"today": today_start}
        ).fetchone()

        order_count = today_orders[0] or 0
        order_revenue = float(today_orders[1] or 0)

        return {
            "status": "ok",
            "date":   today_start.date().isoformat(),
            "caps":   _BUDGET_CAPS,
            "today_orders":  order_count,
            "today_revenue": order_revenue,
            "campaign_plan": CAMPAIGN_BUDGET_PLAN,
            "note": "Real ad spend requires Google/Meta API. Use platform dashboards for actuals.",
        }
    finally:
        db.close()


@router.get("/budgets/plan")
async def campaign_plan():
    """Return full campaign budget allocation plan. Used by N8N + AI review."""
    return {
        "caps":      _BUDGET_CAPS,
        "campaigns": CAMPAIGN_BUDGET_PLAN,
        "total_daily_planned_inr": sum(
            c["daily_budget_inr"] for c in CAMPAIGN_BUDGET_PLAN["google"]
        ) + sum(
            c["daily_budget_inr"] for c in CAMPAIGN_BUDGET_PLAN["meta"]
        ),
    }

@router.post("/webhooks/wabis")
async def wabis_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receive Wabis WhatsApp delivery and reply webhooks.

    Expected payload from Wabis:
      { "type": "message_status" | "incoming_message",
        "phone": "919876543210",
        "status": "delivered" | "read" | "failed",
        "message_id": "...",
        "timestamp": "...",
        "text": "..."    (only for incoming_message) }

    Actions:
    - message_status/delivered → record wabis_delivered event
    - incoming_message         → record wabis_reply event + tag customer
    """
    from crm_models import Customer, Event

    raw_body = await request.body()

    # Optional bearer-token auth (set WABIS_WEBHOOK_SECRET in .env)
    wabis_secret = os.getenv("WABIS_WEBHOOK_SECRET", "")
    if wabis_secret:
        auth_header = (request.headers.get("authorization") or "").replace("Bearer ", "").strip()
        if auth_header != wabis_secret:
            raise HTTPException(status_code=401, detail="Invalid Wabis webhook secret")

    if not raw_body:
        return {"status": "ignored", "reason": "empty_body"}

    try:
        body = json.loads(raw_body)
    except Exception:
        return {"status": "ignored", "reason": "invalid_json"}

    event_type_in = body.get("type", "")
    phone_raw     = str(body.get("phone") or "")
    message_id    = str(body.get("message_id") or "")
    status_raw    = str(body.get("status") or "")
    timestamp_raw = body.get("timestamp")
    text_content  = body.get("text") or ""

    # Normalise phone to E.164-ish (digits only, ensure 91 prefix for IN)
    phone_digits = "".join(c for c in phone_raw if c.isdigit())
    if len(phone_digits) == 10:
        phone_digits = "91" + phone_digits
    elif phone_digits.startswith("0") and len(phone_digits) == 11:
        phone_digits = "91" + phone_digits[1:]

    try:
        event_ts = datetime.fromisoformat(str(timestamp_raw).replace("Z", "+00:00"))
    except Exception:
        event_ts = datetime.now(timezone.utc)

    db = SessionLocal()
    try:
        # Lookup customer by phone
        customer = None
        if phone_digits:
            customer = (
                db.query(Customer)
                .filter(Customer.phone.in_([phone_digits, "+" + phone_digits, phone_raw]))
                .first()
            )
        if not customer and phone_digits:
            # Create minimal customer record so event is linkable
            customer = Customer(phone=phone_digits)
            db.add(customer)
            db.flush()

        if event_type_in == "message_status":
            if status_raw in ("delivered", "read"):
                crm_event_type = "wabis_delivered" if status_raw == "delivered" else "wabis_read"
            else:
                crm_event_type = "wabis_failed"

        elif event_type_in == "incoming_message":
            crm_event_type = "wabis_reply"
            # Tag customer as engaged_whatsapp
            if customer:
                tags = list(customer.tags or [])
                if "engaged_whatsapp" not in tags:
                    tags.append("engaged_whatsapp")
                    customer.tags = tags
        else:
            crm_event_type = f"wabis_{event_type_in}"

        event = Event(
            customer_id=customer.id if customer else None,
            email=customer.email if customer else None,
            event_type=crm_event_type,
            source="wabis",
            event_data={
                "message_id":  message_id,
                "status":      status_raw,
                "phone":       phone_digits,
                "text":        text_content,
                "raw_type":    event_type_in,
            },
            timestamp=event_ts,
        )
        db.add(event)
        db.commit()

        logger.info("Wabis webhook: type=%s status=%s phone=%s", event_type_in, status_raw, phone_digits)
        return {"status": "recorded", "event_type": crm_event_type}

    except Exception as exc:
        db.rollback()
        logger.error("Wabis webhook error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        db.close()


# ─── PHASE 4: WABIS OUTBOUND SEND ─────────────────────────────────────────────

WABIS_BASE_URL = "https://bot.wabis.in/api/v1/whatsapp"
WABIS_PHONE_NUMBER_ID = "252036884661683"  # PureLeven Exim (+918848265849)

class WabisMessagePayload(BaseModel):
    phone: str
    template_id: int          # Wabis internal template ID (from /wabis/templates)
    template_name: Optional[str] = None  # for logging only
    params: Optional[List[str]] = None
    header_image_url: Optional[str] = None  # URL for IMAGE-header templates
    customer_email: Optional[str] = None


@router.get("/wabis/templates")
async def wabis_templates():
    """Fetch approved WhatsApp templates from Wabis for PureLeven Exim (30-min cache)."""
    import urllib.request, urllib.error, urllib.parse, re
    wabis_api_key = os.getenv("WABIS_API_TOKEN") or os.getenv("WABIS_API_KEY", "")
    if not wabis_api_key:
        raise HTTPException(status_code=503, detail="WABIS_API_TOKEN not configured")

    # Use shared cache
    if _time.time() - _WABIS_TMPL_CACHE["ts"] < _TMPL_CACHE_TTL and _WABIS_TMPL_CACHE["data"]:
        raw_list = _WABIS_TMPL_CACHE["data"]
    else:
        params = urllib.parse.urlencode({"apiToken": wabis_api_key, "phone_number_id": WABIS_PHONE_NUMBER_ID})
        url = f"{WABIS_BASE_URL}/template/list?{params}"
        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "curl/7.88.1"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read())
        except Exception as exc:
            logger.warning("Wabis template list error: %s", exc)
            raise HTTPException(status_code=502, detail=str(exc))
        raw_list = data.get("message", [])
        if not isinstance(raw_list, list):
            raw_list = []
        _WABIS_TMPL_CACHE["data"] = raw_list
        _WABIS_TMPL_CACHE["ts"] = _time.time()

    templates = raw_list

    def _parse_wabis_template(t: dict) -> dict:
        """Normalize a raw Wabis template dict into a clean unified structure."""
        raw_json = t.get("template_json") or "{}"
        try:
            tj = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        except Exception:
            tj = {}
        components = tj.get("components") or []

        raw_var_map = t.get("variable_map") or "{}"
        try:
            var_map = json.loads(raw_var_map) if isinstance(raw_var_map, str) else raw_var_map
        except Exception:
            var_map = {}

        header = footer = None
        body = {"text": t.get("body_content", ""), "vars": 0, "examples": [], "meta_text": ""}
        buttons: list = []
        raw_header_subtype = t.get("header_subtype", "").lower()  # 'none','text','image','video'

        for comp in components:
            ctype = comp.get("type", "").lower()
            text = comp.get("text", "")
            var_positions = [int(m) for m in re.findall(r"\{\{(\d+)\}\}", text)]
            n_vars = len(set(var_positions))
            ex_vals: list[str] = []
            ex = comp.get("example", {})
            if ctype == "header":
                ex_vals = ex.get("header_text", [])
                fmt = comp.get("format", "TEXT").upper()
                header = {"text": text, "format": fmt, "vars": n_vars, "examples": ex_vals}
            elif ctype == "body":
                raw_body_ex = ex.get("body_text", [[]])
                ex_vals = raw_body_ex[0] if raw_body_ex else []
                body = {"text": text, "vars": n_vars, "examples": ex_vals, "meta_text": text}
            elif ctype == "footer":
                footer = {"text": text, "vars": n_vars}
            elif ctype == "buttons":
                for btn in comp.get("buttons", []):
                    btn_ex = btn.get("example", [])
                    var_cnt = len(re.findall(r"\{\{\d+\}\}", btn.get("text", "")))
                    buttons.append({"type": btn.get("type", ""), "text": btn.get("text", ""), "vars": var_cnt, "examples": btn_ex})

        # Build var_labels: {1: "First Name", 2: "Product List", ...}
        var_labels: dict[str, str] = {}
        body_vars = var_map.get("body", {})
        if isinstance(body_vars, dict):
            for pos, raw_label in body_vars.items():
                clean = str(raw_label).strip("#").strip("!").replace("-", " ").replace("_", " ").title()
                var_labels[str(pos)] = clean

        total_vars = body.get("vars", 0)
        if header:
            total_vars += header.get("vars", 0)
        for b in buttons:
            total_vars += b.get("vars", 0)

        # Determine sendability
        locale = t.get("locale", "en_US")
        header_format = raw_header_subtype if raw_header_subtype != "none" else ("text" if header else "none")
        send_issue = None
        if header_format in ("image", "video") and not t.get("header_content", ""):
            send_issue = "image_header"  # needs image URL at send time
        # locale mismatch: body has non-ASCII chars but locale is en_US = likely ml
        body_text = body.get("text", "")
        if locale == "en_US" and any(ord(c) > 0x0D00 and ord(c) < 0x0D80 for c in body_text):
            send_issue = send_issue or "locale_mismatch"

        return {
            "id": t["id"],
            "meta_template_id": t.get("template_id", ""),
            "name": t.get("template_name", ""),
            "category": t.get("template_category", ""),
            "status": t.get("status", ""),
            "locale": locale,
            "source": "wabis",
            "header": header,
            "header_format": header_format,
            "body": body,
            "footer": footer,
            "buttons": buttons,
            "var_labels": var_labels,
            "total_vars": total_vars,
            "send_issue": send_issue,  # None | 'image_header' | 'locale_mismatch'
        }

    return [_parse_wabis_template(t) for t in templates if t.get("status") == "Approved"]


@router.post("/wabis/send")
async def wabis_send(payload: WabisMessagePayload):
    """
    Proxy endpoint to send a Wabis WhatsApp template message.
    Stores the outbound event in crm_events for tracking.
    Requires env: WABIS_API_TOKEN
    """
    from crm_models import Event

    wabis_api_key = os.getenv("WABIS_API_TOKEN") or os.getenv("WABIS_API_KEY", "")

    if not wabis_api_key:
        raise HTTPException(status_code=503, detail="WABIS_API_TOKEN not configured")

    import urllib.request, urllib.error, urllib.parse

    # Use form-encoded body; apiToken must be a form param (not Bearer header)
    send_params: dict = {
        "apiToken": wabis_api_key,
        "phone_number_id": WABIS_PHONE_NUMBER_ID,
        "phone_number": payload.phone,
        "template_id": payload.template_id,
    }
    # For IMAGE-header templates the caller must supply an image URL.
    # Wabis expects it as 'header_content' in the send/template call.
    if payload.header_image_url:
        send_params["header_content"] = payload.header_image_url

    form_data = urllib.parse.urlencode(send_params).encode()

    try:
        req = urllib.request.Request(
            f"{WABIS_BASE_URL}/send/template",
            data=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json", "User-Agent": "curl/7.88.1"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="ignore")
        logger.warning("Wabis send HTTP %s: %s", exc.code, err_body)
        raise HTTPException(status_code=502, detail=f"Wabis error {exc.code}: {err_body}")
    except Exception as exc:
        logger.warning("Wabis send error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))

    # Wabis returns HTTP 200 even on failure; status "0" = failed, "1" = success
    wabis_ok = str(result.get("status", "0")) == "1"
    if not wabis_ok:
        err_msg = result.get("message", "Unknown Wabis error")
        logger.warning("Wabis send logical failure for template %s: %s", payload.template_id, err_msg)
        raise HTTPException(status_code=400, detail=err_msg)

    # Log outbound event
    db = SessionLocal()
    try:
        customer = None
        if payload.customer_email:
            from crm_models import Customer
            customer = db.query(Customer).filter(Customer.email == payload.customer_email).first()

        event = Event(
            customer_id=customer.id if customer else None,
            email=payload.customer_email,
            event_type="wabis_sent",
            source="wabis",
            event_data={
                "phone":       payload.phone,
                "template_id": payload.template_id,
                "template":    payload.template_name,
                "params":      payload.params,
                "wabis_response": result,
            },
            timestamp=datetime.now(timezone.utc),
        )
        db.add(event)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

    return {"status": "sent", "wabis_response": result}


# ─── TEMPLATE CACHE (30-minute TTL for both Wabis + Meta) ────────────────────

import time as _time

_WABIS_TMPL_CACHE: dict = {"ts": 0.0, "data": []}
_META_TMPL_CACHE:  dict = {"ts": 0.0, "data": []}
_TMPL_CACHE_TTL = 1800  # 30 minutes


async def _get_wabis_templates_cached() -> list:
    """Return cached Wabis templates, refreshing if stale."""
    import urllib.request, urllib.parse
    if _time.time() - _WABIS_TMPL_CACHE["ts"] < _TMPL_CACHE_TTL and _WABIS_TMPL_CACHE["data"]:
        return _WABIS_TMPL_CACHE["data"]
    wabis_api_key = os.getenv("WABIS_API_TOKEN") or os.getenv("WABIS_API_KEY", "")
    if not wabis_api_key:
        return []
    params = urllib.parse.urlencode({"apiToken": wabis_api_key, "phone_number_id": WABIS_PHONE_NUMBER_ID})
    url = f"{WABIS_BASE_URL}/template/list?{params}"
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "curl/7.88.1"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        templates = data.get("message", [])
        if isinstance(templates, list):
            _WABIS_TMPL_CACHE["data"] = templates
            _WABIS_TMPL_CACHE["ts"] = _time.time()
            return templates
    except Exception as exc:
        logger.warning("Wabis template cache refresh error: %s", exc)
    return _WABIS_TMPL_CACHE["data"]


def _parse_meta_template(t: dict) -> dict:
    """Normalize a Meta WhatsApp Cloud API template into the unified structure."""
    import re
    components = t.get("components", [])
    header = footer = None
    body = {"text": "", "vars": 0, "examples": [], "meta_text": ""}
    buttons: list = []
    var_labels: dict[str, str] = {}

    var_idx = 0
    for comp in components:
        ctype = comp.get("type", "").upper()
        text = comp.get("text", "")
        var_positions = [int(m) for m in re.findall(r"\{\{(\d+)\}\}", text)]
        n_vars = len(set(var_positions))

        if ctype == "HEADER":
            ex_vals = comp.get("example", {}).get("header_text", [])
            header = {"text": text, "format": comp.get("format", "TEXT"), "vars": n_vars, "examples": ex_vals}
        elif ctype == "BODY":
            raw_ex = comp.get("example", {}).get("body_text", [[]])
            ex_vals = raw_ex[0] if raw_ex else []
            body = {"text": text, "vars": n_vars, "examples": ex_vals, "meta_text": text}
            for i, ex in enumerate(ex_vals):
                var_labels[str(i + 1)] = ex.replace("-", " ").replace("_", " ").title()
        elif ctype == "FOOTER":
            footer = {"text": text, "vars": n_vars}
        elif ctype == "BUTTONS":
            for btn in comp.get("buttons", []):
                var_cnt = len(re.findall(r"\{\{\d+\}\}", btn.get("text", "")))
                var_idx += 1
                buttons.append({"type": btn.get("type", ""), "text": btn.get("text", ""), "vars": var_cnt, "examples": btn.get("example", [])})

    total_vars = body.get("vars", 0)
    if header:
        total_vars += header.get("vars", 0)
    for b in buttons:
        total_vars += b.get("vars", 0)

    return {
        "id": t.get("id", ""),
        "meta_template_id": t.get("id", ""),
        "name": t.get("name", ""),
        "category": t.get("category", "").capitalize(),
        "status": t.get("status", "").capitalize(),
        "locale": t.get("language", "en_US"),
        "source": "meta",
        "header": header,
        "body": body,
        "footer": footer,
        "buttons": buttons,
        "var_labels": var_labels,
        "total_vars": total_vars,
    }


@router.get("/meta-wa/templates")
async def meta_wa_templates(force_refresh: bool = False):
    """
    Fetch approved WhatsApp templates from Meta WhatsApp Cloud API.
    Requires env vars:
      META_WABA_ID   — WhatsApp Business Account ID (find in Meta Business Manager → WhatsApp → Settings)
      META_WA_TOKEN  — System User token with whatsapp_business_management + whatsapp_business_messaging scopes
                       (different from the CAPI token; generate at business.facebook.com → System Users)
    Results are cached for 30 minutes (unless force_refresh=True).
    """
    import urllib.request, urllib.error, urllib.parse

    if not force_refresh and _time.time() - _META_TMPL_CACHE["ts"] < _TMPL_CACHE_TTL and _META_TMPL_CACHE["data"]:
        return _META_TMPL_CACHE["data"]

    waba_id  = os.getenv("META_WABA_ID", "")
    wa_token = os.getenv("META_WA_TOKEN") or os.getenv("FACEBOOK_ACCESS_TOKEN", "")

    if not waba_id:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "META_WABA_ID not configured",
                "setup": "Set META_WABA_ID env var. Find it: Meta Business Manager → WhatsApp → Business Accounts → copy Account ID",
            },
        )
    if not wa_token:
        raise HTTPException(status_code=503, detail={"error": "META_WA_TOKEN not configured"})

    params = urllib.parse.urlencode({
        "fields": "id,name,components,language,status,category",
        "status": "APPROVED",
        "limit": "100",
        "access_token": wa_token,
    })
    url = f"https://graph.facebook.com/v20.0/{waba_id}/message_templates?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/7.88.1"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="ignore")
        logger.warning("Meta WA templates HTTP %s: %s", exc.code, err_body)
        raise HTTPException(status_code=502, detail={"error": f"Meta API error {exc.code}", "body": err_body})
    except Exception as exc:
        logger.warning("Meta WA templates error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))

    templates = [_parse_meta_template(t) for t in raw.get("data", [])]
    _META_TMPL_CACHE["data"] = templates
    _META_TMPL_CACHE["ts"] = _time.time()
    return templates


@router.get("/whatsapp/templates")
async def whatsapp_templates_all(refresh: bool = False):
    """
    Unified template list from all configured sources (Wabis + Meta).
    Frontend polls this for the 30-min auto-sync.
    Query param: refresh=true to force cache clear
    Returns {wabis: [...], meta: [...], last_synced: <epoch>, meta_account_id: <id>, counts...}
    """
    # Clear cache if refresh requested
    if refresh:
        _WABIS_TMPL_CACHE["data"] = None
        _WABIS_TMPL_CACHE["ts"] = 0
        _META_TMPL_CACHE["data"] = None
        _META_TMPL_CACHE["ts"] = 0
    # Try wabis (uses existing cached endpoint logic)
    wabis_raw = await _get_wabis_templates_cached()

    import re

    def _parse_wabis_template_from_raw(t: dict) -> dict:
        raw_json = t.get("template_json") or "{}"
        try:
            tj = json.loads(raw_json) if isinstance(raw_json, str) else raw_json
        except Exception:
            tj = {}
        components = tj.get("components") or []
        raw_var_map = t.get("variable_map") or "{}"
        try:
            var_map = json.loads(raw_var_map) if isinstance(raw_var_map, str) else raw_var_map
        except Exception:
            var_map = {}
        header = footer = None
        body = {"text": t.get("body_content", ""), "vars": 0, "examples": [], "meta_text": ""}
        buttons: list = []
        raw_header_subtype = t.get("header_subtype", "").lower()  # 'none','text','image','video'
        for comp in components:
            ctype = comp.get("type", "").lower()
            text = comp.get("text", "")
            n_vars = len(set(int(m) for m in re.findall(r"\{\{(\d+)\}\}", text)))
            ex = comp.get("example", {})
            if ctype == "header":
                ex_vals = ex.get("header_text", [])
                fmt = comp.get("format", "TEXT").upper()
                header = {"text": text, "format": fmt, "vars": n_vars, "examples": ex_vals}
            elif ctype == "body":
                raw_body_ex = ex.get("body_text", [[]])
                ex_vals = raw_body_ex[0] if raw_body_ex else []
                body = {"text": text, "vars": n_vars, "examples": ex_vals, "meta_text": text}
            elif ctype == "footer":
                footer = {"text": text, "vars": n_vars}
            elif ctype == "buttons":
                for btn in comp.get("buttons", []):
                    var_cnt = len(re.findall(r"\{\{\d+\}\}", btn.get("text", "")))
                    buttons.append({"type": btn.get("type", ""), "text": btn.get("text", ""), "vars": var_cnt, "examples": btn.get("example", [])})
        var_labels: dict[str, str] = {}
        body_vars = var_map.get("body", {})
        if isinstance(body_vars, dict):
            for pos, raw_label in body_vars.items():
                clean = str(raw_label).strip("#").strip("!").replace("-", " ").replace("_", " ").title()
                var_labels[str(pos)] = clean
        total_vars = body.get("vars", 0) + (header or {}).get("vars", 0) + sum(b.get("vars", 0) for b in buttons)
        # Determine sendability (matches logic in /wabis/templates parser)
        locale = t.get("locale", "en_US")
        header_format = raw_header_subtype if raw_header_subtype != "none" else ("text" if header else "none")
        # Also detect from parsed header.format if header_subtype is missing
        if header_format in ("none", "") and header:
            header_format = header.get("format", "TEXT").lower()
        send_issue = None
        if header_format in ("image", "video") and not t.get("header_content", ""):
            send_issue = "image_header"
        body_text = body.get("text", "")
        if locale == "en_US" and any(0x0D00 < ord(c) < 0x0D80 for c in body_text):
            send_issue = send_issue or "locale_mismatch"
        return {
            "id": t["id"], "meta_template_id": t.get("template_id", ""),
            "name": t.get("template_name", ""), "category": t.get("template_category", ""),
            "status": t.get("status", ""), "locale": locale,
            "source": "wabis", "header": header, "header_format": header_format,
            "body": body, "footer": footer,
            "buttons": buttons, "var_labels": var_labels, "total_vars": total_vars,
            "send_issue": send_issue,
        }

    wabis = [_parse_wabis_template_from_raw(t) for t in wabis_raw if t.get("status") == "Approved"]

    # Try Meta (non-fatal if not configured)
    meta: list = []
    waba_id = os.getenv("META_WABA_ID", "")
    if waba_id:
        try:
            meta = await meta_wa_templates(force_refresh=refresh)
        except Exception as e:
            logger.warning(f"Meta templates error: {e}")

    return {
        "wabis": wabis,
        "meta": meta,
        "last_synced": _time.time(),
        "meta_configured": bool(waba_id),
        "meta_account_id": waba_id if waba_id else None,
        "wabis_count": len(wabis),
        "meta_count": len(meta),
    }


# ─── META WHATSAPP CLOUD API SEND ─────────────────────────────────────────────

class MetaWAPayload(BaseModel):
    phone: str
    template: str
    params: Optional[List[str]] = None
    phone_number_id: Optional[str] = None  # Override env default
    language_code: Optional[str] = "en_US"


@router.post("/meta-wa/send")
async def meta_wa_send(payload: MetaWAPayload):
    """
    Send a WhatsApp template message via Meta WhatsApp Cloud API.
    Requires: META_CAPI_ACCESS_TOKEN (with whatsapp_business_messaging permission)
              META_WA_PHONE_ID (phone number ID from Meta Business Manager)
    """
    from crm_models import Event

    access_token = os.getenv("META_CAPI_ACCESS_TOKEN", "")
    phone_number_id = payload.phone_number_id or os.getenv("META_WA_PHONE_ID", "")

    if not access_token:
        raise HTTPException(status_code=503, detail="META_CAPI_ACCESS_TOKEN not configured")
    if not phone_number_id:
        raise HTTPException(
            status_code=400,
            detail="Phone Number ID required. Provide phone_number_id in request body or set META_WA_PHONE_ID env var. Find it at: business.facebook.com → WhatsApp → Phone Numbers"
        )

    # Build template components from params
    components = []
    if payload.params:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": p} for p in payload.params],
        })

    meta_body = json.dumps({
        "messaging_product": "whatsapp",
        "to": payload.phone,
        "type": "template",
        "template": {
            "name": payload.template,
            "language": {"code": payload.language_code or "en_US"},
            "components": components,
        },
    }).encode()

    import urllib.request, urllib.error

    meta_url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"
    try:
        req = urllib.request.Request(
            meta_url,
            data=meta_body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="ignore")
        logger.warning("Meta WA send HTTP %s: %s", exc.code, err_body)
        raise HTTPException(status_code=502, detail=f"Meta WA error {exc.code}: {err_body}")
    except Exception as exc:
        logger.warning("Meta WA send error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))

    # Log outbound event
    db = SessionLocal()
    try:
        event = Event(
            customer_id=None,
            email=None,
            event_type="meta_wa_sent",
            source="meta_whatsapp",
            event_data={
                "phone": payload.phone,
                "template": payload.template,
                "params": payload.params,
                "phone_number_id": phone_number_id,
                "meta_response": result,
            },
            timestamp=datetime.now(timezone.utc),
        )
        db.add(event)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

    return {"status": "sent", "meta_response": result}


@router.post("/whatsapp/template/create")
async def create_whatsapp_template(payload: dict):
    """
    Save a custom WhatsApp template locally for future submission to Meta.
    This stores the template definition but doesn't submit it to Meta yet.
    User must submit via Meta WhatsApp Manager for approval.
    """
    try:
        # Validate required fields
        if not payload.get("name") or not payload.get("body"):
            raise HTTPException(status_code=400, detail="Template name and body are required")
        
        # Store template metadata in database for future reference
        db = SessionLocal()
        try:
            event = Event(
                customer_id=None,
                email=None,
                event_type="wa_template_created",
                source="crm_custom",
                event_data={
                    "name": payload.get("name"),
                    "category": payload.get("category", "MARKETING"),
                    "language": payload.get("language", "en_US"),
                    "header": payload.get("header", ""),
                    "body": payload.get("body"),
                    "footer": payload.get("footer", ""),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
                timestamp=datetime.now(timezone.utc),
            )
            db.add(event)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.warning(f"Failed to save template: {e}")
            raise HTTPException(status_code=500, detail="Failed to save template")
        finally:
            db.close()
        
        return {
            "status": "saved",
            "message": f'Template "{payload.get("name")}" saved locally. Submit to Meta WhatsApp Manager for approval.',
            "template": payload
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Template creation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── PHASE 4: CRO — A/B TEST TRACKING ────────────────────────────────────────

_VALID_AB_EVENTS = frozenset(["impression", "click", "add_to_cart", "checkout_start", "purchase"])

_ACTIVE_AB_TESTS = {
    "hero_message": {
        "variants": {
            "A": "Pure. From the Source.",
            "B": "Farm-to-Home Spices & Superfoods",
            "C": "Certified Organic. Family Trusted.",
        },
        "page": "/",
        "metric": "add_to_cart",
    },
    "product_cta": {
        "variants": {
            "A": "Add to Cart",
            "B": "Buy Now – Free Delivery",
            "C": "Add to Cart (₹499 Free Shipping)",
        },
        "page": "/products/*",
        "metric": "add_to_cart",
    },
    "checkout_trust": {
        "variants": {
            "A": "no_badges",
            "B": "badges_below_total",
            "C": "badges_inline_cta",
        },
        "page": "/checkout",
        "metric": "purchase",
    },
}


class ABTestEvent(BaseModel):
    test_id: str
    variant: str
    event: str                      # impression | click | add_to_cart | checkout_start | purchase
    session_id: Optional[str] = None
    email: Optional[str] = None
    value: Optional[float] = None
    page_url: Optional[str] = None
    timestamp: Optional[datetime] = None


@router.post("/cro/ab-event")
async def log_ab_event(payload: ABTestEvent):
    """
    Phase 4: Log an A/B test impression or conversion event.
    Used by the frontend to record which variant a user saw and whether they converted.
    """
    from crm_models import Event

    if payload.test_id not in _ACTIVE_AB_TESTS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown test_id '{payload.test_id}'. Active tests: {list(_ACTIVE_AB_TESTS)}"
        )
    if payload.event not in _VALID_AB_EVENTS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown event '{payload.event}'. Valid: {sorted(_VALID_AB_EVENTS)}"
        )

    test_cfg = _ACTIVE_AB_TESTS[payload.test_id]
    if payload.variant not in test_cfg["variants"]:
        raise HTTPException(
            status_code=422,
            detail=f"Variant '{payload.variant}' not in test '{payload.test_id}'"
        )

    db = SessionLocal()
    try:
        customer = get_or_create_customer(db, email=payload.email) if payload.email else None

        event = Event(
            customer_id=customer.id if customer else None,
            email=payload.email,
            event_type=f"ab_{payload.test_id}_{payload.event}",
            source="cro",
            session_id=payload.session_id,
            event_data={
                "test_id":     payload.test_id,
                "variant":     payload.variant,
                "event":       payload.event,
                "variant_text":test_cfg["variants"][payload.variant],
                "value":       payload.value,
                "page_url":    payload.page_url,
            },
            timestamp=payload.timestamp or datetime.now(timezone.utc),
        )
        db.add(event)
        db.commit()

        return {"status": "recorded", "test_id": payload.test_id, "variant": payload.variant}

    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        db.close()


@router.get("/cro/ab-results/{test_id}")
async def ab_results(test_id: str, days: int = 14):
    """
    Phase 4: Return A/B test conversion rates per variant.
    Calculates: impressions, conversions, CVR, revenue per variant.
    """
    if test_id not in _ACTIVE_AB_TESTS:
        raise HTTPException(status_code=404, detail=f"Unknown test_id '{test_id}'")

    test_cfg = _ACTIVE_AB_TESTS[test_id]
    metric = test_cfg["metric"]
    since = datetime.now(timezone.utc) - timedelta(days=days)

    db = SessionLocal()
    try:
        # Count impressions per variant
        imp_rows = db.execute(
            text("""
            SELECT event_data->>'variant' AS variant, COUNT(*) AS cnt
            FROM crm_events
            WHERE event_type = :imp_type
              AND created_at >= :since
            GROUP BY 1
            """),
            {"imp_type": f"ab_{test_id}_impression", "since": since},
        ).fetchall()

        # Count target conversions per variant
        cvr_rows = db.execute(
            text("""
            SELECT event_data->>'variant' AS variant, COUNT(*) AS cnt,
                   COALESCE(SUM((event_data->>'value')::float), 0) AS revenue
            FROM crm_events
            WHERE event_type = :cvr_type
              AND created_at >= :since
            GROUP BY 1
            """),
            {"cvr_type": f"ab_{test_id}_{metric}", "since": since},
        ).fetchall()

        impressions = {r[0]: r[1] for r in imp_rows}
        conversions = {r[0]: {"count": r[1], "revenue": r[2]} for r in cvr_rows}

        results = {}
        for variant in test_cfg["variants"]:
            imp = impressions.get(variant, 0)
            cvr = conversions.get(variant, {})
            conv_count = cvr.get("count", 0)
            results[variant] = {
                "variant_text":  test_cfg["variants"][variant],
                "impressions":   imp,
                "conversions":   conv_count,
                "cvr_pct":       round(conv_count / imp * 100, 2) if imp > 0 else 0,
                "revenue":       round(cvr.get("revenue", 0), 2),
            }

        return {
            "test_id":  test_id,
            "metric":   metric,
            "days":     days,
            "results":  results,
        }
    finally:
        db.close()


@router.get("/cro/tests")
async def list_ab_tests():
    """Return all active A/B tests and their variants."""
    return {"tests": _ACTIVE_AB_TESTS}


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 5: EMAIL MARKETING AUTOMATION
# ═══════════════════════════════════════════════════════════════════════════════

class EmailSendRequest(BaseModel):
    to_email: str
    template: str          # order_confirmation | order_fulfilled | order_cancelled |
                           # review_request_d3 | repeat_offer_d7 | replenishment_d30 |
                           # winback_d60 | cart_abandonment | _raw_html
    substitutions: Optional[Dict[str, Any]] = None
    order_id: Optional[str] = None   # used to flip lifecycle flag after send
    dedup_key: Optional[str] = None


@router.post("/email/send")
async def send_lifecycle_email(payload: EmailSendRequest):
    """
    Phase 5: Send a transactional or lifecycle email via the configured providers.
    Deduplicates by (to_email, template, dedup_key) using crm_messages table.
    On success, flips the matching lifecycle flag on crm_orders.
    """
    from sendgrid_handler import send_email

    db = SessionLocal()
    try:
        result = send_email(
            to_email=payload.to_email,
            template_name=payload.template,
            substitutions=payload.substitutions or {},
            dedup_key=payload.dedup_key or payload.order_id,
            db=db,
        )
        # Note: send_email is NOT async, no await needed

        # Flip lifecycle flag on order record
        if result.get("status") == "sent" and payload.order_id:
            from crm_models import Order
            _flag_map = {
                "order_confirmation":     None,               # no flag needed
                "order_confirmation_cod": None,               # no flag needed
                "out_for_delivery":       None,
                "welcome":                None,
                "review_request_d3":      "review_email_sent",
                "review_reminder_d7":     "review_email_sent",
                "repeat_offer_d7":        "repeat_email_sent",
                "replenishment_d30":      "replenishment_email_sent",
                "winback_d60":            "winback_email_sent",
                "cart_abandonment":       None,
            }
            flag = _flag_map.get(payload.template)
            if flag:
                order = db.query(Order).filter(Order.shopify_order_id == payload.order_id).first()
                if order:
                    setattr(order, flag, True)
                    db.commit()

        return result
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        db.close()


_EMAIL_QUEUE_WINDOWS = {
    "review_request_d3":    {"days": 3,   "flag": "review_email_sent"},
    "review_reminder_d7":   {"days": 7,   "flag": "review_email_sent"},
    "repeat_offer_d7":      {"days": 7,   "flag": "repeat_email_sent"},
    "replenishment_d30":    {"days": 30,  "flag": "replenishment_email_sent"},
    "winback_d60":          {"days": 60,  "flag": "winback_email_sent"},
}


@router.get("/email/queue/{sequence}")
async def email_queue(sequence: str, limit: int = 100):
    """
    Phase 5: N8N polls this to get orders ready for a given email sequence.
    Returns orders where the lifecycle flag is FALSE and order_date = today-Nd.
    N8N loops over results, calls /email/send for each, then calls /email/mark-sent.

    Sequences: review_request_d3 | repeat_offer_d7 | replenishment_d30 | winback_d60
    """
    from crm_models import Order, Customer

    if sequence not in _EMAIL_QUEUE_WINDOWS:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown sequence '{sequence}'. Valid: {list(_EMAIL_QUEUE_WINDOWS)}",
        )

    cfg  = _EMAIL_QUEUE_WINDOWS[sequence]
    days = cfg["days"]
    flag = cfg["flag"]

    db = SessionLocal()
    try:
        # Window: orders created within the target day (+/- 12 hours)
        window_center = datetime.now(timezone.utc) - timedelta(days=days)
        window_start  = window_center - timedelta(hours=12)
        window_end    = window_center + timedelta(hours=12)

        # For winback: order must have no newer order in the last 30 days
        if sequence == "winback_d60":
            recent_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
            rows = db.execute(text("""
                SELECT o.id, o.shopify_order_id, o.email, o.total_amount,
                       o.order_date, c.first_name, c.last_name, c.phone,
                       c.orders_count,
                       (SELECT STRING_AGG(item->>'name', ', ')
                        FROM jsonb_array_elements(o.items::jsonb) item) AS item_names
                FROM crm_orders o
                JOIN crm_customers c ON c.id = o.customer_id
                WHERE o.order_date BETWEEN :ws AND :we
                  AND o.winback_email_sent = FALSE
                  AND o.rto = FALSE
                  AND o.email IS NOT NULL
                  AND NOT EXISTS (
                        SELECT 1 FROM crm_orders o2
                        WHERE o2.customer_id = o.customer_id
                          AND o2.order_date > :recent
                          AND o2.id != o.id
                  )
                LIMIT :lim
            """), {"ws": window_start, "we": window_end,
                   "recent": recent_cutoff, "lim": limit}).fetchall()
        else:
            rows = db.execute(text(f"""
                SELECT o.id, o.shopify_order_id, o.email, o.total_amount,
                       o.order_date, c.first_name, c.last_name, c.phone,
                       c.orders_count,
                       (SELECT STRING_AGG(item->>'name', ', ')
                        FROM jsonb_array_elements(o.items::jsonb) item) AS item_names
                FROM crm_orders o
                JOIN crm_customers c ON c.id = o.customer_id
                WHERE o.order_date BETWEEN :ws AND :we
                  AND o.{flag} = FALSE
                  AND o.rto = FALSE
                  AND o.email IS NOT NULL
                LIMIT :lim
            """), {"ws": window_start, "we": window_end, "lim": limit}).fetchall()

        queue = [
            {
                "order_id":      r[1],
                "db_id":         r[0],
                "email":         r[2],
                "total_amount":  float(r[3] or 0),
                "order_date":    r[4].isoformat() if r[4] else None,
                "first_name":    r[5] or "there",
                "last_name":     r[6] or "",
                "phone":         r[7] or "",
                "orders_count":  r[8] or 1,
                "item_names":    r[9] or "your order",
            }
            for r in rows
        ]
        return {"sequence": sequence, "count": len(queue), "queue": queue}
    finally:
        db.close()


class MarkEmailSentRequest(BaseModel):
    order_id: str
    sequence: str


@router.post("/email/mark-sent")
async def mark_email_sent(payload: MarkEmailSentRequest):
    """
    Phase 5: Flip lifecycle email flag on an order record.
    Called by N8N after a successful /email/send call.
    """
    from crm_models import Order

    if payload.sequence not in _EMAIL_QUEUE_WINDOWS:
        raise HTTPException(status_code=422, detail=f"Unknown sequence '{payload.sequence}'")

    flag = _EMAIL_QUEUE_WINDOWS[payload.sequence]["flag"]

    db = SessionLocal()
    try:
        order = db.query(Order).filter(Order.shopify_order_id == payload.order_id).first()
        if not order:
            raise HTTPException(status_code=404, detail=f"Order {payload.order_id} not found")
        setattr(order, flag, True)
        db.commit()
        return {"status": "flagged", "order_id": payload.order_id, "flag": flag}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        db.close()


@router.get("/email/queue/cart")
async def cart_email_queue(window_hours: int = 2, limit: int = 50):
    """
    Phase 5: N8N polls this for cart abandoners who haven't received an email yet.
    Returns crm_events of type add_to_cart or cart_* where n8n_notified = FALSE,
    event is >= window_hours old, and customer has no purchase since.
    """
    from crm_models import Event, Order

    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)
        rows = db.execute(text("""
            SELECT e.id, e.email, e.event_data, e.created_at,
                   e.customer_id
            FROM crm_events e
            WHERE e.event_type IN ('add_to_cart', 'cart_add', 'CartAdd', 'view_cart')
              AND e.created_at <= :cutoff
              AND e.n8n_notified = FALSE
              AND e.email IS NOT NULL
              AND NOT EXISTS (
                    SELECT 1 FROM crm_orders o
                    WHERE o.email = e.email
                      AND o.order_date > e.created_at
              )
            ORDER BY e.created_at ASC
            LIMIT :lim
        """), {"cutoff": cutoff, "lim": limit}).fetchall()

        queue = [
            {
                "event_id":   r[0],
                "email":      r[1],
                "event_data": r[2],
                "created_at": r[3].isoformat() if r[3] else None,
                "customer_id": r[4],
            }
            for r in rows
        ]
        return {"count": len(queue), "queue": queue}
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 8: PROPENSITY SCORING
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/customers/{email}/propensity")
async def customer_propensity(email: str):
    """
    Phase 8: Return a propensity-to-convert score (0-100) for a customer.
    Higher score = higher purchase intent. Used by N8N to prioritise ad bids
    and by the budget allocation system for RLSA boost decisions.

    Scoring logic (additive):
    +40  email_capture micro-event recorded
    +30  phone_capture or phone_captured in CRM
    +25  pincode_validation micro-event recorded
    +20  multiple product views (≥ 3 view_item events)
    +20  high time-on-site (impulse_signal > 180s proxy from micro events)
    +15  add_to_cart event recorded
    +10  begin_checkout event recorded
    -20  customer has not visited in 30+ days
    -10  customer has RTO order
    """
    from crm_models import Customer, Event, Order

    db = SessionLocal()
    try:
        customer = db.query(Customer).filter(Customer.email == email).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        # Pull relevant events for this customer
        events = (
            db.query(Event.event_type, Event.created_at)
            .filter(Event.customer_id == customer.id)
            .order_by(Event.created_at.desc())
            .limit(100)
            .all()
        )
        event_types = [e[0] for e in events]
        last_seen   = events[0][1] if events else None

        score = 0
        reasons: list[str] = []

        # Email captured
        if "micro_email_capture" in event_types or customer.email:
            score += 40; reasons.append("+40 email_captured")

        # Phone captured
        if "micro_phone_capture" in event_types or customer.phone:
            score += 30; reasons.append("+30 phone_captured")

        # Pincode validated
        if "micro_pincode_validation" in event_types or "micro_delivery_check" in event_types:
            score += 25; reasons.append("+25 pincode_validated")

        # Multiple product views
        view_count = event_types.count("view_item") + event_types.count("product_view")
        if view_count >= 3:
            score += 20; reasons.append(f"+20 product_views={view_count}")

        # Impulse signals (long session proxy)
        if "micro_impulse_signal" in event_types:
            score += 20; reasons.append("+20 impulse_signal")

        # Add to cart
        if any(e in event_types for e in ("add_to_cart", "cart_add", "CartAdd")):
            score += 15; reasons.append("+15 add_to_cart")

        # Checkout started
        if any(e in event_types for e in ("begin_checkout", "checkout_start", "checkout_initiated")):
            score += 10; reasons.append("+10 begin_checkout")

        # Recency penalty
        if last_seen:
            # Ensure timezone-aware comparison
            last_seen_aware = last_seen.replace(tzinfo=timezone.utc) if last_seen.tzinfo is None else last_seen
            days_since = (datetime.now(timezone.utc) - last_seen_aware).days
            if days_since > 30:
                score -= 20; reasons.append(f"-20 inactive_{days_since}d")

        # RTO penalty
        rto_order = db.query(Order).filter(
            Order.customer_id == customer.id, Order.rto == True).first()
        if rto_order:
            score -= 10; reasons.append("-10 has_rto")

        score = max(0, min(100, score))

        # Tier classification
        tier = (
            "high"   if score >= 65 else
            "medium" if score >= 35 else
            "low"
        )

        return {
            "email":       email,
            "score":       score,
            "tier":        tier,
            "reasons":     reasons,
            "rlsa_bid_boost": {
                "high":   "+15%",
                "medium": "+7%",
                "low":    "0%",
            }[tier],
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 9: AI AD REVIEW SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

class AIReviewTriggerRequest(BaseModel):
    metrics: Dict[str, Any]           # yesterday's spend/ROAS by campaign
    review_type: str = "morning"      # "morning" | "evening"


@router.post("/ai-review/trigger")
async def ai_review_trigger(payload: AIReviewTriggerRequest, background_tasks: BackgroundTasks):
    """
    Phase 9: Trigger an AI-powered ad performance review.
    Creates a pending crm_ai_reviews record, calls Claude API asynchronously,
    then sends an approval email to the manager.
    """
    from crm_models import AIReview
    import uuid

    review_id = str(uuid.uuid4())
    db = SessionLocal()
    try:
        review = AIReview(
            id=review_id,
            review_type=payload.review_type,
            metrics_snapshot=payload.metrics,
            approval_status="pending",
            created_at=datetime.now(timezone.utc),
        )
        db.add(review)
        db.commit()
    except Exception as exc:
        db.rollback()
        db.close()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        db.close()

    # Analyse + notify in background so endpoint returns immediately
    def _analyse_and_notify(rid: str, metrics: dict):
        from claude_analyzer import analyze_ad_performance
        bg_db = SessionLocal()
        try:
            from crm_models import AIReview as _R
            analysis = analyze_ad_performance(metrics)

            review_rec = bg_db.query(_R).filter(_R.id == rid).first()
            if review_rec:
                review_rec.ai_output = analysis
                review_rec.approval_status = "awaiting_approval"
                bg_db.commit()

            # Send approval email
            _send_ai_review_email(rid, analysis, metrics)
        except Exception as exc:
            logger.error("AI review background task failed: %s", exc)
        finally:
            bg_db.close()

    background_tasks.add_task(_analyse_and_notify, review_id, payload.metrics)

    return {"status": "queued", "review_id": review_id}


def _send_ai_review_email(review_id: str, analysis: dict, metrics: dict):
    """Send the AI review approval email to the manager."""
    manager_email = os.getenv("MANAGER_EMAIL", "manager@pureleven.com")
    base_url      = os.getenv("SITE_URL", "https://ai.pureleven.com")

    approve_url = f"{base_url}/api/crm/ai-review/{review_id}/approve?action=approve"
    reject_url  = f"{base_url}/api/crm/ai-review/{review_id}/approve?action=reject"

    health = analysis.get("health", "unknown")
    roas   = analysis.get("overall_roas", 0)
    adjustments = analysis.get("adjustments", [])

    adj_rows = "".join(
        f"<tr><td>{a.get('campaign')}</td>"
        f"<td>{a.get('action')}</td>"
        f"<td>{a.get('percent', 0)}%</td>"
        f"<td>{a.get('rationale', '')}</td></tr>"
        for a in adjustments
    )

    html = f"""
    <div style="font-family:sans-serif;max-width:700px;margin:0 auto">
      <h2>🤖 Pureleven AI Ad Review — {datetime.now().strftime('%Y-%m-%d %I:%M %p')}</h2>
      <p><strong>Health:</strong> {health.upper()} &nbsp;|&nbsp;
         <strong>Overall ROAS:</strong> {roas}x</p>
      <p><strong>Summary:</strong> {analysis.get('summary','')}</p>
      <h3>Recommended Adjustments</h3>
      <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%">
        <tr style="background:#f0f0f0">
          <th>Campaign</th><th>Action</th><th>Change</th><th>Reason</th>
        </tr>
        {adj_rows or '<tr><td colspan="4">No adjustments recommended</td></tr>'}
      </table>
      <br>
      <a href="{approve_url}" style="background:#2E7D32;color:#fff;padding:12px 28px;text-decoration:none;border-radius:4px;margin-right:16px;font-size:16px">
        ✅ APPROVE &amp; EXECUTE
      </a>
      <a href="{reject_url}" style="background:#c62828;color:#fff;padding:12px 28px;text-decoration:none;border-radius:4px;font-size:16px">
        ❌ REJECT
      </a>
      <p style="color:#888;font-size:12px;margin-top:24px">Review ID: {review_id}</p>
    </div>
    """
    try:
        from sendgrid_handler import send_email
        send_email(
            to_email=manager_email,
            template_name="_raw_html",
            substitutions={"__html__": html, "subject": f"AI Ad Review — {health.upper()} ROAS {roas}x"},
            dedup_key=review_id,
        )
    except Exception as exc:
        logger.warning("AI review email send failed: %s", exc)

    # Also log via internal email API (no-SendGrid fallback)
    logger.info("AI review email queued for %s review_id=%s", manager_email, review_id)


@router.get("/ai-review/pending")
async def ai_review_pending():
    """
    Phase 9: Return all AI reviews in 'awaiting_approval' state.
    N8N polls this to check if any reviews are waiting for the manager.
    """
    from crm_models import AIReview
    db = SessionLocal()
    try:
        rows = (
            db.query(AIReview)
            .filter(AIReview.approval_status == "awaiting_approval")
            .order_by(AIReview.created_at.desc())
            .limit(20)
            .all()
        )
        return {
            "count": len(rows),
            "reviews": [
                {
                    "id":            r.id,
                    "review_type":   r.review_type,
                    "created_at":    r.created_at.isoformat() if r.created_at else None,
                    "health":        (r.ai_output or {}).get("health", "unknown"),
                    "overall_roas":  (r.ai_output or {}).get("overall_roas", 0),
                    "adjustments":   (r.ai_output or {}).get("adjustments", []),
                }
                for r in rows
            ],
        }
    finally:
        db.close()


@router.post("/ai-review/{review_id}/approve")
async def ai_review_approve(
    review_id: str,
    action: str = "approve",   # "approve" | "reject"
    background_tasks: BackgroundTasks = None,
):
    """
    Phase 9: Manager approves or rejects an AI review.
    On approval: executes recommended budget adjustments (logged, no live API calls
    without Google Ads / Meta API credentials configured).
    Also accessible via GET (email click-through links use query param).
    """
    from crm_models import AIReview

    if action not in ("approve", "reject"):
        raise HTTPException(status_code=422, detail="action must be 'approve' or 'reject'")

    db = SessionLocal()
    try:
        review = db.query(AIReview).filter(AIReview.id == review_id).first()
        if not review:
            raise HTTPException(status_code=404, detail="Review not found")
        if review.approval_status not in ("awaiting_approval", "pending"):
            return {"status": "already_processed", "approval_status": review.approval_status}

        review.approval_status = "approved" if action == "approve" else "rejected"
        review.approved_at = datetime.now(timezone.utc)
        db.commit()

        if action == "approve" and background_tasks:
            adj = (review.ai_output or {}).get("adjustments", [])
            background_tasks.add_task(_execute_approved_adjustments, review_id, adj)

        return {
            "status":  action + "d",
            "review_id": review_id,
            "adjustments_queued": len((review.ai_output or {}).get("adjustments", [])) if action == "approve" else 0,
        }
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        db.close()


# Allow GET for email click-through
@router.get("/ai-review/{review_id}/approve")
async def ai_review_approve_get(review_id: str, action: str = "approve",
                                background_tasks: BackgroundTasks = None):
    return await ai_review_approve(review_id, action, background_tasks)


def _execute_approved_adjustments(review_id: str, adjustments: list):
    """
    Execute approved budget/bid adjustments.
    Currently logs recommendations; wire to Google Ads / Meta Graph API when credentials added.
    """
    from crm_models import AutomationLog
    import uuid

    bg_db = SessionLocal()
    try:
        for adj in adjustments:
            log = AutomationLog(
                id=str(uuid.uuid4()),
                workflow_name="ai_review_execution",
                trigger="manager_approved",
                status="logged",
                details={
                    "review_id":  review_id,
                    "campaign":   adj.get("campaign"),
                    "platform":   adj.get("platform"),
                    "action":     adj.get("action"),
                    "percent":    adj.get("percent"),
                    "rationale":  adj.get("rationale"),
                    "executed_at": datetime.now(timezone.utc).isoformat(),
                    "note": "Manual execution required until Google Ads / Meta API credentials configured.",
                },
                ran_at=datetime.now(timezone.utc),
            )
            bg_db.add(log)
        bg_db.commit()
        logger.info("AI review %s: %d adjustments logged for execution", review_id, len(adjustments))
    except Exception as exc:
        logger.error("_execute_approved_adjustments error: %s", exc)
        bg_db.rollback()
    finally:
        bg_db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE 10: ATTRIBUTION & ROAS ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/admin/retry-conversions")
async def retry_failed_conversions(background_tasks: BackgroundTasks, admin_secret: str = ""):
    """
    Retry CAPI/Google Ads sends for orders in 'failed' or 'pending' state.
    Max 3 attempts per order. Call via cron or manually.
    """
    if admin_secret != "basil":
        raise HTTPException(status_code=403, detail="Forbidden")

    from crm_models import Order
    db = SessionLocal()
    try:
        retry_orders = db.execute(text("""
             SELECT o.shopify_order_id, o.email, o.total_amount, o.currency,
                 o.gclid, o.fbclid, o.payment_method, o.capi_attempts,
                 o.capi_status, o.created_at, o.items, o.shipping_address,
                 c.phone AS customer_phone
             FROM crm_orders o
             LEFT JOIN crm_customers c ON c.id = o.customer_id
            WHERE (
                   capi_status IN ('failed', 'pending')
                OR meta_status = 'failed'
                OR google_status = 'failed'
              )
              AND capi_attempts < 3
              AND capi_suppressed = false
              AND (total_amount IS NULL OR total_amount >= 50)
            ORDER BY created_at DESC
            LIMIT 50
        """)).fetchall()

        queued = 0
        for row in retry_orders:
            (
                shopify_order_id,
                email,
                total_amount,
                currency,
                gclid,
                fbclid,
                payment_method,
                capi_attempts,
                capi_status,
                created_at,
                items,
                shipping_address,
                customer_phone,
            ) = row
            shipping_address = shipping_address or {}
            order_data = {
                "id": shopify_order_id,
                "email": email,
                "total_price": total_amount,
                "total_amount": total_amount,
                "currency": currency or "INR",
                "items": items or [],
                "shipping_address": shipping_address,
                "billing_address": {
                    "phone": shipping_address.get("phone") or customer_phone,
                },
                "customer": {
                    "phone": customer_phone,
                },
                "_gclid": gclid,
                "_fbclid": fbclid,
                "created_at": created_at.isoformat() if created_at else None,
            }
            background_tasks.add_task(fire_meta_capi, order_data, "", "")
            background_tasks.add_task(fire_google_conversion, order_data)
            queued += 1

        return {
            "status": "queued",
            "orders_queued": queued,
            "note": "CAPI/Google sends queued as background tasks. Check capi_status after 30s."
        }
    finally:
        db.close()


@router.get("/admin/google-ads/health")
async def google_ads_health(admin_secret: str = ""):
    """Non-destructive Google Ads health check for auth and conversion action access."""
    if admin_secret != "basil":
        raise HTTPException(status_code=403, detail="Forbidden")

    gads = _gads()
    if gads is None:
        return {"status": "module_unavailable"}

    try:
        return gads.health_check()
    except Exception as exc:
        logger.warning("google_ads_health error: %s", exc)
        return {"status": "error", "error": str(exc)}


@router.get("/admin/conversions/status")
async def conversions_status(admin_secret: str = "", hours: int = 24):
    """
    Per-destination conversion delivery stats.
    Shows sent/failed/pending counts for meta, google, ga4 over the last N hours.
    """
    if admin_secret != "basil":
        raise HTTPException(status_code=403, detail="Forbidden")

    db = SessionLocal()
    try:
        since = datetime.now(timezone.utc) - timedelta(hours=min(hours, 720))

        # Per-destination counts from crm_orders destination columns
        rows = db.execute(text("""
            SELECT
              COUNT(*)                                                             AS total_orders,
              COUNT(*) FILTER (WHERE meta_status = 'sent')                        AS meta_sent,
              COUNT(*) FILTER (WHERE meta_status = 'failed')                      AS meta_failed,
              COUNT(*) FILTER (WHERE meta_status IS NULL
                AND capi_suppressed = false)                                      AS meta_pending,
              COUNT(*) FILTER (WHERE google_status = 'sent')                      AS google_sent,
              COUNT(*) FILTER (WHERE google_status = 'failed')                    AS google_failed,
              COUNT(*) FILTER (WHERE google_status IS NULL
                AND capi_suppressed = false)                                      AS google_pending,
              COUNT(*) FILTER (WHERE capi_suppressed = true)                      AS suppressed,
              COUNT(*) FILTER (WHERE capi_status = 'failed'
                AND capi_attempts < 3)                                            AS needs_retry
            FROM crm_orders
            WHERE created_at >= :since
        """), {"since": since}).fetchone()

        # TrackingEvent log summary (if table exists)
        try:
            te_rows = db.execute(text("""
                SELECT destination, status, COUNT(*) AS cnt
                FROM tracking_events
                WHERE created_at >= :since
                GROUP BY destination, status
                ORDER BY destination, status
            """), {"since": since}).fetchall()
            tracking_events = {}
            for dest, st, cnt in te_rows:
                tracking_events.setdefault(dest, {})[st] = cnt
        except Exception:
            tracking_events = {}

        return {
            "period_hours":   hours,
            "since":          since.isoformat(),
            "orders": {
                "total":      rows[0],
                "suppressed": rows[7],
                "needs_retry": rows[8],
            },
            "meta":   {"sent": rows[1], "failed": rows[2], "pending": rows[3]},
            "google": {"sent": rows[4], "failed": rows[5], "pending": rows[6]},
            "tracking_events": tracking_events,
        }
    finally:
        db.close()


@router.get("/analytics/attribution-health")
async def attribution_health(admin_secret: str = ""):
    """
    Attribution health dashboard: shows data capture rates, CAPI status, and coverage.
    """
    if admin_secret != "basil":
        raise HTTPException(status_code=403, detail="Forbidden")

    db = SessionLocal()
    try:
        since_7d = datetime.now(timezone.utc) - timedelta(days=7)
        since_30d = datetime.now(timezone.utc) - timedelta(days=30)

        result = db.execute(text("""
            SELECT
              COUNT(*) FILTER (WHERE created_at >= :since_7d)   AS orders_7d,
              COUNT(*) FILTER (WHERE created_at >= :since_30d)  AS orders_30d,
              COUNT(*) FILTER (WHERE gclid IS NOT NULL AND created_at >= :since_30d) AS gclid_30d,
              COUNT(*) FILTER (WHERE fbclid IS NOT NULL AND created_at >= :since_30d) AS fbclid_30d,
              COUNT(*) FILTER (WHERE utm_source IS NOT NULL AND created_at >= :since_30d) AS utm_30d,
              COUNT(*) FILTER (WHERE capi_status = 'sent' AND created_at >= :since_30d) AS capi_sent_30d,
              COUNT(*) FILTER (WHERE capi_status = 'failed' AND created_at >= :since_30d) AS capi_failed_30d,
              COUNT(*) FILTER (WHERE capi_status = 'pending' AND capi_suppressed = false AND created_at >= :since_30d) AS capi_pending_30d,
              COUNT(*) FILTER (WHERE capi_suppressed = true AND created_at >= :since_30d) AS capi_skipped_30d,
              SUM(total_amount) FILTER (WHERE gclid IS NOT NULL AND created_at >= :since_30d) AS gclid_revenue_30d,
              SUM(total_amount) FILTER (WHERE fbclid IS NOT NULL AND created_at >= :since_30d) AS fbclid_revenue_30d,
              SUM(total_amount) FILTER (WHERE created_at >= :since_30d) AS total_revenue_30d
            FROM crm_orders
        """), {"since_7d": since_7d, "since_30d": since_30d}).fetchone()

        events_7d = db.execute(text("""
            SELECT COUNT(*) FROM crm_events
            WHERE event_type = 'page_view' AND created_at >= :since_7d
        """), {"since_7d": since_7d}).scalar() or 0

        identity_count = db.execute(text(
            "SELECT COUNT(*) FROM unified_identity WHERE last_seen >= :since_30d"
        ), {"since_30d": since_30d}).scalar() or 0

        o7, o30, gc30, fb30, utm30, sent30, failed30, pend30, skip30, gc_rev, fb_rev, total_rev = result

        return {
            "status": "ok",
            "last_7_days": {
                "orders": o7,
                "page_view_events": events_7d,
            },
            "last_30_days": {
                "orders_total": o30,
                "orders_with_gclid": gc30,
                "orders_with_fbclid": fb30,
                "orders_with_utm": utm30,
                "attribution_coverage_pct": round((gc30 + fb30) / max(o30, 1) * 100, 1),
                "revenue_total_inr": round(float(total_rev or 0), 2),
                "revenue_attributed_gclid_inr": round(float(gc_rev or 0), 2),
                "revenue_attributed_fbclid_inr": round(float(fb_rev or 0), 2),
            },
            "capi_status_30d": {
                "sent": sent30,
                "failed": failed30,
                "pending": pend30,
                "skipped_fraud": skip30,
            },
            "identity_resolution": {
                "active_identities_30d": identity_count,
            },
        }
    finally:
        db.close()


@router.get("/analytics/attribution")
async def attribution_report(days: int = 30):
    """
    Phase 10: Multi-touch attribution report.
    Shows orders and revenue attributed to each UTM source/medium over the last N days.
    Uses crm_orders + crm_conversion_feeds.
    """
    from crm_models import ConversionFeed, Order

    db = SessionLocal()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)

        # Attribution from conversion feeds (Google Ads, Meta)
        feed_rows = db.execute(text("""
            SELECT source,
                   COUNT(*)                          AS conversions,
                   COALESCE(SUM(conversion_value),0) AS revenue
            FROM crm_conversion_feeds
            WHERE timestamp >= :since
            GROUP BY source
            ORDER BY revenue DESC
        """), {"since": since}).fetchall()

        # Attribution from orders with gclid / fbclid
        gclid_row = db.execute(text("""
            SELECT COUNT(*), COALESCE(SUM(total_amount),0)
            FROM crm_orders
            WHERE order_date >= :since
              AND gclid IS NOT NULL AND gclid != ''
              AND rto = FALSE
        """), {"since": since}).fetchone()

        fbclid_row = db.execute(text("""
            SELECT COUNT(*), COALESCE(SUM(total_amount),0)
            FROM crm_orders
            WHERE order_date >= :since
              AND fbclid IS NOT NULL AND fbclid != ''
              AND rto = FALSE
        """), {"since": since}).fetchone()

        organic_row = db.execute(text("""
            SELECT COUNT(*), COALESCE(SUM(total_amount),0)
            FROM crm_orders
            WHERE order_date >= :since
              AND (gclid IS NULL OR gclid = '')
              AND (fbclid IS NULL OR fbclid = '')
              AND rto = FALSE
        """), {"since": since}).fetchone()

        channels = [
            {
                "channel":     "google_ads",
                "conversions": int(gclid_row[0] or 0),
                "revenue_inr": round(float(gclid_row[1] or 0), 2),
                "note":        "Orders with gclid attribution",
            },
            {
                "channel":     "meta_ads",
                "conversions": int(fbclid_row[0] or 0),
                "revenue_inr": round(float(fbclid_row[1] or 0), 2),
                "note":        "Orders with fbclid attribution",
            },
            {
                "channel":     "organic_direct",
                "conversions": int(organic_row[0] or 0),
                "revenue_inr": round(float(organic_row[1] or 0), 2),
                "note":        "Orders with no paid attribution",
            },
        ]

        for r in feed_rows:
            channels.append({
                "channel":     r[0],
                "conversions": int(r[1]),
                "revenue_inr": round(float(r[2]), 2),
                "note":        "From conversion feeds",
            })

        total_revenue = sum(c["revenue_inr"] for c in channels
                            if c["channel"] in ("google_ads", "meta_ads", "organic_direct"))

        return {
            "days":          days,
            "since":         since.date().isoformat(),
            "channels":      channels,
            "total_revenue": round(total_revenue, 2),
        }
    finally:
        db.close()


@router.get("/analytics/roas")
async def roas_by_channel(days: int = 7):
    """
    Phase 10: ROAS summary per channel over the last N days.
    Budget spend is from CAMPAIGN_BUDGET_PLAN (planned daily budgets × days).
    Revenue is from crm_orders with attribution.
    N8N uses this to decide budget reallocations.
    """
    db = SessionLocal()
    try:
        since = datetime.now(timezone.utc) - timedelta(days=days)

        gclid_rev = db.execute(text("""
            SELECT COALESCE(SUM(total_amount),0)
            FROM crm_orders
            WHERE order_date >= :since AND gclid IS NOT NULL AND gclid != '' AND rto = FALSE
        """), {"since": since}).scalar() or 0

        fbclid_rev = db.execute(text("""
            SELECT COALESCE(SUM(total_amount),0)
            FROM crm_orders
            WHERE order_date >= :since AND fbclid IS NOT NULL AND fbclid != '' AND rto = FALSE
        """), {"since": since}).scalar() or 0

        # Planned spend from budget plan
        google_daily = sum(c["daily_budget_inr"] for c in CAMPAIGN_BUDGET_PLAN["google"])
        meta_daily   = sum(c["daily_budget_inr"] for c in CAMPAIGN_BUDGET_PLAN["meta"])
        google_spend = google_daily * days
        meta_spend   = meta_daily   * days

        def _roas(revenue, spend):
            return round(float(revenue) / spend, 2) if spend > 0 else 0

        return {
            "days":  days,
            "since": since.date().isoformat(),
            "channels": [
                {
                    "channel":       "google_ads",
                    "planned_spend": google_spend,
                    "attributed_revenue": round(float(gclid_rev), 2),
                    "roas":          _roas(gclid_rev, google_spend),
                    "daily_budget":  google_daily,
                },
                {
                    "channel":       "meta_ads",
                    "planned_spend": meta_spend,
                    "attributed_revenue": round(float(fbclid_rev), 2),
                    "roas":          _roas(fbclid_rev, meta_spend),
                    "daily_budget":  meta_daily,
                },
            ],
            "note": "Spend is planned budget × days. For actual spend use Google Ads / Meta dashboards.",
        }
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# JOURNEY ORCHESTRATION — SCHEMAS, ENGINE, ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

# ─── Pydantic Schemas ──────────────────────────────────────────────────────────

class JourneyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    segment_id: Optional[str] = None
    entry_trigger: Optional[str] = None     # cart_abandon | order_complete | customer_create
    exit_criteria: Optional[Dict[str, Any]] = None
    max_frequency_per_day: int = 2
    n8n_workflow_id: Optional[str] = None
    template_json: Optional[List[Dict[str, Any]]] = None  # Array of step defs


class JourneyUpdate(BaseModel):
    description: Optional[str] = None
    status: Optional[str] = None            # DRAFT | ACTIVE | PAUSED
    entry_trigger: Optional[str] = None
    exit_criteria: Optional[Dict[str, Any]] = None
    max_frequency_per_day: Optional[int] = None
    n8n_workflow_id: Optional[str] = None
    template_json: Optional[List[Dict[str, Any]]] = None


class JourneyInstanceUpdate(BaseModel):
    status: Optional[str] = None            # PAUSED | COMPLETED | EXITED
    exit_reason: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    current_step: Optional[int] = None


class JourneyStepLog(BaseModel):
    status: str                             # EXECUTED | SKIPPED | FAILED
    result: Optional[Dict[str, Any]] = None
    executed_at: Optional[datetime] = None


class JourneyEnroll(BaseModel):
    customer_id: str
    journey_id: str


# ─── Segment Assignment Engine ────────────────────────────────────────────────

def _trigger_n8n_workflow(n8n_workflow_id: str, payload: Dict[str, Any]) -> bool:
    """
    Fire-and-forget POST to N8N webhook to start a journey workflow.
    Returns True on success (2xx), False otherwise.
    """
    import httpx
    n8n_base = os.getenv("N8N_BASE_URL", "https://automation.pureleven.com")
    url = f"{n8n_base}/webhook/{n8n_workflow_id}"
    try:
        r = httpx.post(url, json=payload, timeout=5)
        if r.status_code < 300:
            logger.info("N8N triggered: workflow=%s customer=%s", n8n_workflow_id, payload.get("customer_id"))
            return True
        logger.warning("N8N webhook non-2xx: %s %s", r.status_code, r.text[:200])
    except Exception as exc:
        logger.warning("N8N trigger failed: %s", exc)
    return False


def assign_customer_to_journeys(customer_id: str, trigger: str, db: Session) -> List[str]:
    """
    Evaluate all ACTIVE journeys whose entry_trigger matches.
    Enroll customer in matching journeys (skip if already ACTIVE in same journey).
    Fire N8N webhook for each new enrollment.
    Returns list of newly enrolled journey IDs.
    """
    from crm_models import Journey, JourneyInstance, Customer

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        return []

    journeys = db.query(Journey).filter(
        Journey.status == "ACTIVE",
        Journey.entry_trigger == trigger,
    ).all()

    enrolled = []
    for journey in journeys:
        # Skip if already active in this journey
        existing = db.query(JourneyInstance).filter(
            JourneyInstance.journey_id == journey.id,
            JourneyInstance.customer_id == customer_id,
            JourneyInstance.status == "ACTIVE",
        ).first()
        if existing:
            continue

        # Create new instance
        instance = JourneyInstance(
            id=str(__import__("uuid").uuid4()),
            journey_id=journey.id,
            customer_id=customer_id,
            email=customer.email,
            status="ACTIVE",
            current_step=0,
        )
        db.add(instance)
        db.flush()  # Get instance.id before commit

        # Trigger N8N if workflow ID configured
        if journey.n8n_workflow_id:
            _trigger_n8n_workflow(journey.n8n_workflow_id, {
                "journey_id":       journey.id,
                "journey_name":     journey.name,
                "instance_id":      instance.id,
                "customer_id":      customer_id,
                "customer_email":   customer.email,
                "customer_phone":   customer.phone,
                "trigger":          trigger,
                "template":         journey.template_json or [],
            })

        enrolled.append(journey.id)
        logger.info("Enrolled customer=%s in journey=%s", customer_id, journey.name)

    db.commit()
    return enrolled


def _exit_customer_from_journey(journey_id: str, customer_id: str, reason: str, db: Session):
    """Mark a customer's journey instance as EXITED (e.g. after purchase)."""
    from crm_models import JourneyInstance

    instance = db.query(JourneyInstance).filter(
        JourneyInstance.journey_id == journey_id,
        JourneyInstance.customer_id == customer_id,
        JourneyInstance.status == "ACTIVE",
    ).first()
    if instance:
        instance.status = "EXITED"
        instance.exit_reason = reason
        instance.completed_at = datetime.utcnow()
        db.commit()


# ─── Journey CRUD Endpoints ───────────────────────────────────────────────────

@router.post("/journeys", status_code=201)
def create_journey(body: JourneyCreate):
    """Create a new journey template."""
    from crm_models import Journey
    db = SessionLocal()
    try:
        journey = Journey(
            id=str(__import__("uuid").uuid4()),
            name=body.name,
            description=body.description,
            segment_id=body.segment_id,
            status="DRAFT",
            entry_trigger=body.entry_trigger,
            exit_criteria=body.exit_criteria,
            max_frequency_per_day=body.max_frequency_per_day,
            n8n_workflow_id=body.n8n_workflow_id,
            template_json=body.template_json,
        )
        db.add(journey)
        db.commit()
        db.refresh(journey)
        return {
            "id": journey.id, "name": journey.name,
            "status": journey.status, "entry_trigger": journey.entry_trigger,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.get("/journeys")
def list_journeys(status: Optional[str] = None):
    """List all journey templates. Filter by status if provided."""
    from crm_models import Journey
    db = SessionLocal()
    try:
        q = db.query(Journey)
        if status:
            q = q.filter(Journey.status == status.upper())
        journeys = q.order_by(Journey.created_at.desc()).all()
        return [{
            "id": j.id, "name": j.name, "description": j.description,
            "status": j.status, "entry_trigger": j.entry_trigger,
            "n8n_workflow_id": j.n8n_workflow_id,
            "step_count": len(j.template_json or []),
            "created_at": j.created_at.isoformat(),
        } for j in journeys]
    finally:
        db.close()


@router.get("/journeys/analytics")
def journey_analytics():
    """Aggregate analytics across all journeys: active count, conversion rate, channel breakdown."""
    from crm_models import Journey, JourneyInstance, JourneyStep, MessageLog
    db = SessionLocal()
    try:
        journeys = db.query(Journey).filter(Journey.status == "ACTIVE").all()
        result = []
        total_active = 0
        total_completed = 0

        message_join_column = getattr(MessageLog, "journey_instance_id", None)

        for j in journeys:
            active = db.query(JourneyInstance).filter(
                JourneyInstance.journey_id == j.id,
                JourneyInstance.status == "ACTIVE",
            ).count()
            completed = db.query(JourneyInstance).filter(
                JourneyInstance.journey_id == j.id,
                JourneyInstance.status == "COMPLETED",
            ).count()
            exited = db.query(JourneyInstance).filter(
                JourneyInstance.journey_id == j.id,
                JourneyInstance.status == "EXITED",
            ).count()
            total_entered = active + completed + exited
            conv_rate = round(completed / total_entered, 3) if total_entered else 0

            # Message breakdown for this journey
            if message_join_column is not None:
                email_sent = db.query(MessageLog).join(
                    JourneyInstance, message_join_column == JourneyInstance.id
                ).filter(
                    JourneyInstance.journey_id == j.id,
                    MessageLog.channel == "email",
                ).count()
                wa_sent = db.query(MessageLog).join(
                    JourneyInstance, message_join_column == JourneyInstance.id
                ).filter(
                    JourneyInstance.journey_id == j.id,
                    MessageLog.channel == "whatsapp",
                ).count()
            else:
                email_sent = db.query(MessageLog).join(
                    JourneyInstance, MessageLog.customer_id == JourneyInstance.customer_id
                ).filter(
                    JourneyInstance.journey_id == j.id,
                    MessageLog.channel == "email",
                ).count()
                wa_sent = db.query(MessageLog).join(
                    JourneyInstance, MessageLog.customer_id == JourneyInstance.customer_id
                ).filter(
                    JourneyInstance.journey_id == j.id,
                    MessageLog.channel == "whatsapp",
                ).count()

            total_active += active
            total_completed += completed
            result.append({
                "journey_id":      j.id,
                "journey_name":    j.name,
                "active":          active,
                "completed":       completed,
                "exited":          exited,
                "conversion_rate": conv_rate,
                "email_sent":      email_sent,
                "whatsapp_sent":   wa_sent,
            })

        return {
            "total_active_instances": total_active,
            "total_completed": total_completed,
            "journeys": result,
        }
    finally:
        db.close()


@router.get("/journeys/{journey_id}")
def get_journey(journey_id: str):
    """Get full journey template including step definitions."""
    from crm_models import Journey
    db = SessionLocal()
    try:
        j = db.query(Journey).filter(Journey.id == journey_id).first()
        if not j:
            raise HTTPException(status_code=404, detail="Journey not found")
        return {
            "id": j.id, "name": j.name, "description": j.description,
            "status": j.status, "entry_trigger": j.entry_trigger,
            "exit_criteria": j.exit_criteria,
            "max_frequency_per_day": j.max_frequency_per_day,
            "n8n_workflow_id": j.n8n_workflow_id,
            "template_json": j.template_json,
            "created_at": j.created_at.isoformat(),
            "updated_at": j.updated_at.isoformat(),
        }
    finally:
        db.close()


@router.patch("/journeys/{journey_id}")
def update_journey(journey_id: str, body: JourneyUpdate):
    """Update journey status, template, or N8N workflow ID."""
    from crm_models import Journey
    db = SessionLocal()
    try:
        j = db.query(Journey).filter(Journey.id == journey_id).first()
        if not j:
            raise HTTPException(status_code=404, detail="Journey not found")
        for field, val in body.model_dump(exclude_none=True).items():
            setattr(j, field, val)
        j.updated_at = datetime.utcnow()
        db.commit()
        return {"id": j.id, "name": j.name, "status": j.status}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.delete("/journeys/{journey_id}", status_code=204)
def delete_journey(journey_id: str):
    """Delete a journey (only DRAFT journeys can be deleted)."""
    from crm_models import Journey
    db = SessionLocal()
    try:
        j = db.query(Journey).filter(Journey.id == journey_id).first()
        if not j:
            raise HTTPException(status_code=404, detail="Journey not found")
        if j.status != "DRAFT":
            raise HTTPException(status_code=400, detail="Only DRAFT journeys can be deleted")
        db.delete(j)
        db.commit()
    finally:
        db.close()


# ─── Journey Instance Endpoints ────────────────────────────────────────────────

@router.post("/journey-instances", status_code=201)
def enroll_customer(body: JourneyEnroll):
    """Manually enroll a customer in a journey (bypasses trigger check)."""
    from crm_models import Customer, Journey, JourneyInstance
    db = SessionLocal()
    try:
        customer = db.query(Customer).filter(Customer.id == body.customer_id).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        journey = db.query(Journey).filter(Journey.id == body.journey_id).first()
        if not journey:
            raise HTTPException(status_code=404, detail="Journey not found")

        # Check if already active
        existing = db.query(JourneyInstance).filter(
            JourneyInstance.journey_id == body.journey_id,
            JourneyInstance.customer_id == body.customer_id,
            JourneyInstance.status == "ACTIVE",
        ).first()
        if existing:
            return {"instance_id": existing.id, "status": "already_active"}

        instance = JourneyInstance(
            id=str(__import__("uuid").uuid4()),
            journey_id=body.journey_id,
            customer_id=body.customer_id,
            email=customer.email,
            status="ACTIVE",
            current_step=0,
        )
        db.add(instance)
        db.commit()
        db.refresh(instance)

        if journey.n8n_workflow_id:
            _trigger_n8n_workflow(journey.n8n_workflow_id, {
                "journey_id":     journey.id,
                "journey_name":   journey.name,
                "instance_id":    instance.id,
                "customer_id":    body.customer_id,
                "customer_email": customer.email,
                "trigger":        "manual",
                "template":       journey.template_json or [],
            })

        return {"instance_id": instance.id, "journey_name": journey.name, "status": "enrolled"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.get("/journey-instances/{instance_id}")
def get_journey_instance(instance_id: str):
    """Get a single journey instance with its step execution history."""
    from crm_models import JourneyInstance, JourneyStep, Journey
    db = SessionLocal()
    try:
        inst = db.query(JourneyInstance).filter(JourneyInstance.id == instance_id).first()
        if not inst:
            raise HTTPException(status_code=404, detail="Journey instance not found")
        steps = db.query(JourneyStep).filter(
            JourneyStep.journey_instance_id == instance_id
        ).order_by(JourneyStep.step_index).all()
        journey = db.query(Journey).filter(Journey.id == inst.journey_id).first()
        return {
            "instance_id":   inst.id,
            "journey_name":  journey.name if journey else inst.journey_id,
            "customer_id":   inst.customer_id,
            "email":         inst.email,
            "status":        inst.status,
            "current_step":  inst.current_step,
            "started_at":    inst.started_at.isoformat(),
            "completed_at":  inst.completed_at.isoformat() if inst.completed_at else None,
            "exit_reason":   inst.exit_reason,
            "result_data":   inst.result_data,
            "steps": [{
                "step_index": s.step_index,
                "step_type":  s.step_type,
                "step_name":  s.step_name,
                "status":     s.status,
                "scheduled_at": s.scheduled_at.isoformat() if s.scheduled_at else None,
                "executed_at":  s.executed_at.isoformat() if s.executed_at else None,
                "result":     s.result,
            } for s in steps],
        }
    finally:
        db.close()


@router.patch("/journey-instances/{instance_id}")
def update_journey_instance(instance_id: str, body: JourneyInstanceUpdate):
    """Pause, resume, exit, or update step progress on a journey instance.
    Also used by N8N to report journey completion."""
    from crm_models import JourneyInstance
    db = SessionLocal()
    try:
        inst = db.query(JourneyInstance).filter(JourneyInstance.id == instance_id).first()
        if not inst:
            raise HTTPException(status_code=404, detail="Journey instance not found")
        if body.status:
            inst.status = body.status.upper()
            if body.status.upper() in ("COMPLETED", "EXITED"):
                inst.completed_at = datetime.utcnow()
        if body.exit_reason is not None:
            inst.exit_reason = body.exit_reason
        if body.result_data is not None:
            inst.result_data = body.result_data
        if body.current_step is not None:
            inst.current_step = body.current_step
        inst.updated_at = datetime.utcnow()
        db.commit()
        return {"instance_id": inst.id, "status": inst.status, "current_step": inst.current_step}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


# ─── Customer Timeline (CRM view) ─────────────────────────────────────────────

@router.get("/customers/{email}/timeline")
def customer_timeline(email: str):
    """
    Full customer journey timeline: profile + active journeys + all messages sent.
    Used by CRM dashboard to display customer journey view.
    """
    from crm_models import Customer, JourneyInstance, Journey, MessageLog, JourneyStep
    db = SessionLocal()
    try:
        customer = db.query(Customer).filter(Customer.email == email).first()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        # Active journey instances
        instances = db.query(JourneyInstance).filter(
            JourneyInstance.customer_id == customer.id,
        ).order_by(JourneyInstance.started_at.desc()).limit(10).all()

        active_journeys = []
        for inst in instances:
            journey = db.query(Journey).filter(Journey.id == inst.journey_id).first()
            step_count = len(journey.template_json or []) if journey else 0
            progress = round(inst.current_step / step_count * 100) if step_count else 0
            active_journeys.append({
                "instance_id":   inst.id,
                "journey_name":  journey.name if journey else inst.journey_id,
                "status":        inst.status,
                "current_step":  inst.current_step,
                "total_steps":   step_count,
                "progress_pct":  progress,
                "started_at":    inst.started_at.isoformat(),
            })

        # All messages sent to this customer (email + WhatsApp)
        messages = db.query(MessageLog).filter(
            MessageLog.customer_email == email,
        ).order_by(MessageLog.sent_at.desc()).limit(50).all()

        message_timeline = [{
            "id":          m.id,
            "channel":     m.channel,
            "template_id": m.template_id,
            "provider":    m.provider,
            "status":      m.status,
            "sent_at":     m.sent_at.isoformat() if m.sent_at else None,
        } for m in messages]

        # Next pending step
        next_step = db.query(JourneyStep).join(
            JourneyInstance, JourneyStep.journey_instance_id == JourneyInstance.id
        ).filter(
            JourneyInstance.customer_id == customer.id,
            JourneyInstance.status == "ACTIVE",
            JourneyStep.status == "PENDING",
        ).order_by(JourneyStep.scheduled_at).first()

        return {
            "customer": {
                "id":          customer.id,
                "email":       customer.email,
                "first_name":  customer.first_name,
                "last_name":   customer.last_name,
                "orders_count": customer.orders_count,
                "total_spent": customer.total_spent,
                "last_order_date": customer.last_order_date.isoformat() if customer.last_order_date else None,
            },
            "active_journeys":  active_journeys,
            "messages":         message_timeline,
            "next_action": {
                "step_type":    next_step.step_type if next_step else None,
                "step_name":    next_step.step_name if next_step else None,
                "scheduled_at": next_step.scheduled_at.isoformat() if next_step and next_step.scheduled_at else None,
            } if next_step else None,
        }
    finally:
        db.close()


# ─── N8N Step Logging (bidirectional sync) ────────────────────────────────────

@router.post("/journey-steps/{step_id}/log")
def log_journey_step(step_id: str, body: JourneyStepLog):
    """
    Called by N8N after executing a step.
    Updates step status + result, logs message, advances instance.current_step.
    """
    from crm_models import JourneyStep, JourneyInstance, MessageLog
    db = SessionLocal()
    try:
        step = db.query(JourneyStep).filter(JourneyStep.id == step_id).first()
        if not step:
            raise HTTPException(status_code=404, detail="Step not found")

        step.status = body.status.upper()
        step.result = body.result
        step.executed_at = body.executed_at or datetime.utcnow()

        # Advance instance step counter
        instance = db.query(JourneyInstance).filter(
            JourneyInstance.id == step.journey_instance_id
        ).first()
        if instance and step.step_index is not None:
            instance.current_step = max(instance.current_step, step.step_index + 1)
            instance.updated_at = datetime.utcnow()

        # Log to crm_messages for dedup + analytics
        if body.status.upper() == "EXECUTED" and step.step_type in ("email", "whatsapp"):
            action = step.action_data or {}
            msg_log = MessageLog(
                id=str(__import__("uuid").uuid4()),
                customer_id=instance.customer_id if instance else None,
                customer_email=instance.email if instance else None,
                channel=step.step_type,
                template_id=action.get("template_id"),
                provider=action.get("provider", "unknown"),
                status="SENT",
                journey_instance_id=step.journey_instance_id,
                sent_at=step.executed_at,
            )
            db.add(msg_log)

        db.commit()
        return {"step_id": step_id, "status": step.status}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.post("/webhooks/n8n")
async def n8n_webhook(request: Request):
    """
    Generic inbound webhook from N8N.
    Handles: journey_step_result, journey_complete, journey_error.
    Body: { "event": "step_result|journey_complete|journey_error", "data": {...} }
    """
    from crm_models import JourneyInstance, JourneyStep
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event   = payload.get("event")
    data    = payload.get("data", {})
    db      = SessionLocal()

    try:
        if event == "journey_complete":
            instance_id = data.get("instance_id")
            if instance_id:
                inst = db.query(JourneyInstance).filter(JourneyInstance.id == instance_id).first()
                if inst:
                    inst.status = "COMPLETED"
                    inst.completed_at = datetime.utcnow()
                    inst.result_data = data.get("result_data")
                    db.commit()
            return {"ok": True, "event": event}

        if event == "journey_error":
            instance_id = data.get("instance_id")
            if instance_id:
                inst = db.query(JourneyInstance).filter(JourneyInstance.id == instance_id).first()
                if inst:
                    inst.status = "EXITED"
                    inst.exit_reason = data.get("error", "N8N error")
                    inst.completed_at = datetime.utcnow()
                    db.commit()
            return {"ok": True, "event": event}

        if event == "step_result":
            step_id = data.get("step_id")
            if step_id:
                step = db.query(JourneyStep).filter(JourneyStep.id == step_id).first()
                if step:
                    step.status = data.get("status", "EXECUTED").upper()
                    step.result = data.get("result")
                    step.executed_at = datetime.utcnow()
                    db.commit()
                    # Phase 3.5: Broadcast to WebSocket clients via Redis pub/sub
                    try:
                        if redis:
                            import json as _json
                            _redis = redis.Redis.from_url(
                                os.getenv("REDIS_URL", "redis://pureleven-redis:6379/0"),
                                decode_responses=True
                            )
                            _redis.publish("pubsub:steps", _json.dumps({
                                "id": step.id,
                                "step_type": step.step_type,
                                "step_name": step.step_name,
                                "status": step.status,
                                "result": step.result,
                                "journey_instance_id": step.journey_instance_id,
                                "timestamp": datetime.utcnow().isoformat(),
                                **{k: data.get(k) for k in ("email", "customer_id", "journey_name") if data.get(k)},
                            }))
                            _redis.close()
                    except Exception as _re:
                        logger.warning("Redis broadcast failed (non-fatal): %s", _re)
            return {"ok": True, "event": event}

        logger.warning("Unknown N8N webhook event: %s", event)
        return {"ok": False, "error": f"Unknown event: {event}"}
    finally:
        db.close()


# ─── Trigger helpers (called from existing webhook handlers) ──────────────────

def _background_assign_journeys(customer_id: str, trigger: str):
    """Open a fresh DB session and run journey assignment. Safe for background tasks."""
    db = SessionLocal()
    try:
        assign_customer_to_journeys(customer_id, trigger, db)
    except Exception as exc:
        logger.error("assign_customer_to_journeys failed: %s", exc)
    finally:
        db.close()


# ─── Phase 4.3: Attribution background helper ─────────────────────────────────

def _background_backtrack_attribution(customer_id: str, order_id: str, order_value: float):
    """
    Link a completed order to the journey that drove it.
    Finds the most recent ACTIVE or COMPLETED JourneyInstance for this customer
    and writes a JourneyAttribution record.
    """
    from crm_models import JourneyInstance, JourneyAttribution
    db = SessionLocal()
    try:
        # Find the most recently-started journey instance for this customer
        instance = (
            db.query(JourneyInstance)
            .filter(
                JourneyInstance.customer_id == customer_id,
                JourneyInstance.status.in_(["ACTIVE", "COMPLETED"]),
            )
            .order_by(JourneyInstance.started_at.desc())
            .first()
        )
        if not instance:
            logger.info("No journey instance to attribute order %s to", order_id)
            return

        attr = JourneyAttribution(
            journey_id=instance.journey_id,
            journey_instance_id=instance.id,
            customer_id=customer_id,
            order_id=order_id,
            order_value=order_value,
            attributed_revenue=order_value,
            currency="INR",
            attribution_model="last_touch",
            conversion_date=datetime.utcnow(),
        )
        db.add(attr)
        db.commit()
        logger.info("Attribution recorded: order %s → journey %s", order_id, instance.journey_id)
    except Exception as exc:
        logger.error("Attribution backtrack failed: %s", exc)
        db.rollback()
    finally:
        db.close()


# ─── Phase 5: Journey Clone, A/B Variants, Bulk Enroll, Execute Step ──────────

class JourneyVariantCreate(BaseModel):
    variant_name: str
    traffic_split_pct: int = 50
    template_json: Optional[Dict[str, Any]] = None
    config_changes: Optional[Dict[str, Any]] = None


class BulkEnrollRequest(BaseModel):
    csv_content: str


class JourneyStepExecuteRequest(BaseModel):
    step_type: str                         # email | meta_audience | google_audience | whatsapp
    customer_id: Optional[str] = None
    email: Optional[str] = None
    action_data: Optional[Dict[str, Any]] = None  # template_id, subject, body, audience_id, etc.
    step_id: Optional[str] = None          # journey step record id for result logging


@router.post("/journeys/{journey_id}/clone", status_code=201)
def clone_journey(journey_id: str):
    """
    Create a DRAFT copy of an existing journey with '(Copy)' suffix.
    Returns the new journey object.
    """
    from crm_models import Journey
    db = SessionLocal()
    try:
        source = db.query(Journey).filter(Journey.id == journey_id).first()
        if not source:
            raise HTTPException(status_code=404, detail="Journey not found")

        copy_name = f"{source.name} (Copy)"
        # Ensure unique name by appending a counter if needed
        suffix = 0
        base_name = copy_name
        while db.query(Journey).filter(Journey.name == copy_name).first():
            suffix += 1
            copy_name = f"{base_name} {suffix}"

        new_journey = Journey(
            name=copy_name,
            description=source.description,
            segment_id=source.segment_id,
            status="DRAFT",
            entry_trigger=source.entry_trigger,
            exit_criteria=source.exit_criteria,
            max_frequency_per_day=source.max_frequency_per_day,
            n8n_workflow_id=source.n8n_workflow_id,
            template_json=source.template_json,
        )
        db.add(new_journey)
        db.commit()
        db.refresh(new_journey)
        return {
            "id": new_journey.id,
            "name": new_journey.name,
            "status": new_journey.status,
            "entry_trigger": new_journey.entry_trigger,
            "cloned_from": journey_id,
        }
    finally:
        db.close()


@router.post("/journeys/{journey_id}/variants", status_code=201)
def create_journey_variant(journey_id: str, body: JourneyVariantCreate):
    """Create an A/B variant for a journey."""
    from crm_models import Journey, JourneyVariant
    db = SessionLocal()
    try:
        journey = db.query(Journey).filter(Journey.id == journey_id).first()
        if not journey:
            raise HTTPException(status_code=404, detail="Journey not found")

        variant = JourneyVariant(
            journey_id=journey_id,
            variant_name=body.variant_name,
            traffic_split_pct=max(1, min(99, body.traffic_split_pct)),
            template_json=body.template_json or journey.template_json,
            config_changes=body.config_changes,
            status="DRAFT",
        )
        db.add(variant)
        db.commit()
        db.refresh(variant)
        return {
            "id": variant.id,
            "journey_id": journey_id,
            "variant_name": variant.variant_name,
            "traffic_split_pct": variant.traffic_split_pct,
            "status": variant.status,
            "enrollments": variant.enrollments,
            "conversions": variant.conversions,
            "revenue": variant.revenue,
            "created_at": variant.created_at.isoformat(),
        }
    finally:
        db.close()


@router.get("/journeys/{journey_id}/variants")
def list_journey_variants(journey_id: str):
    """List all A/B variants for a journey with performance stats."""
    from crm_models import Journey, JourneyVariant
    db = SessionLocal()
    try:
        journey = db.query(Journey).filter(Journey.id == journey_id).first()
        if not journey:
            raise HTTPException(status_code=404, detail="Journey not found")

        variants = db.query(JourneyVariant).filter(JourneyVariant.journey_id == journey_id).all()
        return {
            "journey_id": journey_id,
            "variants": [
                {
                    "id": v.id,
                    "variant_name": v.variant_name,
                    "traffic_split_pct": v.traffic_split_pct,
                    "status": v.status,
                    "enrollments": v.enrollments,
                    "conversions": v.conversions,
                    "revenue": v.revenue,
                    "created_at": v.created_at.isoformat(),
                }
                for v in variants
            ],
        }
    finally:
        db.close()


@router.post("/journeys/{journey_id}/variants/{variant_id}/promote")
def promote_variant_winner(journey_id: str, variant_id: str):
    """Mark a variant as the winner and pause all others."""
    from crm_models import JourneyVariant
    db = SessionLocal()
    try:
        variants = db.query(JourneyVariant).filter(JourneyVariant.journey_id == journey_id).all()
        if not variants:
            raise HTTPException(status_code=404, detail="No variants found")

        winner = next((v for v in variants if v.id == variant_id), None)
        if not winner:
            raise HTTPException(status_code=404, detail="Variant not found")

        for v in variants:
            v.status = "WINNER" if v.id == variant_id else "PAUSED"
        db.commit()
        return {"ok": True, "winner_id": variant_id, "winner_name": winner.variant_name}
    finally:
        db.close()


@router.post("/journeys/{journey_id}/bulk-enroll")
def bulk_enroll_customers(journey_id: str, body: BulkEnrollRequest, background_tasks: BackgroundTasks):
    """
    Enroll a list of customers from CSV content into a journey.
    Required CSV column: email. Optional: first_name, last_name, phone.
    Returns a job summary with success/error counts.
    """
    from crm_models import Journey, BulkEnrollmentJob
    db = SessionLocal()
    try:
        journey = db.query(Journey).filter(Journey.id == journey_id).first()
        if not journey:
            raise HTTPException(status_code=404, detail="Journey not found")

        # Parse CSV
        reader = csv.DictReader(io.StringIO(body.csv_content.strip()))
        rows = list(reader)
        if not rows:
            raise HTTPException(status_code=400, detail="CSV is empty or has no data rows")

        if "email" not in (reader.fieldnames or []):
            raise HTTPException(status_code=400, detail="CSV must have an 'email' column")

        # Create job record
        job = BulkEnrollmentJob(
            journey_id=journey_id,
            status="RUNNING",
            total_rows=len(rows),
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        job_id = job.id
        db.close()

        # Process in background
        background_tasks.add_task(_process_bulk_enrollment, job_id, journey_id, rows)

        # Return immediate result for small batches (≤100 rows)
        if len(rows) <= 100:
            result = _process_bulk_enrollment_sync(journey_id, rows)
            return {
                "job_id": job_id,
                "total_rows": len(rows),
                "success_count": result["success"],
                "error_count": result["errors"],
                "error_rows": result["error_rows"],
                "status": "COMPLETED",
            }

        return {
            "job_id": job_id,
            "total_rows": len(rows),
            "status": "RUNNING",
            "message": "Bulk enrollment started. Check job status for progress.",
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        try:
            db.close()
        except Exception:
            pass


@router.get("/journeys/{journey_id}/bulk-enroll/{job_id}")
def get_bulk_enrollment_job(journey_id: str, job_id: str):
    """
    Get status and details of a bulk enrollment job.
    Returns: {status, total_rows, success_count, error_count, error_rows, created_at, completed_at}
    """
    from crm_models import BulkEnrollmentJob, Journey
    db = SessionLocal()
    try:
        # Verify journey exists
        journey = db.query(Journey).filter(Journey.id == journey_id).first()
        if not journey:
            raise HTTPException(status_code=404, detail="Journey not found")
        
        # Get job
        job = db.query(BulkEnrollmentJob).filter(
            BulkEnrollmentJob.id == job_id,
            BulkEnrollmentJob.journey_id == journey_id
        ).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return {
            "id": job.id,
            "status": job.status,
            "total_rows": job.total_rows,
            "success_count": job.success_count,
            "error_count": job.error_count,
            "error_rows": job.error_rows or [],
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


@router.get("/journeys/{journey_id}/bulk-enroll/latest")
def get_latest_bulk_enrollment_job(journey_id: str):
    """
    Get the most recent bulk enrollment job for a journey.
    Returns: {id, status, total_rows, success_count, error_count, error_rows, created_at, completed_at}
    """
    from crm_models import BulkEnrollmentJob, Journey
    db = SessionLocal()
    try:
        # Verify journey exists
        journey = db.query(Journey).filter(Journey.id == journey_id).first()
        if not journey:
            raise HTTPException(status_code=404, detail="Journey not found")
        
        # Get latest job
        job = db.query(BulkEnrollmentJob).filter(
            BulkEnrollmentJob.journey_id == journey_id
        ).order_by(BulkEnrollmentJob.created_at.desc()).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="No bulk enrollment jobs found for this journey")
        
        return {
            "id": job.id,
            "status": job.status,
            "total_rows": job.total_rows,
            "success_count": job.success_count,
            "error_count": job.error_count,
            "error_rows": job.error_rows or [],
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        db.close()


def _process_bulk_enrollment_sync(journey_id: str, rows: list) -> dict:
    """Process CSV rows synchronously (for small batches). Returns {success, errors, error_rows}."""
    success, errors, error_rows = 0, 0, []
    db = SessionLocal()
    try:
        for i, row in enumerate(rows, start=2):
            email = (row.get("email") or "").strip().lower()
            if not email:
                errors += 1
                error_rows.append({"row": i, "email": "", "reason": "Missing email"})
                continue
            try:
                customer = get_or_create_customer(
                    db,
                    email=email,
                    phone=(row.get("phone") or "").strip() or None,
                )
                # Update name if provided
                first_name = (row.get("first_name") or "").strip()
                last_name = (row.get("last_name") or "").strip()
                if first_name and not customer.first_name:
                    customer.first_name = first_name
                if last_name and not customer.last_name:
                    customer.last_name = last_name
                if first_name or last_name:
                    db.commit()
                assign_customer_to_journeys(customer.id, "bulk_enroll", db)
                success += 1
            except Exception as exc:
                errors += 1
                error_rows.append({"row": i, "email": email, "reason": str(exc)})
    finally:
        db.close()
    return {"success": success, "errors": errors, "error_rows": error_rows}


def _process_bulk_enrollment(job_id: str, journey_id: str, rows: list):
    """Background task: process bulk enrollment and update job record."""
    from crm_models import BulkEnrollmentJob
    result = _process_bulk_enrollment_sync(journey_id, rows)
    db = SessionLocal()
    try:
        job = db.query(BulkEnrollmentJob).filter(BulkEnrollmentJob.id == job_id).first()
        if job:
            job.status = "COMPLETED"
            job.success_count = result["success"]
            job.error_count = result["errors"]
            job.error_rows = result["error_rows"]
            job.completed_at = datetime.utcnow()
            db.commit()
    except Exception as exc:
        logger.error("Failed to update bulk enrollment job %s: %s", job_id, exc)
    finally:
        db.close()


@router.post("/journeys/{journey_id}/execute-step")
async def execute_journey_step(journey_id: str, body: JourneyStepExecuteRequest, background_tasks: BackgroundTasks):
    """
    Phase 4.1: Dispatcher endpoint for N8N to trigger channel-specific actions.
    N8N calls this to send emails, sync audiences, etc. without needing credentials itself.
    step_type: email | meta_audience | google_audience | whatsapp | attribution
    """
    step_type = body.step_type.lower()

    if step_type == "email":
        background_tasks.add_task(_execute_email_step, body.email, body.customer_id, body.action_data or {}, body.step_id)
        return {"ok": True, "step_type": step_type, "queued": True}

    elif step_type == "meta_audience":
        background_tasks.add_task(_execute_meta_audience_step, body.customer_id, body.action_data or {}, body.step_id)
        return {"ok": True, "step_type": step_type, "queued": True}

    elif step_type == "google_audience":
        background_tasks.add_task(_execute_google_audience_step, body.customer_id, body.action_data or {}, body.step_id)
        return {"ok": True, "step_type": step_type, "queued": True}

    else:
        raise HTTPException(status_code=400, detail=f"Unknown step_type: {step_type}")


def _execute_email_step(email: Optional[str], customer_id: Optional[str], action_data: dict, step_id: Optional[str]):
    """Send a journey step email via SendGrid."""
    try:
        if not email and customer_id:
            from crm_models import Customer as CModel
            db = SessionLocal()
            try:
                cust = db.query(CModel).filter(CModel.id == customer_id).first()
                email = cust.email if cust else None
            finally:
                db.close()
        if not email:
            logger.warning("execute_email_step: no email for customer %s", customer_id)
            return
        template_name = action_data.get("template_name", "generic_journey")
        _send_transactional_email_task(template_name, {"email": email, **action_data}, step_id)
        logger.info("Journey email step executed for %s (template: %s)", email, template_name)
    except Exception as exc:
        logger.error("execute_email_step failed: %s", exc)


def _execute_meta_audience_step(customer_id: Optional[str], action_data: dict, step_id: Optional[str]):
    """Add/remove customer from Meta Custom Audience."""
    try:
        from meta_audience_sync import MetaAudienceSync
        from crm_models import Customer as CModel
        if not customer_id:
            return
        db = SessionLocal()
        try:
            cust = db.query(CModel).filter(CModel.id == customer_id).first()
            if not cust:
                return
            sync = MetaAudienceSync()
            audience_id = action_data.get("audience_id")
            sync.sync_customers_to_audience([cust], audience_id)
            logger.info("Meta audience step for customer %s → audience %s", customer_id, audience_id)
        finally:
            db.close()
    except ImportError:
        logger.warning("meta_audience_sync not available, skipping Meta audience step")
    except Exception as exc:
        logger.error("execute_meta_audience_step failed: %s", exc)


def _execute_google_audience_step(customer_id: Optional[str], action_data: dict, step_id: Optional[str]):
    """Add customer to Google Ads Customer Match audience."""
    try:
        from google_audience_sync import GoogleAudienceSync
        from crm_models import Customer as CModel
        if not customer_id:
            return
        db = SessionLocal()
        try:
            cust = db.query(CModel).filter(CModel.id == customer_id).first()
            if not cust:
                return
            sync = GoogleAudienceSync()
            user_list_id = action_data.get("user_list_id")
            sync.sync_customers_to_audience([cust], user_list_id)
            logger.info("Google audience step for customer %s → list %s", customer_id, user_list_id)
        finally:
            db.close()
    except ImportError:
        logger.warning("google_audience_sync not available, skipping Google audience step")
    except Exception as exc:
        logger.error("execute_google_audience_step failed: %s", exc)


@router.get("/journeys/{journey_id}/attribution")
def get_journey_attribution(journey_id: str):
    """Return attribution stats for a journey: total revenue, conversions, avg order value."""
    from crm_models import JourneyAttribution
    db = SessionLocal()
    try:
        records = db.query(JourneyAttribution).filter(
            JourneyAttribution.journey_id == journey_id
        ).all()
        total_revenue = sum(r.attributed_revenue for r in records)
        conversions = len(records)
        avg_order = total_revenue / conversions if conversions else 0
        return {
            "journey_id": journey_id,
            "conversions": conversions,
            "total_attributed_revenue": round(total_revenue, 2),
            "avg_order_value": round(avg_order, 2),
            "currency": "INR",
            "records": [
                {
                    "id": r.id,
                    "order_id": r.order_id,
                    "order_value": r.order_value,
                    "attributed_revenue": r.attributed_revenue,
                    "attribution_model": r.attribution_model,
                    "conversion_date": r.conversion_date.isoformat() if r.conversion_date else None,
                }
                for r in records[-20:]  # return last 20
            ],
        }
    finally:
        db.close()


@router.get("/auth/google-ads/callback")
def google_ads_oauth_callback(code: str, state: Optional[str] = None):
    """
    OAuth callback from Google Ads API.
    Exchanges the authorization code for access and refresh tokens.
    """
    import urllib.request
    import urllib.parse
    import urllib.error
    import json as json_lib
    
    try:
        client_id = os.getenv("GOOGLE_ADS_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_ADS_CLIENT_SECRET")
        redirect_uri = "https://track.pureleven.com/api/crm/auth/google-ads/callback"
        
        if not client_id or not client_secret:
            raise HTTPException(status_code=500, detail="Google Ads credentials not configured")
        
        # Log the request details for debugging
        logger.info(f"OAuth callback: code={code[:20]}..., redirect_uri={redirect_uri}")
        
        # Exchange code for tokens using urllib (no external deps)
        token_url = "https://www.googleapis.com/oauth2/v4/token"
        token_data = urllib.parse.urlencode({
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }).encode("utf-8")
        
        req = urllib.request.Request(token_url, data=token_data, method="POST")
        try:
            with urllib.request.urlopen(req) as response:
                token_response = json_lib.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # Capture the actual error response from Google
            error_body = e.read().decode("utf-8")
            logger.error(f"Google OAuth HTTP {e.code}: {error_body}")
            raise HTTPException(status_code=400, detail=f"Token exchange failed (HTTP {e.code}): {error_body}")
        except Exception as e:
            logger.error(f"Google OAuth token exchange failed: {type(e).__name__}: {e}")
            raise HTTPException(status_code=400, detail=f"Token exchange failed: {str(e)}")
        
        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        
        if not refresh_token:
            return {
                "status": "error",
                "message": "No refresh token received. Make sure to use access_type=offline in the authorization URL.",
                "access_token": access_token[:50] + "..." if access_token else None,
            }
        
        # Save refresh token to .env file
        env_file = "/opt/pureleven/ai-engine/.env"
        if os.path.exists(env_file):
            with open(env_file, "r") as f:
                lines = f.readlines()
            
            found = False
            for i, line in enumerate(lines):
                if line.startswith("GOOGLE_ADS_OAUTH_REFRESH_TOKEN="):
                    lines[i] = f"GOOGLE_ADS_OAUTH_REFRESH_TOKEN={refresh_token}\n"
                    found = True
                    break
            
            if not found:
                lines.append(f"GOOGLE_ADS_OAUTH_REFRESH_TOKEN={refresh_token}\n")
            
            with open(env_file, "w") as f:
                f.writelines(lines)
            
            logger.info("✅ Google Ads refresh token saved to .env")
        
        return {
            "status": "success",
            "message": "✅ Authorization successful! Refresh token has been saved.",
            "access_token": access_token[:50] + "..." if access_token else None,
            "refresh_token": refresh_token[:30] + "..." if refresh_token else None,
            "expires_in": token_response.get("expires_in"),
        }
        
    except Exception as e:
        logger.error("Google OAuth callback error: %s", e)
        raise HTTPException(status_code=500, detail=f"Callback processing failed: {str(e)}")
