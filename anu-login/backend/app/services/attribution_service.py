"""
app/services/attribution_service.py

ROI Attribution Service — links campaign touches to purchases.

Models:
  last_touch   — 100% credit to last campaign touch before purchase
  first_touch  — 100% credit to first campaign touch
  linear       — equal credit across all touches
  time_decay   — more credit to touches closer to purchase (40-20-40 simplification)

Usage:
    from app.services.attribution_service import AttributionService
    svc = AttributionService()
    svc.run_attribution(shop_domain="rwxtic-gz.myshopify.com", lookback_days=30)
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


class AttributionService:
    """Compute and store revenue attribution for email campaigns."""

    def run_attribution(
        self,
        shop_domain: str = "rwxtic-gz.myshopify.com",
        lookback_days: int = 30,
        model: str = "last_touch",
    ) -> dict[str, Any]:
        """
        Main entry: find orders placed within lookback_days and attribute them
        to campaign touches (sends, opens, clicks) within 7 days before the order.

        Returns a summary dict with attributed_orders, total_attributed_revenue.
        """
        since = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()

        with get_connection() as conn:
            # 1. Load all purchases from event_logs in window
            purchase_rows = conn.execute(
                """
                SELECT event_id, session_id, customer_id,
                       CAST(json_extract(event_data,'$.value') AS REAL) as revenue,
                       json_extract(event_data,'$.order_id') as order_id,
                       json_extract(event_data,'$.email') as email,
                       created_at
                FROM event_logs
                WHERE shop_domain = ?
                  AND event_name = 'purchase'
                  AND created_at >= ?
                """,
                (shop_domain, since),
            ).fetchall()

            # Also get orders from promotional_customers (Shopify order data)
            promo_orders = conn.execute(
                """
                SELECT pc.email, cs.sent_at, cs.opened_at, cs.clicked_at, cs.campaign_id,
                       pc.total_orders, pc.total_spent
                FROM campaign_sends cs
                JOIN promotional_customers pc ON pc.email = cs.email
                WHERE cs.sent_at >= ?
                """,
                (since,),
            ).fetchall()

            attributed = 0
            total_revenue = 0.0
            skipped = 0

            # 2. For each purchase event, find pre-purchase campaign touches
            for p_row in purchase_rows:
                order_email = p_row["email"]
                order_time  = p_row["created_at"]
                order_value = float(p_row["revenue"] or 0)
                order_id    = p_row["order_id"] or p_row["event_id"]

                if not order_email or order_value <= 0:
                    skipped += 1
                    continue

                # Find campaign sends to this email within 7 days before purchase
                window_start = (
                    datetime.fromisoformat(order_time.replace("Z", "+00:00"))
                    - timedelta(days=7)
                ).isoformat()

                touches = conn.execute(
                    """
                    SELECT cs.id, cs.campaign_id, cs.sent_at, cs.opened_at, cs.clicked_at,
                           pc.name as campaign_name
                    FROM campaign_sends cs
                    LEFT JOIN promotional_campaigns pc ON pc.id = cs.campaign_id
                    WHERE cs.email = ?
                      AND cs.sent_at >= ?
                      AND cs.sent_at <= ?
                    ORDER BY cs.sent_at ASC
                    """,
                    (order_email, window_start, order_time),
                ).fetchall()

                if not touches:
                    skipped += 1
                    continue

                # Apply attribution model
                credits = self._apply_model(touches, order_value, model)

                # Store attribution records
                for send_id, campaign_id, attribution_rev, touch_type in credits:
                    # Check if already attributed
                    exists = conn.execute(
                        "SELECT 1 FROM campaign_attribution WHERE order_id=? AND campaign_id=?",
                        (order_id, campaign_id),
                    ).fetchone()
                    if exists:
                        continue

                    # Compute days to convert
                    send_time = next(
                        (t["sent_at"] for t in touches if t["campaign_id"] == campaign_id), None
                    )
                    days_to_convert = None
                    if send_time:
                        try:
                            st = datetime.fromisoformat(send_time.replace("Z", "+00:00"))
                            pt = datetime.fromisoformat(order_time.replace("Z", "+00:00"))
                            days_to_convert = (pt - st).days
                        except Exception:
                            pass

                    conn.execute(
                        """
                        INSERT OR IGNORE INTO campaign_attribution
                          (id, campaign_id, campaign_type, order_id, customer_email,
                           order_revenue, attribution_model, attributed_revenue,
                           touch_type, days_to_convert, created_at)
                        VALUES (?, ?, 'promotional', ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(uuid.uuid4()),
                            campaign_id,
                            order_id,
                            order_email,
                            order_value,
                            model,
                            round(attribution_rev, 2),
                            touch_type,
                            days_to_convert,
                            _now(),
                        ),
                    )
                    total_revenue += attribution_rev
                    attributed += 1

        logger.info(
            "Attribution complete model=%s attributed=%d total_revenue=%.2f skipped=%d",
            model, attributed, total_revenue, skipped,
        )
        return {
            "model": model,
            "attributed_orders": attributed,
            "total_attributed_revenue": round(total_revenue, 2),
            "skipped": skipped,
            "computed_at": _now(),
        }

    def _apply_model(
        self,
        touches: list[Any],
        order_value: float,
        model: str,
    ) -> list[tuple[str, str, float, str]]:
        """
        Returns list of (send_id, campaign_id, attributed_revenue, touch_type).
        """
        if not touches:
            return []

        results = []

        if model == "last_touch":
            t = touches[-1]
            touch_type = "click" if t["clicked_at"] else ("open" if t["opened_at"] else "send")
            results.append((t["id"], t["campaign_id"], order_value, touch_type))

        elif model == "first_touch":
            t = touches[0]
            touch_type = "click" if t["clicked_at"] else ("open" if t["opened_at"] else "send")
            results.append((t["id"], t["campaign_id"], order_value, touch_type))

        elif model == "linear":
            per_touch = order_value / len(touches)
            for t in touches:
                touch_type = "click" if t["clicked_at"] else ("open" if t["opened_at"] else "send")
                results.append((t["id"], t["campaign_id"], per_touch, touch_type))

        elif model == "time_decay":
            # 40% first, 20% middle, 40% last (simplified)
            n = len(touches)
            if n == 1:
                credits = [1.0]
            elif n == 2:
                credits = [0.4, 0.6]
            else:
                middle_share = 0.2 / max(n - 2, 1)
                credits = [0.4] + [middle_share] * (n - 2) + [0.4]
                # Normalize to sum to 1
                total = sum(credits)
                credits = [c / total for c in credits]

            for i, t in enumerate(touches):
                credit = credits[i] if i < len(credits) else 0
                touch_type = "click" if t["clicked_at"] else ("open" if t["opened_at"] else "send")
                results.append((t["id"], t["campaign_id"], order_value * credit, touch_type))

        else:
            # Default: last touch
            t = touches[-1]
            results.append((t["id"], t["campaign_id"], order_value, "send"))

        return results

    def get_campaign_roi(
        self,
        campaign_id: str | None = None,
        days: int = 30,
        model: str = "last_touch",
    ) -> list[dict[str, Any]]:
        """Return ROI breakdown per campaign."""
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        with get_connection() as conn:
            params: list[Any] = [since]
            where = "WHERE ca.created_at >= ?"
            if campaign_id:
                where += " AND ca.campaign_id = ?"
                params.append(campaign_id)

            rows = conn.execute(
                f"""
                SELECT
                    ca.campaign_id,
                    pc.name AS campaign_name,
                    COUNT(DISTINCT ca.order_id) AS orders,
                    COUNT(DISTINCT ca.customer_email) AS customers,
                    SUM(ca.attributed_revenue) AS total_attributed,
                    AVG(ca.days_to_convert) AS avg_days_to_convert,
                    pc.total_recipients,
                    pc.total_sent,
                    pc.open_rate,
                    pc.click_rate
                FROM campaign_attribution ca
                LEFT JOIN promotional_campaigns pc ON pc.id = ca.campaign_id
                {where}
                GROUP BY ca.campaign_id
                ORDER BY total_attributed DESC
                """,
                params,
            ).fetchall()

        result = []
        for r in rows:
            d = dict(r)
            total_sent = d.get("total_sent") or 0
            d["roi_pct"] = (
                round(d["total_attributed"] / (total_sent * 0.5) * 100, 1)  # simplified: ₹0.5 per send cost
                if total_sent > 0 else 0
            )
            result.append(d)
        return result

    def get_cohort_retention(
        self,
        shop_domain: str = "rwxtic-gz.myshopify.com",
        cohort_weeks: int = 8,
    ) -> list[dict[str, Any]]:
        """
        Compute weekly cohort retention from event_logs.
        Returns list of {cohort_week, week_0, week_1, ..., week_N} retention %.
        """
        with get_connection() as conn:
            # Get first purchase date per customer (their cohort week)
            cohort_rows = conn.execute(
                """
                SELECT
                    customer_id,
                    json_extract(event_data,'$.email') as email,
                    DATE(MIN(created_at)) as first_purchase_date,
                    strftime('%Y-%W', MIN(created_at)) as cohort_week
                FROM event_logs
                WHERE shop_domain = ?
                  AND event_name = 'purchase'
                  AND customer_id IS NOT NULL
                GROUP BY COALESCE(customer_id, json_extract(event_data,'$.email'))
                ORDER BY first_purchase_date DESC
                LIMIT ?
                """,
                (shop_domain, cohort_weeks * 100),
            ).fetchall()

            # Group by cohort_week
            cohorts: dict[str, list[str]] = {}
            for r in cohort_rows:
                week = r["cohort_week"] or "unknown"
                cid = r["customer_id"] or r["email"] or ""
                if cid:
                    cohorts.setdefault(week, []).append(cid)

            results = []
            for week, customers in sorted(cohorts.items())[:cohort_weeks]:
                if not customers:
                    continue
                row: dict[str, Any] = {"cohort_week": week, "size": len(customers)}

                # Check retention for subsequent weeks (0-4)
                for wk_offset in range(5):
                    week_num = int(week.split("-")[1]) + wk_offset if "-" in week else 0
                    year = week.split("-")[0] if "-" in week else "2026"
                    from_iso = f"{year}-W{week_num:02d}-1"
                    try:
                        from_dt = datetime.strptime(from_iso, "%Y-W%W-%w")
                        to_dt = from_dt + timedelta(days=7)
                        retained = conn.execute(
                            f"""
                            SELECT COUNT(DISTINCT COALESCE(customer_id,'')) as cnt
                            FROM event_logs
                            WHERE event_name = 'purchase'
                              AND shop_domain = ?
                              AND COALESCE(customer_id,'') IN ({','.join('?'*len(customers))})
                              AND created_at >= ?
                              AND created_at < ?
                            """,
                            [shop_domain] + customers + [from_dt.isoformat(), to_dt.isoformat()],
                        ).fetchone()["cnt"]
                        pct = round(retained / len(customers) * 100, 1)
                        row[f"week_{wk_offset}"] = pct
                    except Exception:
                        row[f"week_{wk_offset}"] = 0
                results.append(row)

        return results

    def get_customer_ltv(
        self,
        shop_domain: str = "rwxtic-gz.myshopify.com",
        top_n: int = 100,
    ) -> list[dict[str, Any]]:
        """Compute basic LTV per customer from event_logs purchases."""
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    COALESCE(customer_id, json_extract(event_data,'$.email')) as cid,
                    json_extract(event_data,'$.email') as email,
                    COUNT(*) as purchase_count,
                    SUM(CAST(json_extract(event_data,'$.value') AS REAL)) as total_revenue,
                    MIN(created_at) as first_purchase,
                    MAX(created_at) as last_purchase
                FROM event_logs
                WHERE shop_domain = ?
                  AND event_name = 'purchase'
                  AND cid IS NOT NULL
                GROUP BY cid
                ORDER BY total_revenue DESC
                LIMIT ?
                """,
                (shop_domain, top_n),
            ).fetchall()
        return [dict(r) for r in rows]
