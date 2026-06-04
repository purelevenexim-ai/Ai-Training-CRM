"""
app/routes/review_journey.py

Review Journey API endpoints:

  POST /api/review-journey/orchestrate          — Daily orchestration (cron target)
  GET  /api/review-journey/overview             — Dashboard summary cards
  GET  /api/review-journey/customers            — Paginated customer list
  GET  /api/review-journey/messages             — Message send logs
  GET  /api/review-journey/analytics            — Funnel chart data
  POST /api/review-journey/confirm-review       — Mark customer as having reviewed
  POST /api/review-journey/load-csv             — Trigger CSV re-import (admin)
  GET  /api/review-journey/customer/{id}        — Single customer detail

Click-tracking for review links is handled by the existing /r endpoint in link_tracker.py.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.storage import get_db_connection
from app.review_journey_engine import (
    get_review_journey_cohort,
    send_review_stage,
    record_review_submission,
    _compute_customer_status,
    ReviewStageResult,
    REVIEW_JOURNEY_STAGES,
)

router = APIRouter()
logger = logging.getLogger(__name__)

SHOP_DOMAIN = "rwxtic-gz.myshopify.com"


# ─── Helper ───────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_dict(row: Any) -> dict:
    if row is None:
        return {}
    return dict(row)


# ─── 1. Master Orchestration ─────────────────────────────────────────────────

@router.post("/review-journey/orchestrate")
def orchestrate_review_journey(dry_run: bool = Query(default=False)):
    """
    Run all review journey stages for eligible customers today.
    Called by the daily cron (scripts/daily_review_orchestrate.sh) or manually.
    """
    results: list[dict] = []
    stage_summary: dict[str, dict] = {}

    with get_db_connection() as conn:
        for stage in REVIEW_JOURNEY_STAGES:
            cohort = get_review_journey_cohort(conn, SHOP_DOMAIN, stage)
            stage_summary[stage] = {"eligible": len(cohort), "sent": 0, "suppressed": 0, "errors": 0}

            for customer in cohort:
                result: ReviewStageResult = send_review_stage(
                    conn, customer, stage, channel="whatsapp", dry_run=dry_run
                )
                entry = {
                    "customer_id":   result.customer_id,
                    "phone":         result.phone,
                    "stage":         result.stage,
                    "template":      result.template_name,
                    "status":        result.status,
                    "message_id":    result.message_id,
                    "error":         result.error,
                }
                results.append(entry)

                if result.status in ("sent", "dry_run"):
                    stage_summary[stage]["sent"] += 1
                elif result.status == "suppressed":
                    stage_summary[stage]["suppressed"] += 1
                else:
                    stage_summary[stage]["errors"] += 1

    total_sent = sum(s["sent"] for s in stage_summary.values())
    logger.info(
        "Review journey orchestration complete — dry_run=%s sent=%d stages=%s",
        dry_run, total_sent, stage_summary,
    )

    return {
        "dry_run": dry_run,
        "total_sent": total_sent,
        "stage_summary": stage_summary,
        "results": results,
        "orchestrated_at": _now(),
    }


# ─── 2. Dashboard overview cards ─────────────────────────────────────────────

@router.get("/review-journey/overview")
def get_review_journey_overview():
    """
    Return high-level KPI cards for the Review Journey dashboard tab.
    """
    with get_db_connection() as conn:
        # Total customers in the review funnel (delivered, not suppressed)
        total = conn.execute(
            "SELECT COUNT(*) FROM journey_customers WHERE shop_domain=? AND delivery_status='delivered'",
            (SHOP_DOMAIN,)
        ).fetchone()[0]

        # Day 15 review requests sent
        review_requests_sent = conn.execute(
            "SELECT COUNT(*) FROM journey_customers WHERE shop_domain=? AND day15_sent=1",
            (SHOP_DOMAIN,)
        ).fetchone()[0]

        # Reviews submitted
        reviews_submitted = conn.execute(
            "SELECT COUNT(*) FROM journey_customers WHERE shop_domain=? AND review_submitted_at IS NOT NULL",
            (SHOP_DOMAIN,)
        ).fetchone()[0]

        # Review link clicks (via review_journey_events)
        review_clicks = conn.execute(
            """
            SELECT COUNT(*) FROM review_journey_events
            WHERE shop_domain=? AND event_type IN ('review_link_clicked','link_clicked')
              AND journey_stage = 'review_pure_day15'
            """,
            (SHOP_DOMAIN,)
        ).fetchone()[0]

        # Repeat purchases
        repeat_purchases = conn.execute(
            "SELECT COUNT(*) FROM journey_customers WHERE shop_domain=? AND repeat_purchase_triggered=1",
            (SHOP_DOMAIN,)
        ).fetchone()[0]

        # Cross-sell sent
        crosssell_sent = conn.execute(
            "SELECT COUNT(*) FROM journey_customers WHERE shop_domain=? AND crosssell_day18_sent=1",
            (SHOP_DOMAIN,)
        ).fetchone()[0]

        # Replenishment sent
        replenishment_sent = conn.execute(
            "SELECT COUNT(*) FROM journey_customers WHERE shop_domain=? AND replenishment_day45_sent=1",
            (SHOP_DOMAIN,)
        ).fetchone()[0]

        # VIP sent
        vip_sent = conn.execute(
            "SELECT COUNT(*) FROM journey_customers WHERE shop_domain=? AND vip_day75_sent=1",
            (SHOP_DOMAIN,)
        ).fetchone()[0]

        # Status breakdown
        status_rows = conn.execute(
            """
            SELECT customer_status, COUNT(*) as cnt
            FROM journey_customers WHERE shop_domain=? AND delivery_status='delivered'
            GROUP BY customer_status
            """,
            (SHOP_DOMAIN,)
        ).fetchall()
        status_breakdown = {r["customer_status"] or "cold": r["cnt"] for r in status_rows}

        # Conversion rates
        review_rate   = round(reviews_submitted / review_requests_sent * 100, 1) if review_requests_sent else 0
        click_rate    = round(review_clicks / review_requests_sent * 100, 1) if review_requests_sent else 0
        repeat_rate   = round(repeat_purchases / total * 100, 1) if total else 0

    return {
        "total_customers": total,
        "review_requests_sent": review_requests_sent,
        "review_clicks": review_clicks,
        "reviews_submitted": reviews_submitted,
        "crosssell_sent": crosssell_sent,
        "replenishment_sent": replenishment_sent,
        "vip_sent": vip_sent,
        "repeat_purchases": repeat_purchases,
        "review_rate_pct": review_rate,
        "click_rate_pct": click_rate,
        "repeat_purchase_rate_pct": repeat_rate,
        "status_breakdown": status_breakdown,
    }


# ─── 3. Customer list ─────────────────────────────────────────────────────────

@router.get("/review-journey/customers")
def list_review_customers(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=25, le=100),
    status: Optional[str] = Query(default=None),
    reviewed: Optional[bool] = Query(default=None),
    search: Optional[str] = Query(default=None, max_length=100),
):
    """Return paginated list of customers in the review journey funnel."""
    offset = (page - 1) * per_page
    params: list[Any] = [SHOP_DOMAIN]
    where_clauses = ["shop_domain = ?", "delivery_status = 'delivered'"]

    if status:
        where_clauses.append("customer_status = ?")
        params.append(status)

    if reviewed is True:
        where_clauses.append("review_submitted_at IS NOT NULL")
    elif reviewed is False:
        where_clauses.append("review_submitted_at IS NULL")

    if search:
        where_clauses.append("(name LIKE ? OR phone LIKE ? OR email LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])

    where_sql = " AND ".join(where_clauses)

    with get_db_connection() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM journey_customers WHERE {where_sql}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT id, name, phone, email,
                   purchased_product_name, purchased_product_handle,
                   customer_status, delivery_status, delivered_at,
                   day15_sent, day15_sent_at,
                   review_requested_at, review_submitted_at, review_submitted_channel,
                   review_rating, review_text,
                   crosssell_day18_sent, crosssell_day18_sent_at,
                   replenishment_day45_sent, replenishment_day45_sent_at,
                   vip_day75_sent, vip_day75_sent_at,
                   repeat_purchase_triggered, repeat_purchase_date,
                   engagement_score, is_responsive, google_review_status,
                   order_value_paise, shopify_order_id,
                   journey_started_at, created_at
            FROM journey_customers
            WHERE {where_sql}
            ORDER BY delivered_at DESC
            LIMIT ? OFFSET ?
            """,
            params + [per_page, offset],
        ).fetchall()

    customers = []
    for r in rows:
        c = dict(r)
        # Compute delivery day
        if c.get("delivered_at"):
            try:
                dt = datetime.fromisoformat(c["delivered_at"].replace("Z", "+00:00"))
                c["days_since_delivery"] = int(
                    (datetime.now(timezone.utc) - dt).total_seconds() / 86400
                )
            except Exception:
                c["days_since_delivery"] = None
        else:
            c["days_since_delivery"] = None
        c["order_value_inr"] = round(c.get("order_value_paise", 0) / 100, 2) if c.get("order_value_paise") else 0
        customers.append(c)

    return {
        "customers": customers,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total else 1,
    }


# ─── 4. Message logs ──────────────────────────────────────────────────────────

@router.get("/review-journey/messages")
def list_review_messages(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, le=200),
    stage: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    customer_id: Optional[str] = Query(default=None),
):
    """
    Return paginated message send logs for review journey stages.
    """
    offset = (page - 1) * per_page
    stages = ("review_pure_day15", "review_thanks_day18", "crosssell_day18",
               "replenishment_day45", "vip_day75")

    where_clauses = [f"jm.journey_stage IN ({','.join('?'*len(stages))})"]
    params: list[Any] = list(stages)

    if stage:
        where_clauses = ["jm.journey_stage = ?"]
        params = [stage]

    if status:
        where_clauses.append("jm.delivery_status = ?")
        params.append(status)

    if customer_id:
        where_clauses.append("jm.customer_id = ?")
        params.append(customer_id)

    where_sql = " AND ".join(where_clauses)

    with get_db_connection() as conn:
        total = conn.execute(
            f"SELECT COUNT(*) FROM journey_messages jm WHERE {where_sql}", params
        ).fetchone()[0]

        rows = conn.execute(
            f"""
            SELECT
                jm.id, jm.customer_id, jm.template_name, jm.journey_stage,
                jm.delivery_status, jm.sent_at, jm.opened_at, jm.clicked_at,
                jm.channel, jm.wabis_message_id,
                jc.name AS customer_name, jc.phone, jc.customer_status,
                jc.purchased_product_name, jc.review_submitted_at
            FROM journey_messages jm
            LEFT JOIN journey_customers jc ON jc.id = jm.customer_id
            WHERE {where_sql}
            ORDER BY jm.sent_at DESC
            LIMIT ? OFFSET ?
            """,
            params + [per_page, offset],
        ).fetchall()

    messages = [dict(r) for r in rows]

    return {
        "messages": messages,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": (total + per_page - 1) // per_page if total else 1,
    }


# ─── 5. Analytics / Funnel ────────────────────────────────────────────────────

@router.get("/review-journey/analytics")
def get_review_journey_analytics(days: int = Query(default=90, le=365)):
    """
    Return funnel metrics and time-series data for charting.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    with get_db_connection() as conn:
        # Funnel: delivered → review_requested → review_clicked → reviewed → repeat_purchase
        funnel = []
        funnel_steps = [
            ("Delivered",         "SELECT COUNT(*) FROM journey_customers WHERE shop_domain=? AND delivery_status='delivered' AND delivered_at >= ?", [SHOP_DOMAIN, since]),
            ("Review Requested",  "SELECT COUNT(*) FROM journey_customers WHERE shop_domain=? AND day15_sent=1 AND day15_sent_at >= ?", [SHOP_DOMAIN, since]),
            ("Review Link Click", "SELECT COUNT(*) FROM review_journey_events WHERE shop_domain=? AND event_type IN ('review_link_clicked','link_clicked') AND journey_stage='review_pure_day15' AND created_at >= ?", [SHOP_DOMAIN, since]),
            ("Review Submitted",  "SELECT COUNT(*) FROM journey_customers WHERE shop_domain=? AND review_submitted_at IS NOT NULL AND review_submitted_at >= ?", [SHOP_DOMAIN, since]),
            ("Repeat Purchase",   "SELECT COUNT(*) FROM journey_customers WHERE shop_domain=? AND repeat_purchase_triggered=1 AND repeat_purchase_date >= ?", [SHOP_DOMAIN, since]),
        ]
        for label, sql, p in funnel_steps:
            count = conn.execute(sql, p).fetchone()[0]
            funnel.append({"label": label, "count": count})

        # Daily messages sent (for line chart) — last 30 days
        daily_rows = conn.execute(
            """
            SELECT DATE(sent_at) as day, journey_stage, COUNT(*) as cnt
            FROM journey_messages
            WHERE journey_stage IN ('review_pure_day15','review_thanks_day18',
                  'crosssell_day18','replenishment_day45','vip_day75')
              AND sent_at >= ?
            GROUP BY DATE(sent_at), journey_stage
            ORDER BY day
            """,
            [(datetime.now(timezone.utc) - timedelta(days=30)).isoformat()],
        ).fetchall()

        daily_data: dict[str, dict[str, int]] = {}
        for r in daily_rows:
            day = r["day"]
            if day not in daily_data:
                daily_data[day] = {}
            daily_data[day][r["journey_stage"]] = r["cnt"]

        # Status distribution
        status_rows = conn.execute(
            """
            SELECT customer_status, COUNT(*) as cnt
            FROM journey_customers WHERE shop_domain=? AND delivery_status='delivered'
            GROUP BY customer_status ORDER BY cnt DESC
            """,
            (SHOP_DOMAIN,)
        ).fetchall()

        # Rating distribution
        rating_rows = conn.execute(
            """
            SELECT review_rating, COUNT(*) as cnt
            FROM journey_customers
            WHERE shop_domain=? AND review_rating IS NOT NULL
            GROUP BY review_rating ORDER BY review_rating
            """,
            (SHOP_DOMAIN,)
        ).fetchall()

        # Top products by purchase
        product_rows = conn.execute(
            """
            SELECT purchased_product_name, COUNT(*) as cnt
            FROM journey_customers WHERE shop_domain=? AND purchased_product_name IS NOT NULL
            GROUP BY purchased_product_name ORDER BY cnt DESC LIMIT 10
            """,
            (SHOP_DOMAIN,)
        ).fetchall()

    return {
        "funnel": funnel,
        "daily_messages": [
            {"date": d, **stages} for d, stages in sorted(daily_data.items())
        ],
        "status_distribution": [
            {"status": r["customer_status"] or "cold", "count": r["cnt"]}
            for r in status_rows
        ],
        "rating_distribution": [
            {"rating": r["review_rating"], "count": r["cnt"]}
            for r in rating_rows
        ],
        "top_products": [
            {"product": r["purchased_product_name"], "count": r["cnt"]}
            for r in product_rows
        ],
        "period_days": days,
    }


# ─── 6. Confirm review submitted ─────────────────────────────────────────────

class ConfirmReviewRequest(BaseModel):
    customer_id: str
    rating: int = 5
    review_text: str = ""
    channel: str = "google"


@router.post("/review-journey/confirm-review")
def confirm_review(body: ConfirmReviewRequest):
    """
    Called when a customer confirms they have submitted a Google review.
    Also triggered by GMB webhook when a new review is detected.
    """
    if not (1 <= body.rating <= 5):
        raise HTTPException(status_code=422, detail="Rating must be 1-5")

    with get_db_connection() as conn:
        customer = conn.execute(
            "SELECT id FROM journey_customers WHERE id = ?",
            (body.customer_id,)
        ).fetchone()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        record_review_submission(
            conn=conn,
            customer_id=body.customer_id,
            rating=body.rating,
            review_text=body.review_text,
            channel=body.channel,
        )

    return {"ok": True, "customer_id": body.customer_id, "rating": body.rating}


# ─── 7. Mark repeat purchase ─────────────────────────────────────────────────

class RepeatPurchaseRequest(BaseModel):
    customer_id: str
    order_id: Optional[str] = None
    order_value_inr: Optional[float] = None


@router.post("/review-journey/mark-repeat-purchase")
def mark_repeat_purchase(body: RepeatPurchaseRequest):
    """Mark that a customer has made a repeat purchase (called from Shopify webhook)."""
    with get_db_connection() as conn:
        customer = conn.execute(
            "SELECT id FROM journey_customers WHERE id = ?",
            (body.customer_id,)
        ).fetchone()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")

        now = _now()
        conn.execute(
            """
            UPDATE journey_customers
            SET repeat_purchase_triggered = 1,
                repeat_purchase_date = ?,
                customer_status = CASE
                    WHEN customer_status NOT IN ('purchased','vip') THEN 'purchased'
                    ELSE customer_status
                END,
                engagement_score = engagement_score + 30,
                updated_at = ?
            WHERE id = ?
            """,
            (now, now, body.customer_id),
        )

    return {"ok": True}


# ─── 8. Single customer detail ────────────────────────────────────────────────

@router.get("/review-journey/customer/{customer_id}")
def get_customer_detail(customer_id: str):
    with get_db_connection() as conn:
        customer = conn.execute(
            "SELECT * FROM journey_customers WHERE id = ?",
            (customer_id,)
        ).fetchone()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        c = dict(customer)

        messages = conn.execute(
            """
            SELECT * FROM journey_messages
            WHERE customer_id = ? AND journey_stage IN (
              'review_pure_day15','review_thanks_day18',
              'crosssell_day18','replenishment_day45','vip_day75'
            )
            ORDER BY sent_at DESC
            """,
            (customer_id,),
        ).fetchall()

        events = conn.execute(
            """
            SELECT * FROM review_journey_events
            WHERE customer_id = ?
            ORDER BY created_at DESC LIMIT 50
            """,
            (customer_id,),
        ).fetchall()

    c["order_value_inr"] = round(c.get("order_value_paise", 0) / 100, 2)
    return {
        "customer": c,
        "messages": [dict(m) for m in messages],
        "events": [dict(e) for e in events],
    }


# ─── 9. Send single stage (admin / testing) ──────────────────────────────────

class SendStageRequest(BaseModel):
    customer_id: str
    stage: str
    dry_run: bool = False


@router.post("/review-journey/send-stage")
def send_stage_manually(body: SendStageRequest):
    """Manually trigger a review journey stage for one customer (admin/testing)."""
    if body.stage not in REVIEW_JOURNEY_STAGES:
        raise HTTPException(status_code=422, detail=f"Unknown stage: {body.stage}")

    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM journey_customers WHERE id = ?",
            (body.customer_id,)
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Customer not found")

        result = send_review_stage(conn, dict(row), body.stage, dry_run=body.dry_run)

    return {
        "customer_id": result.customer_id,
        "stage": result.stage,
        "template": result.template_name,
        "status": result.status,
        "message_id": result.message_id,
        "error": result.error,
    }
