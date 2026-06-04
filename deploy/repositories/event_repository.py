"""
repositories/event_repository.py

Data access layer for crm_events (linked events only — customer_id IS NOT NULL).

Note: Events with NULL customer_id are intentionally excluded.
  - page_view events (197 rows): anonymous visitors, no customer_id by design.
  - wabis_sent events (27 rows): automated WhatsApp sends, no customer_id by design.
These are NOT data quality issues.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.crm_models import Event


class EventRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_linked_events(self, customer_id: str, limit: int = 100) -> list[Event]:
        """Return events linked to this customer, sorted newest first."""
        return (
            self.db.query(Event)
            .filter(Event.customer_id == customer_id)
            .order_by(Event.timestamp.desc())
            .limit(limit)
            .all()
        )

    def get_recent_activity_count(self, customer_id: str, days: int = 30) -> int:
        """Count linked events in the last N days."""
        since = datetime.utcnow() - timedelta(days=days)
        return (
            self.db.query(func.count(Event.id))
            .filter(Event.customer_id == customer_id, Event.timestamp >= since)
            .scalar()
            or 0
        )
