
# ── Customer 360 (Sprint 0) ────────────────────────────────────────────────────
# These endpoints are appended to routes/customers.py.
# They use UUID customer_id (not email) to fetch from crm_customers + crm_orders + crm_events.

from sqlalchemy.orm import Session
from fastapi import Depends
from app.database import get_db
from app.repositories.customer_repository import CustomerRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.event_repository import EventRepository
from app.services.customer360_service import Customer360Service


@router.get('/customers/{customer_id}/360')
def get_customer_360(
    customer_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
):
    """
    Customer 360 profile.

    Returns:
      customer            — identity fields
      stats               — total_revenue, order_count, last_order_date
      latest_order        — most recent order details
      recent_activity_count — linked events in last 30 days
      customer_health     — { status: active | lapsed | inactive }

    Data sources: crm_customers + crm_orders + crm_events (linked only)
    """
    svc = Customer360Service(
        customer_repo=CustomerRepository(db),
        order_repo=OrderRepository(db),
        event_repo=EventRepository(db),
    )
    return svc.get_profile(customer_id)


@router.get('/customers/{customer_id}/timeline')
def get_customer_timeline(
    customer_id: str,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: None = Depends(_require_admin),
):
    """
    Unified customer activity timeline.

    Merges crm_orders + crm_events (WHERE customer_id IS NOT NULL), sorted newest first.
    Anonymous page_view and automated wabis_sent events (NULL customer_id) are excluded by design.

    Data sources: crm_orders (259/259 linked) + crm_events (146/370 linked)
    """
    svc = Customer360Service(
        customer_repo=CustomerRepository(db),
        order_repo=OrderRepository(db),
        event_repo=EventRepository(db),
    )
    return svc.get_timeline(customer_id, limit=limit, offset=offset)
