"""
Basil Commerce OS — Phase 4
routes/analytics.py

Dashboard KPI queries from event_logs + orders tables.
Endpoints:
  GET /api/analytics/summary?shop_domain=x&days=7   — KPI summary card
  GET /api/analytics/events?shop_domain=x&event=x   — paginated event stream
  GET /api/analytics/funnel?shop_domain=x&days=7    — add-to-cart → checkout → purchase funnel
  GET /api/analytics/revenue?shop_domain=x&days=30  — daily revenue timeseries
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Query

from app.services.attribution_service import AttributionService
from app.storage import get_db_connection

_attribution_svc = AttributionService()

router = APIRouter()


def _since(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


@router.get("/analytics/summary", summary="KPI summary card")
def analytics_summary(
    shop_domain: str,
    days: int = Query(default=7, ge=1, le=365),
) -> dict[str, Any]:
    since = _since(days)

    with get_db_connection() as conn:
        total_events = conn.execute(
            "SELECT COUNT(*) FROM event_logs WHERE shop_domain = ? AND created_at >= ?",
            (shop_domain, since),
        ).fetchone()[0]

        atc = conn.execute(
            "SELECT COUNT(*) FROM event_logs WHERE shop_domain = ? AND event_name = 'add_to_cart' AND created_at >= ?",
            (shop_domain, since),
        ).fetchone()[0]

        checkout = conn.execute(
            "SELECT COUNT(*) FROM event_logs WHERE shop_domain = ? AND event_name IN ('begin_checkout','initiate_checkout') AND created_at >= ?",
            (shop_domain, since),
        ).fetchone()[0]

        purchase = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(CAST(json_extract(event_data,'$.value') AS REAL)), 0) FROM event_logs WHERE shop_domain = ? AND event_name = 'purchase' AND created_at >= ?",
            (shop_domain, since),
        ).fetchone()
        purchase_count = purchase[0] or 0
        purchase_value = purchase[1] or 0

        unique_sessions = conn.execute(
            "SELECT COUNT(DISTINCT session_id) FROM event_logs WHERE shop_domain = ? AND created_at >= ?",
            (shop_domain, since),
        ).fetchone()[0]

    return {
        "shop_domain":       shop_domain,
        "period_days":       days,
        "total_events":      total_events,
        "unique_sessions":   unique_sessions,
        "add_to_cart":       atc,
        "begin_checkout":    checkout,
        "purchase_count":    purchase_count,
        "purchase_revenue":  round(purchase_value, 2),
        "checkout_rate":     round(checkout / atc * 100, 1) if atc else 0,
        "purchase_rate":     round(purchase_count / atc * 100, 1) if atc else 0,
    }


@router.get("/analytics/funnel", summary="ATC → checkout → purchase funnel")
def analytics_funnel(
    shop_domain: str,
    days: int = Query(default=7, ge=1, le=365),
) -> dict[str, Any]:
    since = _since(days)

    events = ["add_to_cart", "begin_checkout", "initiate_checkout", "purchase"]
    with get_db_connection() as conn:
        counts = {}
        for ev in events:
            row = conn.execute(
                "SELECT COUNT(DISTINCT session_id) FROM event_logs WHERE shop_domain = ? AND event_name = ? AND created_at >= ?",
                (shop_domain, ev, since),
            ).fetchone()
            counts[ev] = row[0] or 0

    checkout_sessions = max(counts["begin_checkout"], counts["initiate_checkout"])
    atc               = counts["add_to_cart"]

    return {
        "funnel": [
            {"step": "Add to Cart",     "sessions": atc},
            {"step": "Begin Checkout",  "sessions": checkout_sessions},
            {"step": "Purchase",        "sessions": counts["purchase"]},
        ],
        "atc_to_checkout_pct": round(checkout_sessions / atc * 100, 1) if atc else 0,
        "checkout_to_purchase_pct": round(counts["purchase"] / checkout_sessions * 100, 1) if checkout_sessions else 0,
    }


@router.get("/analytics/revenue", summary="Daily revenue timeseries")
def analytics_revenue(
    shop_domain: str,
    days: int = Query(default=30, ge=1, le=365),
) -> dict[str, Any]:
    since = _since(days)

    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT
              substr(created_at, 1, 10) AS day,
              COUNT(*)                                                                AS purchases,
              COALESCE(SUM(CAST(json_extract(event_data,'$.value') AS REAL)), 0)    AS revenue
            FROM event_logs
            WHERE shop_domain = ? AND event_name = 'purchase' AND created_at >= ?
            GROUP BY day
            ORDER BY day ASC
            """,
            (shop_domain, since),
        ).fetchall()

    return {
        "shop_domain": shop_domain,
        "period_days": days,
        "series":      [{"date": r["day"], "purchases": r["purchases"], "revenue": round(r["revenue"], 2)} for r in rows],
    }


@router.get("/analytics/events", summary="Paginated event stream")
def analytics_events(
    shop_domain: str,
    event_name:  str  = "",
    limit:       int  = Query(default=50, ge=1, le=200),
    offset:      int  = Query(default=0, ge=0),
) -> dict[str, Any]:
    with get_db_connection() as conn:
        if event_name:
            rows = conn.execute(
                "SELECT * FROM event_logs WHERE shop_domain = ? AND event_name = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (shop_domain, event_name, limit, offset),
            ).fetchall()
            total = conn.execute(
                "SELECT COUNT(*) FROM event_logs WHERE shop_domain = ? AND event_name = ?",
                (shop_domain, event_name),
            ).fetchone()[0]
        else:
            rows = conn.execute(
                "SELECT * FROM event_logs WHERE shop_domain = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (shop_domain, limit, offset),
            ).fetchall()
            total = conn.execute(
                "SELECT COUNT(*) FROM event_logs WHERE shop_domain = ?",
                (shop_domain,),
            ).fetchone()[0]

    return {
        "total":  total,
        "limit":  limit,
        "offset": offset,
        "events": [dict(r) for r in rows],
    }


@router.get("/analytics/roi", summary="Campaign ROI with attribution")
def analytics_roi(
    shop_domain: str = "rwxtic-gz.myshopify.com",
    days: int = Query(default=30, ge=1, le=365),
    campaign_id: str = "",
    model: str = Query(default="last_touch", pattern="^(last_touch|first_touch|linear|time_decay)$"),
) -> dict[str, Any]:
    """Return per-campaign attributed revenue and ROI."""
    roi = _attribution_svc.get_campaign_roi(
        campaign_id=campaign_id or None,
        days=days,
        model=model,
    )
    total_attributed = sum(r.get("total_attributed") or 0 for r in roi)
    return {
        "shop_domain":     shop_domain,
        "period_days":     days,
        "attribution_model": model,
        "total_attributed_revenue": round(total_attributed, 2),
        "campaigns":       roi,
    }


@router.get("/analytics/cohorts", summary="Weekly cohort retention")
def analytics_cohorts(
    shop_domain: str = "rwxtic-gz.myshopify.com",
    cohort_weeks: int = Query(default=8, ge=1, le=26),
) -> dict[str, Any]:
    """Cohort retention curves."""
    cohorts = _attribution_svc.get_cohort_retention(
        shop_domain=shop_domain,
        cohort_weeks=cohort_weeks,
    )
    return {
        "shop_domain":   shop_domain,
        "cohort_weeks":  cohort_weeks,
        "cohorts":       cohorts,
    }


@router.get("/analytics/clv", summary="Customer lifetime value")
def analytics_clv(
    shop_domain: str = "rwxtic-gz.myshopify.com",
    top_n: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    """Top customers by total lifetime revenue."""
    customers = _attribution_svc.get_customer_ltv(
        shop_domain=shop_domain,
        top_n=top_n,
    )
    total_ltv = sum(c.get("total_revenue") or 0 for c in customers)
    return {
        "shop_domain":    shop_domain,
        "customer_count": len(customers),
        "total_revenue":  round(total_ltv, 2),
        "avg_ltv":        round(total_ltv / len(customers), 2) if customers else 0,
        "customers":      customers,
    }
