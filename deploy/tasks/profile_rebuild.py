"""
tasks/profile_rebuild.py

Background task: rebuild customer metrics from crm_orders.

What it does:
  - Reads actual order data from crm_orders for a given customer
  - Updates crm_customers.orders_count, total_spent, last_order_date
  - Keeps customer master record in sync with real order data

Why it exists:
  - crm_customers.total_spent and orders_count may drift over time
    when orders are imported/updated outside the main flow
  - This task is the authoritative sync source (nightly via Celery beat)
  - Can also be triggered on-demand via POST /api/customers/{id}/rebuild-profile

Usage:
  # Trigger single customer rebuild
  rebuild_customer_profile.delay("customer-uuid")

  # Trigger full rebuild (all customers)  — runs nightly via beat
  rebuild_all_profiles.delay()
"""
from __future__ import annotations

import logging

from sqlalchemy import func, select, text

from app.celery_app import app
from app.crm_models import Customer, Order
from app.database import SessionLocal

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def rebuild_customer_profile(self, customer_id: str) -> dict:
    """
    Recompute and persist customer metrics from crm_orders.

    Returns dict with before/after values for observability.
    """
    try:
        with SessionLocal() as db:
            # Compute stats from authoritative order source
            stats = db.execute(
                select(
                    func.count(Order.id).label("order_count"),
                    func.coalesce(func.sum(Order.total_amount), 0).label("total_spent"),
                    func.max(Order.order_date).label("last_order_date"),
                ).where(
                    Order.customer_id == customer_id,
                    Order.status.in_(["paid", "fulfilled", "complete"]),
                )
            ).one()

            customer = db.get(Customer, customer_id)
            if customer is None:
                logger.warning("rebuild_customer_profile: customer %s not found", customer_id)
                return {"customer_id": customer_id, "status": "not_found"}

            before = {
                "orders_count": customer.orders_count,
                "total_spent": float(customer.total_spent or 0),
            }

            customer.orders_count = stats.order_count
            customer.total_spent = float(stats.total_spent)
            if stats.last_order_date is not None:
                customer.last_order_date = stats.last_order_date

            db.commit()

            after = {
                "orders_count": customer.orders_count,
                "total_spent": float(customer.total_spent or 0),
            }

            logger.info(
                "rebuild_customer_profile: %s before=%s after=%s",
                customer_id,
                before,
                after,
            )
            return {"customer_id": customer_id, "status": "ok", "before": before, "after": after}

    except Exception as exc:
        logger.error("rebuild_customer_profile failed for %s: %s", customer_id, exc)
        raise self.retry(exc=exc)


@app.task
def rebuild_all_profiles() -> dict:
    """
    Queue individual rebuild tasks for every customer.
    Called nightly by Celery beat (03:00 UTC).
    """
    with SessionLocal() as db:
        rows = db.execute(text("SELECT id FROM crm_customers")).fetchall()
        customer_ids = [str(r[0]) for r in rows]

    for cid in customer_ids:
        rebuild_customer_profile.delay(cid)

    logger.info("rebuild_all_profiles: queued %d jobs", len(customer_ids))
    return {"status": "queued", "count": len(customer_ids)}
