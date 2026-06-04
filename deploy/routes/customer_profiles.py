"""
routes/customer_profiles.py

Customer identity resolution and profile management via PostgreSQL.

Endpoints:
  GET  /crm/profiles/resolve                — lookup by email / shopify_customer_id
  POST /crm/profiles/identify               — upsert customer + register identity
  GET  /crm/profiles/{customer_id}          — profile detail
  GET  /crm/profiles/{customer_id}/history  — event history (linked events only)

Rewritten from original SQLite version to use PostgreSQL via SQLAlchemy.
Routes moved from /customers/* to /crm/profiles/* to avoid conflicts with
the existing /customers/{email} endpoints in routes/customers.py.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.config import settings
from app.crm_models import Customer, CustomerIdentity, Event
from app.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["customer-profiles"])


# ── Auth ───────────────────────────────────────────────────────────────────────

def _require_admin(admin_secret: str = Query(..., alias="admin_secret")) -> None:
    if admin_secret != settings.admin_secret:
        raise HTTPException(status_code=403, detail="Invalid admin_secret")


# ── Models ─────────────────────────────────────────────────────────────────────

class IdentifyRequest(BaseModel):
    email: str = Field(default="")
    phone: str = Field(default="")
    first_name: str = Field(default="")
    last_name: str = Field(default="")
    shopify_customer_id: str = Field(default="")
    source: str = Field(default="web")


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/crm/profiles/resolve")
def resolve_customer(
    email: str = Query(default=""),
    shopify_customer_id: str = Query(default=""),
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
) -> list[dict[str, Any]]:
    """Lookup customer by email or Shopify customer ID."""
    if not email and not shopify_customer_id:
        raise HTTPException(status_code=400, detail="Provide email or shopify_customer_id")

    q = db.query(Customer)
    if email:
        q = q.filter(Customer.email == email.strip().lower())
    elif shopify_customer_id:
        q = q.filter(Customer.shopify_customer_id == shopify_customer_id.strip())

    rows = q.limit(10).all()
    return [_customer_to_dict(c) for c in rows]


@router.post("/crm/profiles/identify")
def identify_customer(
    payload: IdentifyRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    """
    Upsert customer profile and register identity links.
    Matches on email first, then shopify_customer_id.
    """
    customer: Customer | None = None

    if payload.email:
        customer = (
            db.query(Customer)
            .filter(Customer.email == payload.email.strip().lower())
            .first()
        )

    if customer is None and payload.shopify_customer_id:
        customer = (
            db.query(Customer)
            .filter(Customer.shopify_customer_id == payload.shopify_customer_id.strip())
            .first()
        )

    if customer:
        # Update non-null fields
        if payload.first_name:
            customer.first_name = payload.first_name
        if payload.last_name:
            customer.last_name = payload.last_name
        if payload.phone:
            customer.phone = payload.phone
        if payload.shopify_customer_id:
            customer.shopify_customer_id = payload.shopify_customer_id
        db.commit()
        status_str = "updated"
    else:
        if not payload.email:
            raise HTTPException(status_code=400, detail="email required to create a new customer")
        customer = Customer(
            email=payload.email.strip().lower(),
            phone=payload.phone or None,
            first_name=payload.first_name or None,
            last_name=payload.last_name or None,
            shopify_customer_id=payload.shopify_customer_id or None,
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        status_str = "created"

    # Register identity links (idempotent via get-or-create)
    identities_to_register: list[tuple[str, str]] = []
    if payload.email:
        identities_to_register.append(("email", payload.email.strip().lower()))
    if payload.phone:
        identities_to_register.append(("phone", payload.phone.strip()))
    if payload.shopify_customer_id:
        identities_to_register.append(("shopify_customer_id", payload.shopify_customer_id.strip()))

    for id_type, id_value in identities_to_register:
        existing = (
            db.query(CustomerIdentity)
            .filter(
                CustomerIdentity.canonical_customer_id == customer.id,
                CustomerIdentity.identity_type == id_type,
            )
            .first()
        )
        if existing is None:
            db.add(
                CustomerIdentity(
                    canonical_customer_id=customer.id,
                    identity_type=id_type,
                    identity_value=id_value,
                    confidence_score=1.0,
                )
            )
    db.commit()

    return {"customer_id": customer.id, "status": status_str}


@router.get("/crm/profiles/{customer_id}")
def get_profile(
    customer_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    """Get customer profile by UUID."""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return _customer_to_dict(customer)


@router.get("/crm/profiles/{customer_id}/history")
def get_history(
    customer_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
) -> dict[str, Any]:
    """
    Get linked event history for a customer (customer_id IS NOT NULL events only).
    Anonymous page_views and automated wabis_sent events are excluded by design.
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")

    events = (
        db.query(Event)
        .filter(Event.customer_id == customer_id)
        .order_by(Event.timestamp.desc())
        .limit(limit)
        .all()
    )

    return {
        "customer_id": customer_id,
        "count": len(events),
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "source": e.source,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "event_data": e.event_data,
            }
            for e in events
        ],
    }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _customer_to_dict(c: Customer) -> dict[str, Any]:
    return {
        "id": c.id,
        "email": c.email,
        "phone": c.phone,
        "first_name": c.first_name,
        "last_name": c.last_name,
        "shopify_customer_id": c.shopify_customer_id,
        "email_subscribed": c.email_subscribed,
        "sms_subscribed": c.sms_subscribed,
        "total_spent": c.total_spent,
        "orders_count": c.orders_count,
        "last_order_date": c.last_order_date.isoformat() if c.last_order_date else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
