"""Multi-touch attribution helpers for Pureleven CRM.

This module computes derived attribution from crm_events and stores outputs only
when ATTRIBUTION_WRITE_ENABLED is true. Raw events remain the source of truth.
"""

from __future__ import annotations

import os
from datetime import timedelta
from typing import Any

from crm_models import Event, Order, OrderTouchpointAttribution


DEFAULT_MODELS = ("position_based_40_20_40", "first_touch", "last_touch", "linear")


class AttributionEngine:
    def __init__(self, db: Any, write_enabled: bool | None = None) -> None:
        self.db = db
        if write_enabled is None:
            write_enabled = (os.getenv("ATTRIBUTION_WRITE_ENABLED", "false") or "false").lower() in {
                "1",
                "true",
                "yes",
                "on",
            }
        self.write_enabled = write_enabled

    def _order(self, order_ref: str) -> Order | None:
        order = self.db.query(Order).filter(Order.id == order_ref).first()
        if order:
            return order
        return self.db.query(Order).filter(Order.shopify_order_id == order_ref).first()

    @staticmethod
    def _event_source(event: Event) -> str:
        data = event.event_data or {}
        return (
            data.get("utm_source")
            or data.get("source")
            or event.source
            or "unknown"
        )

    @staticmethod
    def _event_campaign(event: Event) -> tuple[str | None, str | None]:
        data = event.event_data or {}
        return data.get("campaign_id") or data.get("utm_campaign"), data.get("campaign_name") or data.get("utm_campaign")

    def touchpoints_for_order(self, order: Order, lookback_days: int = 30) -> list[Event]:
        if not order.customer_id:
            return []
        end_at = order.order_date or order.created_at
        if not end_at:
            return []
        start_at = end_at - timedelta(days=lookback_days)
        return (
            self.db.query(Event)
            .filter(
                Event.customer_id == order.customer_id,
                Event.timestamp >= start_at,
                Event.timestamp <= end_at,
            )
            .order_by(Event.timestamp.asc(), Event.created_at.asc())
            .all()
        )

    @staticmethod
    def _weights(model: str, count: int) -> list[float]:
        if count <= 0:
            return []
        if model == "first_touch":
            return [1.0] + [0.0] * (count - 1)
        if model == "last_touch":
            return [0.0] * (count - 1) + [1.0]
        if model == "linear":
            return [1.0 / count] * count
        if model == "position_based_40_20_40":
            if count == 1:
                return [1.0]
            if count == 2:
                return [0.5, 0.5]
            middle_weight = 0.2 / (count - 2)
            return [0.4] + [middle_weight] * (count - 2) + [0.4]
        return [1.0 / count] * count

    def calculate_order_attribution(self,
                                    order_ref: str,
                                    models: list[str] | None = None,
                                    lookback_days: int = 30) -> dict[str, Any]:
        order = self._order(order_ref)
        if not order:
            return {"status": "not_found", "order_ref": order_ref}

        touchpoints = self.touchpoints_for_order(order, lookback_days=lookback_days)
        if not touchpoints:
            return {
                "status": "no_touchpoints",
                "order_id": order.id,
                "shopify_order_id": order.shopify_order_id,
                "models": {},
                "write_enabled": self.write_enabled,
            }

        total_value = float(order.total_amount or 0)
        model_names = models or list(DEFAULT_MODELS)
        output: dict[str, list[dict[str, Any]]] = {}

        for model in model_names:
            weights = self._weights(model, len(touchpoints))
            rows: list[dict[str, Any]] = []
            for idx, event in enumerate(touchpoints):
                source = self._event_source(event)
                campaign_id, campaign_name = self._event_campaign(event)
                event_data = event.event_data or {}
                weight = weights[idx]
                touch_type = "assist"
                if idx == 0:
                    touch_type = "first"
                if idx == len(touchpoints) - 1:
                    touch_type = "last" if touch_type != "first" else "first_last"
                row = {
                    "event_id": event.id,
                    "source": source,
                    "campaign_id": campaign_id,
                    "campaign_name": campaign_name,
                    "touch_type": touch_type,
                    "attributed_percentage": round(weight * 100, 4),
                    "attributed_value": round(total_value * weight, 2),
                    "gclid": event_data.get("gclid"),
                    "fbclid": event_data.get("fbclid"),
                    "fbp": event_data.get("fbp"),
                    "fbc": event_data.get("fbc"),
                }
                rows.append(row)
                if self.write_enabled:
                    existing = (
                        self.db.query(OrderTouchpointAttribution)
                        .filter(
                            OrderTouchpointAttribution.order_id == order.id,
                            OrderTouchpointAttribution.touchpoint_event_id == event.id,
                            OrderTouchpointAttribution.attribution_model == model,
                        )
                        .first()
                    )
                    if not existing:
                        existing = OrderTouchpointAttribution(
                            order_id=order.id,
                            shopify_order_id=order.shopify_order_id,
                            customer_id=order.customer_id,
                            touchpoint_event_id=event.id,
                            attribution_model=model,
                            source=source,
                            touch_type=touch_type,
                        )
                        self.db.add(existing)
                    existing.campaign_id = campaign_id
                    existing.campaign_name = campaign_name
                    existing.gclid = row["gclid"]
                    existing.fbclid = row["fbclid"]
                    existing.fbp = row["fbp"]
                    existing.fbc = row["fbc"]
                    existing.attributed_percentage = row["attributed_percentage"]
                    existing.attributed_value = row["attributed_value"]
                    existing.lookback_days = lookback_days
            output[model] = rows

        if self.write_enabled:
            self.db.commit()

        return {
            "status": "ok",
            "order_id": order.id,
            "shopify_order_id": order.shopify_order_id,
            "total_value": total_value,
            "touchpoint_count": len(touchpoints),
            "write_enabled": self.write_enabled,
            "models": output,
        }
