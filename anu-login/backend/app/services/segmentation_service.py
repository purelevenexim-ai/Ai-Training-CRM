"""
app/services/segmentation_service.py

Customer Segmentation Service (RFM + Engagement).

Computes:
  - RFM (Recency / Frequency / Monetary) scores
  - Segments: vip, high_value, regular, at_risk, inactive, new
  - Engagement label: active, warm, cold, dormant, inactive
  - Churn risk score (0–1)
  - CLV estimate (simple ARPU × avg lifespan)

Usage:
    from app.services.segmentation_service import SegmentationService
    svc = SegmentationService()
    svc.compute_all_segments(shop_domain="rwxtic-gz.myshopify.com")
    results = svc.query_segment("vip", limit=100)
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from app.storage import get_connection

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SegmentationService:

    def compute_all_segments(
        self,
        shop_domain: str = "rwxtic-gz.myshopify.com",
    ) -> dict[str, Any]:
        """
        Compute RFM segments for all known customers.

        Data sources (all optional — uses what's available):
          1. promotional_customers (Shopify sync)
          2. event_logs purchases
          3. journey_customers

        Writes/updates customer_segments table.
        Returns summary dict.
        """
        with get_connection() as conn:
            customers = self._load_customers(conn, shop_domain)

        if not customers:
            return {"segmented": 0, "message": "No customer data found"}

        now = datetime.now(timezone.utc)
        counts: dict[str, int] = {}
        written = 0

        with get_connection() as conn:
            for email, data in customers.items():
                segment = self._rfm_segment(data, now)
                engagement = self._engagement_label(data, now)
                churn_risk = self._churn_risk(data, now)
                clv = self._clv_estimate(data)

                recency = data.get("recency_days")
                counts[segment] = counts.get(segment, 0) + 1

                conn.execute(
                    """
                    INSERT INTO customer_segments
                      (id, email, shop_domain, rfm_segment, recency_days,
                       frequency, monetary_inr, engagement_label,
                       churn_risk_score, clv_estimate_inr, computed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(email) DO UPDATE SET
                        rfm_segment        = excluded.rfm_segment,
                        recency_days       = excluded.recency_days,
                        frequency          = excluded.frequency,
                        monetary_inr       = excluded.monetary_inr,
                        engagement_label   = excluded.engagement_label,
                        churn_risk_score   = excluded.churn_risk_score,
                        clv_estimate_inr   = excluded.clv_estimate_inr,
                        computed_at        = excluded.computed_at
                    """,
                    (
                        str(uuid.uuid4()),
                        email,
                        shop_domain,
                        segment,
                        recency,
                        data.get("frequency", 0),
                        data.get("monetary", 0.0),
                        engagement,
                        churn_risk,
                        clv,
                        _now(),
                    ),
                )
                written += 1

        logger.info("Segmentation complete: %d customers, distribution=%s", written, counts)
        return {"segmented": written, "distribution": counts, "computed_at": _now()}

    def _load_customers(
        self, conn: Any, shop_domain: str
    ) -> dict[str, dict[str, Any]]:
        """
        Aggregate customer data from multiple sources into a unified dict keyed by email.
        """
        customers: dict[str, dict[str, Any]] = {}

        # 1. promotional_customers (Shopify synced)
        try:
            rows = conn.execute(
                """
                SELECT email, total_orders, total_spent, last_order_date,
                       created_at, whatsapp_opted_in, email_opted_in
                FROM promotional_customers
                WHERE shop_domain = ?
                """,
                (shop_domain,),
            ).fetchall()
            for r in rows:
                email = (r["email"] or "").lower().strip()
                if not email:
                    continue
                customers[email] = {
                    "frequency": int(r["total_orders"] or 0),
                    "monetary":  float(r["total_spent"] or 0),
                    "last_order_date": r["last_order_date"],
                    "first_seen": r["created_at"],
                    "channels":  [],
                }
                if r["whatsapp_opted_in"]:
                    customers[email]["channels"].append("whatsapp")
                if r["email_opted_in"]:
                    customers[email]["channels"].append("email")
        except Exception as exc:
            logger.debug("No promotional_customers data: %s", exc)

        # 2. event_logs purchases (fills in or enriches)
        try:
            now_iso = _now()
            purchase_rows = conn.execute(
                """
                SELECT
                    json_extract(event_data,'$.email') as email,
                    COUNT(*) as freq,
                    SUM(CAST(json_extract(event_data,'$.value') AS REAL)) as monetary,
                    MAX(created_at) as last_purchase,
                    MIN(created_at) as first_purchase
                FROM event_logs
                WHERE shop_domain = ?
                  AND event_name = 'purchase'
                GROUP BY email
                """,
                (shop_domain,),
            ).fetchall()
            for r in purchase_rows:
                email = (r["email"] or "").lower().strip()
                if not email:
                    continue
                existing = customers.get(email, {})
                # Use max frequency/monetary
                freq = max(int(r["freq"] or 0), existing.get("frequency", 0))
                monetary = max(float(r["monetary"] or 0), existing.get("monetary", 0))
                customers[email] = {
                    **existing,
                    "frequency": freq,
                    "monetary":  monetary,
                    "last_order_date": r["last_purchase"] or existing.get("last_order_date"),
                    "first_seen": r["first_purchase"] or existing.get("first_seen"),
                }
        except Exception as exc:
            logger.debug("No event_logs purchase data: %s", exc)

        # Compute recency_days for each
        now = datetime.now(timezone.utc)
        for email, data in customers.items():
            lod = data.get("last_order_date")
            if lod:
                try:
                    dt = datetime.fromisoformat(lod.replace("Z", "+00:00"))
                    data["recency_days"] = (now - dt).days
                except Exception:
                    data["recency_days"] = None
            else:
                data["recency_days"] = None

        return customers

    def _rfm_segment(self, data: dict[str, Any], now: datetime) -> str:
        """Assign RFM segment based on recency, frequency, monetary."""
        recency  = data.get("recency_days")
        freq     = data.get("frequency", 0)
        monetary = data.get("monetary", 0.0)

        # VIP: High spend + frequent + recent
        if monetary >= 5000 and freq >= 5 and (recency is None or recency <= 60):
            return "vip"
        # High value: decent spend + multiple orders
        if monetary >= 2000 and freq >= 3:
            return "high_value"
        # At risk: used to buy but gone cold
        if freq >= 2 and recency is not None and recency > 90:
            return "at_risk"
        # Inactive: hasn't bought in 180+ days
        if recency is not None and recency > 180:
            return "inactive"
        # New: first time buyer
        if freq <= 1:
            return "new"
        # Regular: everything else
        return "regular"

    def _engagement_label(self, data: dict[str, Any], now: datetime) -> str:
        """Label based on recency."""
        recency = data.get("recency_days")
        if recency is None:
            return "inactive"
        if recency <= 30:
            return "active"
        if recency <= 60:
            return "warm"
        if recency <= 120:
            return "cold"
        if recency <= 180:
            return "dormant"
        return "inactive"

    def _churn_risk(self, data: dict[str, Any], now: datetime) -> float:
        """
        Simple churn risk score 0.0 (safe) to 1.0 (about to churn).
        Based on: recency days + frequency drop-off.
        """
        recency = data.get("recency_days")
        freq    = data.get("frequency", 0)

        if recency is None:
            return 0.5

        # Score increases with recency, decreases with frequency
        recency_score = min(recency / 180, 1.0)
        freq_dampener = 1.0 / max(freq, 1)  # more orders = less churn risk
        raw = recency_score * (0.7 + 0.3 * freq_dampener)
        return round(min(raw, 1.0), 4)

    def _clv_estimate(self, data: dict[str, Any]) -> float:
        """
        Simple CLV: avg order value × purchase frequency × 2 years.
        Capped at ₹50,000 to avoid outlier distortion.
        """
        freq     = max(data.get("frequency", 0), 0)
        monetary = max(data.get("monetary", 0.0), 0.0)

        if freq == 0 or monetary == 0:
            return 0.0

        aov = monetary / freq
        # Assume annual frequency capped at 12
        annual_freq = min(freq, 12)
        clv = aov * annual_freq * 2  # 2-year horizon
        return round(min(clv, 50000), 2)

    # ── Query helpers ──────────────────────────────────────────────────────────

    def query_segment(
        self,
        segment: str | None = None,
        engagement: str | None = None,
        churn_risk_min: float | None = None,
        limit: int = 500,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Query customer_segments with optional filters.
        Returns {customers: [...], total: int}.
        """
        with get_connection() as conn:
            conditions: list[str] = []
            params: list[Any] = []

            if segment:
                conditions.append("rfm_segment = ?")
                params.append(segment)
            if engagement:
                conditions.append("engagement_label = ?")
                params.append(engagement)
            if churn_risk_min is not None:
                conditions.append("churn_risk_score >= ?")
                params.append(churn_risk_min)

            where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

            total = conn.execute(
                f"SELECT COUNT(*) FROM customer_segments {where}", params
            ).fetchone()[0]

            rows = conn.execute(
                f"""
                SELECT * FROM customer_segments {where}
                ORDER BY clv_estimate_inr DESC
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset],
            ).fetchall()

        return {"customers": [dict(r) for r in rows], "total": total}

    def segment_summary(self) -> list[dict[str, Any]]:
        """Segment distribution with avg CLV."""
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT rfm_segment, engagement_label,
                       COUNT(*) as customer_count,
                       ROUND(AVG(clv_estimate_inr), 2) as avg_clv,
                       ROUND(AVG(churn_risk_score), 4) as avg_churn_risk,
                       MAX(computed_at) as last_computed
                FROM customer_segments
                GROUP BY rfm_segment
                ORDER BY customer_count DESC
                """
            ).fetchall()
        return [dict(r) for r in rows]

    def save_segment(
        self,
        name: str,
        description: str,
        filters: dict[str, Any],
    ) -> dict[str, Any]:
        """Save a named segment definition and compute its current count."""
        now = _now()
        seg_id = str(uuid.uuid4())

        # Compute count using filters
        result = self.query_segment(
            segment=filters.get("rfm_segment"),
            engagement=filters.get("engagement_label"),
            churn_risk_min=filters.get("churn_risk_min"),
            limit=10000,
        )
        count = result["total"]

        import json
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO saved_segments
                  (id, name, description, filters_json, customer_count, last_computed, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name           = excluded.name,
                    description    = excluded.description,
                    filters_json   = excluded.filters_json,
                    customer_count = excluded.customer_count,
                    last_computed  = excluded.last_computed,
                    updated_at     = excluded.updated_at
                """,
                (seg_id, name, description, json.dumps(filters), count, now, now, now),
            )

        return {"id": seg_id, "name": name, "customer_count": count, "created_at": now}

    def list_saved_segments(self) -> list[dict[str, Any]]:
        """List all saved segment definitions."""
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM saved_segments ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]
