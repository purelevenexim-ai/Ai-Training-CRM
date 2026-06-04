"""
repositories/segment_repository.py

SegmentRepository — evaluates which crm_segments a customer belongs to.

The rule_set column in crm_segments is currently empty ({}) for all rows.
Membership is evaluated at query-time by matching customer stats against
the well-known segment names defined in this system.

Segment definitions (in sync with crm_segments table):
  buyer             — has at least one order
  high_ltv          — lifetime spend > ₹2,000
  lapsed_buyer      — last order 60+ days ago (and has ordered)
  replenishment_due — last order 30–50 days ago (and has ordered)

To add a new segment: insert into crm_segments, then add a matching
elif branch in _evaluate() below.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.crm_models import Segment


class SegmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_customer_segments(
        self,
        customer_id: str,
        total_revenue: float,
        order_count: int,
        last_order_date: datetime | None,
    ) -> list[dict[str, Any]]:
        """
        Return list of segments this customer qualifies for.

        Args:
            customer_id: UUID string (used for future rule_set queries)
            total_revenue: sum of paid orders
            order_count: number of paid orders
            last_order_date: datetime of most recent paid order, or None
        """
        active_segments = (
            self.db.query(Segment)
            .filter(Segment.is_active == True)
            .all()
        )

        result: list[dict[str, Any]] = []
        for seg in active_segments:
            if self._evaluate(seg.name, total_revenue, order_count, last_order_date):
                result.append(
                    {
                        "id": str(seg.id),
                        "name": seg.name,
                        "description": seg.description,
                    }
                )
        return result

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _evaluate(
        self,
        name: str,
        total_revenue: float,
        order_count: int,
        last_order_date: datetime | None,
    ) -> bool:
        """Return True if the customer satisfies the named segment rule."""
        if name == "buyer":
            return order_count > 0

        if name == "high_ltv":
            return total_revenue > 2000.0

        if name == "lapsed_buyer":
            if order_count == 0 or last_order_date is None:
                return False
            days_since = (datetime.utcnow() - last_order_date).days
            return days_since >= 60

        if name == "replenishment_due":
            if order_count == 0 or last_order_date is None:
                return False
            days_since = (datetime.utcnow() - last_order_date).days
            return 30 <= days_since <= 50

        # Unknown segment name — skip (rule_set extension point for later)
        return False
