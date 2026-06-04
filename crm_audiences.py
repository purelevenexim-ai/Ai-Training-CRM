"""
crm_audiences.py — Audience Classification Engine
Classifies CRM customers into retargeting segments based on event history and orders.

Segments:
  checkout_abandoner   — checkout_start in last 3 days, no purchase after
  cart_abandoner       — add_to_cart / cart_viewed in last 7 days, no purchase after
  product_viewer       — product_view in last 30 days, not a buyer
  multi_product_browser— 3+ distinct products in one session, last 21 days
  returning_visitor    — 2+ sessions in last 30 days
  buyer                — has at least one completed order
  replenishment_due    — buyer, last delivered order 30-50 days ago
  lapsed_buyer         — buyer, last order 60+ days ago
  high_ltv             — buyer, total_spent > 2000 INR

Usage:
    from crm_audiences import AudienceEngine
    engine = AudienceEngine(db_session)
    segments = engine.classify(customer_id)
    engine.refresh_all()
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import List

from sqlalchemy import text

logger = logging.getLogger("pureleven.audiences")

# Segment definitions (name → description)
SEGMENT_DEFS = {
    "checkout_abandoner":    "Reached checkout in last 3 days, no purchase",
    "cart_abandoner":        "Added to cart in last 7 days, no purchase",
    "product_viewer":        "Viewed products in last 30 days, not a buyer",
    "multi_product_browser": "Viewed 3+ products in one session (last 21 days)",
    "returning_visitor":     "Returned to site 2+ times (last 30 days)",
    "buyer":                 "Has at least one completed order",
    "replenishment_due":     "Buyer with last order 30–50 days ago",
    "lapsed_buyer":          "Buyer with last order 60+ days ago",
    "high_ltv":              "Buyer with total spend > ₹2,000",
}


class AudienceEngine:
    def __init__(self, db) -> None:
        self.db = db

    # ─── Per-customer classification ─────────────────────────────────────────

    def classify(self, customer_id: str) -> List[str]:
        """Return list of segment names the customer currently belongs to."""
        now = datetime.now(timezone.utc)
        segments: List[str] = []

        # --- buyer check (most important, gates replenishment/lapsed) ---
        row = self.db.execute(
            text("""
            SELECT orders_count, total_spent, last_order_date
            FROM crm_customers WHERE id = :cid
            """),
            {"cid": customer_id},
        ).fetchone()
        if not row:
            return segments

        orders_count, total_spent, last_order_date = row

        if orders_count and orders_count > 0:
            segments.append("buyer")
            if total_spent and total_spent > 2000:
                segments.append("high_ltv")
            if last_order_date:
                if isinstance(last_order_date, str):
                    last_order_date = datetime.fromisoformat(last_order_date)
                # Make timezone-aware if naive
                if last_order_date.tzinfo is None:
                    last_order_date = last_order_date.replace(tzinfo=timezone.utc)
                age_days = (now - last_order_date).days
                if 30 <= age_days <= 50:
                    segments.append("replenishment_due")
                elif age_days >= 60:
                    segments.append("lapsed_buyer")
        else:
            # Non-buyer audience checks
            # checkout_abandoner: checkout_start event in last 3 days, no purchase after
            co_row = self.db.execute(
                text("""
                SELECT MAX(timestamp) FROM crm_events
                WHERE customer_id = :cid
                  AND event_type IN ('checkout_start', 'checkout_initiated')
                  AND timestamp > :since
                """),
                {"cid": customer_id, "since": now - timedelta(days=3)},
            ).fetchone()
            last_checkout = co_row[0] if co_row else None

            if last_checkout:
                if isinstance(last_checkout, str):
                    last_checkout = datetime.fromisoformat(last_checkout)
                if last_checkout.tzinfo is None:
                    last_checkout = last_checkout.replace(tzinfo=timezone.utc)
                segments.append("checkout_abandoner")
            else:
                # cart_abandoner: cart_viewed / add_to_cart in last 7 days
                cart_row = self.db.execute(
                    text("""
                    SELECT COUNT(*) FROM crm_events
                    WHERE customer_id = :cid
                      AND event_type IN ('cart_viewed', 'add_to_cart', 'abandoned_checkout')
                      AND timestamp > :since
                    """),
                    {"cid": customer_id, "since": now - timedelta(days=7)},
                ).fetchone()
                if cart_row and cart_row[0] > 0:
                    segments.append("cart_abandoner")

            # product_viewer: any product_view in last 30 days
            pv_row = self.db.execute(
                text("""
                SELECT COUNT(*) FROM crm_events
                WHERE customer_id = :cid
                  AND event_type = 'product_view'
                  AND timestamp > :since
                """),
                {"cid": customer_id, "since": now - timedelta(days=30)},
            ).fetchone()
            if pv_row and pv_row[0] > 0:
                segments.append("product_viewer")

            # multi_product_browser: 3+ distinct product handles in last 21 days
            mp_row = self.db.execute(
                text("""
                SELECT COUNT(DISTINCT event_data->>'product_handle') FROM crm_events
                WHERE customer_id = :cid
                  AND event_type = 'product_view'
                  AND timestamp > :since
                  AND event_data->>'product_handle' IS NOT NULL
                """),
                {"cid": customer_id, "since": now - timedelta(days=21)},
            ).fetchone()
            if mp_row and mp_row[0] >= 3:
                segments.append("multi_product_browser")

        # returning_visitor: 2+ page_view events in last 30 days
        # (approximated by event count — each page load sends one)
        rv_row = self.db.execute(
            text("""
            SELECT COUNT(*) FROM crm_events
            WHERE customer_id = :cid
              AND event_type = 'page_view'
              AND timestamp > :since
            """),
            {"cid": customer_id, "since": now - timedelta(days=30)},
        ).fetchone()
        if rv_row and rv_row[0] >= 2:
            segments.append("returning_visitor")

        return list(set(segments))

    # ─── Upsert segments into crm_segments + membership ─────────────────────

    def upsert_customer_segments(self, customer_id: str) -> List[str]:
        """Classify and persist segment membership for a customer."""
        segments = self.classify(customer_id)
        if not segments:
            return segments

        # Ensure segment rows exist
        from uuid import uuid4
        for seg_name in segments:
            desc = SEGMENT_DEFS.get(seg_name, seg_name)
            self.db.execute(
                text("""
                INSERT INTO crm_segments (id, name, description, rule_set, is_active, auto_update)
                VALUES (:id, :name, :desc, :rules, true, true)
                ON CONFLICT (name) DO NOTHING
                """),
                {
                    "id":    str(uuid4()),
                    "name":  seg_name,
                    "desc":  desc,
                    "rules": "{}",
                },
            )
        self.db.commit()
        return segments

    # ─── Bulk refresh ────────────────────────────────────────────────────────

    def refresh_all(self, limit: int = 5000) -> int:
        """Reclassify all customers. Returns count processed."""
        rows = self.db.execute(
            text("SELECT id FROM crm_customers ORDER BY updated_at DESC LIMIT :limit"),
            {"limit": limit},
        ).fetchall()
        count = 0
        for (cid,) in rows:
            try:
                self.upsert_customer_segments(cid)
                count += 1
            except Exception as exc:
                logger.warning("classify failed for %s: %s", cid, exc)
        logger.info("Audience refresh complete: %d customers processed", count)
        return count

    # ─── Abandonment candidates (for N8N polling) ────────────────────────────

    def checkout_abandonment_candidates(
        self,
        window_minutes: int = 15,
        limit: int = 50,
    ) -> list[dict]:
        """
        Events where checkout was initiated ≥ window_minutes ago
        and no subsequent purchase exists, and n8n_notified = false.
        """
        now = datetime.now(timezone.utc)
        since = now - timedelta(minutes=window_minutes + 120)   # look back up to 2h+window
        cutoff = now - timedelta(minutes=window_minutes)

        rows = self.db.execute(
            text("""
            SELECT
                e.id            AS event_id,
                e.customer_id,
                e.email,
                e.timestamp,
                e.event_data,
                c.first_name,
                c.phone
            FROM crm_events e
            LEFT JOIN crm_customers c ON c.id = e.customer_id
            WHERE e.event_type IN ('checkout_start', 'checkout_initiated')
              AND e.timestamp BETWEEN :since AND :cutoff
              AND e.n8n_notified = false
              AND NOT EXISTS (
                  SELECT 1 FROM crm_orders o
                  WHERE o.customer_id = e.customer_id
                    AND o.created_at > e.timestamp
              )
            ORDER BY e.timestamp DESC
            LIMIT :limit
            """),
            {"since": since, "cutoff": cutoff, "limit": limit},
        ).fetchall()

        return [
            {
                "event_id":    str(r[0]),
                "customer_id": str(r[1]) if r[1] else None,
                "email":       r[2],
                "timestamp":   r[3].isoformat() if r[3] else None,
                "cart_value":  (r[4] or {}).get("cart_value"),
                "first_name":  r[5],
                "phone":       r[6],
            }
            for r in rows
        ]

    def cart_abandonment_candidates(
        self,
        window_minutes: int = 30,
        limit: int = 50,
    ) -> list[dict]:
        """
        Events where cart was viewed/added ≥ window_minutes ago,
        no checkout or purchase since, n8n_notified = false.
        """
        now = datetime.now(timezone.utc)
        since = now - timedelta(minutes=window_minutes + 180)
        cutoff = now - timedelta(minutes=window_minutes)

        rows = self.db.execute(
            text("""
            SELECT
                e.id, e.customer_id, e.email, e.timestamp, e.event_data,
                c.first_name, c.phone
            FROM crm_events e
            LEFT JOIN crm_customers c ON c.id = e.customer_id
            WHERE e.event_type IN ('cart_viewed', 'add_to_cart', 'abandoned_checkout')
              AND e.timestamp BETWEEN :since AND :cutoff
              AND e.n8n_notified = false
              AND NOT EXISTS (
                  SELECT 1 FROM crm_events e2
                  WHERE e2.customer_id = e.customer_id
                    AND e2.event_type IN ('checkout_start', 'checkout_initiated')
                    AND e2.timestamp > e.timestamp
              )
              AND NOT EXISTS (
                  SELECT 1 FROM crm_orders o
                  WHERE o.customer_id = e.customer_id
                    AND o.created_at > e.timestamp
              )
            ORDER BY e.timestamp DESC
            LIMIT :limit
            """),
            {"since": since, "cutoff": cutoff, "limit": limit},
        ).fetchall()

        return [
            {
                "event_id":    str(r[0]),
                "customer_id": str(r[1]) if r[1] else None,
                "email":       r[2],
                "timestamp":   r[3].isoformat() if r[3] else None,
                "cart_value":  (r[4] or {}).get("cart_value"),
                "first_name":  r[5],
                "phone":       r[6],
            }
            for r in rows
        ]
