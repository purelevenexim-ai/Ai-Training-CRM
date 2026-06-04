"""
repositories/customer_repository.py

Data access layer for crm_customers.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.crm_models import Customer


class CustomerRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_id(self, customer_id: str) -> Customer | None:
        return self.db.query(Customer).filter(Customer.id == customer_id).first()

    def get_by_email(self, email: str) -> Customer | None:
        return (
            self.db.query(Customer)
            .filter(Customer.email == email.strip().lower())
            .first()
        )
