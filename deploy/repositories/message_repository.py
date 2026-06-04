"""
repositories/message_repository.py

MessageRepository — query interface for crm_messages.

Only returns messages WHERE customer_id IS NOT NULL.
Unlinked messages (failed sends to unknown addresses) are
intentionally excluded from customer timelines.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.crm_models import MessageLog


class MessageRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_customer_id(self, customer_id: str, limit: int = 100) -> list[MessageLog]:
        """Return messages linked to this customer, newest first."""
        return (
            self.db.query(MessageLog)
            .filter(
                MessageLog.customer_id == customer_id,
            )
            .order_by(MessageLog.sent_at.desc())
            .limit(limit)
            .all()
        )

    def get_message_count(self, customer_id: str) -> int:
        """Count of messages sent to this customer."""
        return (
            self.db.query(MessageLog)
            .filter(MessageLog.customer_id == customer_id)
            .count()
        )
