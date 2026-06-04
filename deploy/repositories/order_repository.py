"""
repositories/order_repository.py

Data access layer for crm_orders.
"""
from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.crm_models import Order


class OrderRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_customer_id(self, customer_id: str) -> list[Order]:
        return (
            self.db.query(Order)
            .filter(Order.customer_id == customer_id)
            .order_by(Order.order_date.desc())
            .all()
        )

    def get_latest_order(self, customer_id: str) -> Order | None:
        return (
            self.db.query(Order)
            .filter(Order.customer_id == customer_id)
            .order_by(Order.order_date.desc())
            .first()
        )

    def get_total_revenue(self, customer_id: str) -> float:
        result = (
            self.db.query(func.sum(Order.total_amount))
            .filter(Order.customer_id == customer_id)
            .scalar()
        )
        return float(result or 0.0)

    def get_order_count(self, customer_id: str) -> int:
        return (
            self.db.query(func.count(Order.id))
            .filter(Order.customer_id == customer_id)
            .scalar()
            or 0
        )
