"""
services/customer360_service.py

Customer 360 profile and timeline builder.

Architecture:
  CustomerRepository  → crm_customers
  OrderRepository     → crm_orders
  EventRepository     → crm_events (linked only)
  MessageRepository   → crm_messages (linked only)
  SegmentRepository   → crm_segments (query-based evaluation)
            ↓
  Customer360Service  → profile + timeline
            ↓
  /360 and /timeline API endpoints

Sprint 0: customers + orders + linked events.
Sprint 1: + messages + segment membership.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import HTTPException

from app.repositories.customer_repository import CustomerRepository
from app.repositories.event_repository import EventRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.segment_repository import SegmentRepository


def _derive_health_status(last_order_date: datetime | None, recent_activity_count: int) -> str:
    if last_order_date is None:
        return "inactive"
    days_since = (datetime.utcnow() - last_order_date).days
    if days_since <= 90:
        return "active"
    return "lapsed"


class Customer360Service:
    def __init__(
        self,
        customer_repo: CustomerRepository,
        order_repo: OrderRepository,
        event_repo: EventRepository,
        message_repo: MessageRepository,
        segment_repo: SegmentRepository,
    ) -> None:
        self.customer_repo = customer_repo
        self.order_repo = order_repo
        self.event_repo = event_repo
        self.message_repo = message_repo
        self.segment_repo = segment_repo

    def get_profile(self, customer_id: str) -> dict[str, Any]:
        customer = self.customer_repo.get_by_id(customer_id)
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")

        total_revenue = self.order_repo.get_total_revenue(customer_id)
        order_count = self.order_repo.get_order_count(customer_id)
        latest_order = self.order_repo.get_latest_order(customer_id)
        recent_activity_count = self.event_repo.get_recent_activity_count(customer_id, days=30)
        messages_count = self.message_repo.get_message_count(customer_id)

        last_order_date = latest_order.order_date if latest_order else None

        segments = self.segment_repo.get_customer_segments(
            customer_id=customer_id,
            total_revenue=total_revenue,
            order_count=order_count,
            last_order_date=last_order_date,
        )

        health_status = _derive_health_status(
            last_order_date=last_order_date,
            recent_activity_count=recent_activity_count,
        )

        return {
            "customer": {
                "id": customer.id,
                "email": customer.email,
                "phone": customer.phone,
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "shopify_customer_id": customer.shopify_customer_id,
                "email_subscribed": customer.email_subscribed,
                "sms_subscribed": customer.sms_subscribed,
                "created_at": customer.created_at.isoformat() if customer.created_at else None,
            },
            "stats": {
                "total_revenue": round(total_revenue, 2),
                "order_count": order_count,
                "last_order_date": (last_order_date.isoformat() if last_order_date else None),
            },
            "latest_order": (
                {
                    "id": latest_order.id,
                    "shopify_order_id": latest_order.shopify_order_id,
                    "date": latest_order.order_date.isoformat() if latest_order.order_date else None,
                    "amount": latest_order.total_amount,
                    "currency": latest_order.currency,
                    "status": latest_order.status,
                }
                if latest_order
                else None
            ),
            "recent_activity_count": recent_activity_count,
            "messages_count": messages_count,
            "segments": segments,
            "customer_health": {
                "status": health_status,
            },
        }

    def get_timeline(
        self,
        customer_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        customer = self.customer_repo.get_by_id(customer_id)
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")

        orders = self.order_repo.get_by_customer_id(customer_id)
        events = self.event_repo.get_linked_events(customer_id, limit=limit + offset + 50)
        messages = self.message_repo.get_by_customer_id(customer_id, limit=limit + offset + 50)

        items: list[dict[str, Any]] = []

        for order in orders:
            items.append(
                {
                    "type": "order",
                    "date": order.order_date.isoformat() if order.order_date else None,
                    "order_id": order.id,
                    "shopify_order_id": order.shopify_order_id,
                    "amount": order.total_amount,
                    "currency": order.currency,
                    "status": order.status,
                    "description": f"Order — \u20b9{order.total_amount:,.0f}",
                }
            )

        for event in events:
            items.append(
                {
                    "type": "event",
                    "date": event.timestamp.isoformat() if event.timestamp else None,
                    "event_type": event.event_type,
                    "source": event.source,
                    "description": event.event_type.replace("_", " ").title(),
                    "event_data": event.event_data,
                }
            )

        for msg in messages:
            items.append(
                {
                    "type": "message",
                    "date": msg.sent_at.isoformat() if msg.sent_at else None,
                    "channel": msg.channel,
                    "template_id": msg.template_id,
                    "status": msg.status,
                    "provider": msg.provider,
                    "description": f"{(msg.channel or 'message').title()} — {msg.template_id or 'sent'}",
                }
            )

        items.sort(key=lambda x: x["date"] or "", reverse=True)

        total = len(items)
        page = items[offset : offset + limit]

        return {
            "customer_id": customer_id,
            "total": total,
            "limit": limit,
            "offset": offset,
            "items": page,
        }
