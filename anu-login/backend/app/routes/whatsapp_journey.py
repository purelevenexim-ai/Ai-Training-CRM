"""
Basil Commerce OS — Phase 5
routes/whatsapp_journey.py

WhatsApp journey management.
Handles:
  - Customer onboarding (upsert from Shopify order webhook)
  - Journey state inspection
  - Daily engagement score recalculation + decay
  - Cron-ready endpoint to advance customers through journey stages
  - Dashboard stats

Endpoints:
  POST /api/journey/customers/upsert         — create/update from Shopify order
  GET  /api/journey/customers/{phone}        — get customer journey state
  POST /api/journey/score/recalculate        — daily cron: decay + recalculate segments
  GET  /api/journey/cohorts/today            — customers ready for each stage today
  GET  /api/journey/stats                    — dashboard metrics
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, date, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.storage import get_db_connection

router = APIRouter()

# ─── Decay & scoring config ───────────────────────────────────────────────────

DAILY_DECAY_FACTOR = 0.98  # score *= 0.98 every day

SEGMENT_THRESHOLDS = {
    "vip": 80.0,
    "responsive": 40.0,
    "low": 5.0,
}

# Days since last engagement before forcing re-segmentation as non-responsive
NON_RESPONSIVE_DAYS = 30


# ─── Models ───────────────────────────────────────────────────────────────────

class OrderUpsertRequest(BaseModel):
    """Called from Shopify order.created / order.paid webhook or manual sync."""
    shop_domain: str = Field(min_length=1, max_length=200)
    shopify_order_id: str = Field(min_length=1, max_length=100)
    shopify_customer_id: str = ""
    phone: str = Field(min_length=7, max_length=20)
    name: str = ""
    email: str = ""
    order_value_paise: int = Field(default=0, ge=0)
    waybill_id: str = ""
    estimated_delivery_at: str = ""
    # Cumulative across all orders (pass from Shopify customer data)
    total_spent_paise: int = Field(default=0, ge=0)
    purchase_count: int = Field(default=1, ge=1)


class RecalculateRequest(BaseModel):
    shop_domain: str = Field(min_length=1, max_length=200)
    dry_run: bool = False  # if True, return changes without saving


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _days_since(iso_ts: str | None) -> float | None:
    if not iso_ts:
        return None
    try:
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        return delta.total_seconds() / 86400
    except ValueError:
        return None


def _calculate_segment(score: float) -> str:
    if score >= SEGMENT_THRESHOLDS["vip"]:
        return "vip"
    if score >= SEGMENT_THRESHOLDS["responsive"]:
        return "responsive"
    if score >= SEGMENT_THRESHOLDS["low"]:
        return "low"
    return "dormant"


def _normalize_phone(phone: str) -> str:
    return "".join(c for c in phone if c.isdigit())


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post(
    "/journey/customers/upsert",
    summary="Create or update a customer in the WhatsApp journey (from Shopify order)",
    status_code=status.HTTP_200_OK,
)
def upsert_journey_customer(payload: OrderUpsertRequest) -> dict[str, Any]:
    """
    Called when a new Shopify order is created.
    - If order already tracked → update waybill / delivery estimate
    - If new order → create journey customer at stage 'order_confirmed'
    """
    now = _now_iso()
    phone_normalized = _normalize_phone(payload.phone)

    with get_db_connection() as conn:
        # Check if this order already exists
        existing = conn.execute(
            "SELECT * FROM journey_customers WHERE shop_domain = ? AND shopify_order_id = ? LIMIT 1",
            (payload.shop_domain, payload.shopify_order_id),
        ).fetchone()

        if existing:
            # Update waybill / delivery info if changed
            conn.execute(
                """
                UPDATE journey_customers SET
                    waybill_id = COALESCE(NULLIF(?, ''), waybill_id),
                    estimated_delivery_at = COALESCE(NULLIF(?, ''), estimated_delivery_at),
                    name = COALESCE(NULLIF(?, ''), name),
                    total_spent_paise = ?,
                    purchase_count = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    payload.waybill_id or None,
                    payload.estimated_delivery_at or None,
                    payload.name or None,
                    payload.total_spent_paise,
                    payload.purchase_count,
                    now,
                    existing["id"],
                ),
            )
            return {"status": "updated", "customer_id": existing["id"], "shopify_order_id": payload.shopify_order_id}

        # New customer / new order
        customer_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO journey_customers (
                id, shop_domain, phone, name, email,
                shopify_customer_id, shopify_order_id,
                waybill_id, estimated_delivery_at, order_value_paise,
                delivery_status, journey_stage, journey_started_at,
                engagement_score, is_responsive, do_not_message,
                whatsapp_subscription_status, google_review_status,
                customer_segment, total_spent_paise, purchase_count,
                created_at, updated_at
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?,
                'pending', 'order_confirmed', ?,
                0.0, 0, 0,
                'subscribed', 'not_submitted',
                'new', ?, ?,
                ?, ?
            )
            """,
            (
                customer_id,
                payload.shop_domain,
                phone_normalized,
                payload.name or None,
                payload.email or None,
                payload.shopify_customer_id or None,
                payload.shopify_order_id,
                payload.waybill_id or None,
                payload.estimated_delivery_at or None,
                payload.order_value_paise,
                now,
                payload.total_spent_paise,
                payload.purchase_count,
                now,
                now,
            ),
        )

    return {
        "status": "created",
        "customer_id": customer_id,
        "phone": phone_normalized,
        "shopify_order_id": payload.shopify_order_id,
        "journey_stage": "order_confirmed",
    }


@router.get(
    "/journey/customers/{phone}",
    summary="Get customer WhatsApp journey state by phone number",
    status_code=status.HTTP_200_OK,
)
def get_customer_journey(
    phone: str,
    shop_domain: str = Query(..., min_length=1),
) -> dict[str, Any]:
    normalized = _normalize_phone(phone)
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM journey_customers
            WHERE shop_domain = ? AND (phone = ? OR phone = ?)
            ORDER BY created_at DESC LIMIT 10
            """,
            (shop_domain, phone, normalized),
        ).fetchall()

    if not rows:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found")

    # Return all orders for this customer
    customers = []
    for row in rows:
        c = dict(row)
        c["days_since_order"] = _days_since(c.get("journey_started_at"))
        c["days_since_delivery"] = _days_since(c.get("delivered_at"))
        c["days_since_engagement"] = _days_since(c.get("last_engagement_at"))
        customers.append(c)

    return {"phone": phone, "count": len(customers), "orders": customers}


@router.post(
    "/journey/score/recalculate",
    summary="Daily cron: apply score decay and re-segment all customers",
    status_code=status.HTTP_200_OK,
)
def recalculate_scores(payload: RecalculateRequest) -> dict[str, Any]:
    """
    Run once daily (12:01am IST).
    1. Apply engagement score decay: score *= 0.98
    2. Re-calculate customer_segment from new score
    3. Mark is_responsive=False for customers silent > 30 days
    4. Return stats on segment distribution
    """
    now = _now_iso()
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=NON_RESPONSIVE_DAYS)).isoformat()

    with get_db_connection() as conn:
        # Fetch all active customers (not unsubscribed)
        rows = conn.execute(
            """
            SELECT id, engagement_score, customer_segment, is_responsive,
                   last_engagement_at, do_not_message
            FROM journey_customers
            WHERE shop_domain = ? AND whatsapp_subscription_status != 'unsubscribed'
            """,
            (payload.shop_domain,),
        ).fetchall()

        segment_counts: dict[str, int] = {"vip": 0, "responsive": 0, "low": 0, "dormant": 0}
        changes: list[dict[str, Any]] = []

        for row in rows:
            customer_id = row["id"]
            old_score = float(row["engagement_score"])
            old_segment = row["customer_segment"]
            old_responsive = bool(row["is_responsive"])

            # Apply decay
            new_score = old_score * DAILY_DECAY_FACTOR
            new_segment = _calculate_segment(new_score)

            # Check if silent too long → mark non-responsive
            last_engagement = row["last_engagement_at"]
            gone_silent = (
                last_engagement is not None
                and last_engagement < cutoff_date
            )
            new_responsive = old_responsive and not gone_silent

            segment_counts[new_segment] = segment_counts.get(new_segment, 0) + 1

            has_changed = (
                abs(new_score - old_score) > 0.001
                or new_segment != old_segment
                or new_responsive != old_responsive
            )

            if has_changed:
                changes.append({
                    "id": customer_id,
                    "old_score": old_score,
                    "new_score": new_score,
                    "old_segment": old_segment,
                    "new_segment": new_segment,
                    "old_responsive": old_responsive,
                    "new_responsive": new_responsive,
                })

                if not payload.dry_run:
                    conn.execute(
                        """
                        UPDATE journey_customers SET
                            engagement_score = ?,
                            customer_segment = ?,
                            is_responsive = ?,
                            updated_at = ?
                        WHERE id = ?
                        """,
                        (new_score, new_segment, 1 if new_responsive else 0, now, customer_id),
                    )

    return {
        "status": "dry_run" if payload.dry_run else "ok",
        "shop_domain": payload.shop_domain,
        "total_customers": len(rows),
        "changes": len(changes),
        "segment_distribution": segment_counts,
        "ran_at": now,
    }


@router.get(
    "/journey/cohorts/today",
    summary="Get customers ready to receive a message today by journey stage",
    status_code=status.HTTP_200_OK,
)
def get_today_cohorts(
    shop_domain: str = Query(..., min_length=1),
) -> dict[str, Any]:
    """
    Returns cohorts of customers eligible for messaging at each journey stage today.
    Called by N8N daily orchestration workflow at 10am IST.

    Stage windows (days since delivered_at or journey_started_at):
      day2:  2-3 days since order (in_transit)
      day5:  0-1 days since delivered
      day15: 10-14 days since delivered, not yet reviewed, is_responsive
      day30: 28-32 days since delivered, is_responsive, no recent purchase
      day60: 58-62 days since delivered, is_responsive
      day75: 73-77 days since delivered, no recent purchase
      day95: 93-97 days since delivered
    """
    now_dt = datetime.now(timezone.utc)

    def _window(days_min: int, days_max: int, ts_col: str, extra_where: str = "") -> list[dict[str, Any]]:
        cutoff_min = (now_dt - timedelta(days=days_max)).isoformat()
        cutoff_max = (now_dt - timedelta(days=days_min)).isoformat()
        sql = f"""
            SELECT id, phone, name, shopify_order_id, shopify_customer_id,
                   engagement_score, customer_segment, is_responsive,
                   order_value_paise, waybill_id, journey_stage,
                   delivered_at, journey_started_at, do_not_message
            FROM journey_customers
            WHERE shop_domain = ?
              AND do_not_message = 0
              AND whatsapp_subscription_status = 'subscribed'
              AND {ts_col} >= ? AND {ts_col} <= ?
              {extra_where}
        """
        rows = conn.execute(sql, (shop_domain, cutoff_min, cutoff_max)).fetchall()
        return [dict(r) for r in rows]

    with get_db_connection() as conn:
        cohorts = {
            "day2_in_transit": _window(
                1, 4, "journey_started_at",
                "AND day2_sent = 0 AND delivery_status NOT IN ('delivered', 'delivery_failed')",
            ),
            "day5_delivered": _window(
                0, 2, "delivered_at",
                "AND day5_sent = 0",
            ),
            "day15_review": _window(
                10, 16, "delivered_at",
                "AND day15_sent = 0 AND is_responsive = 1 AND google_review_status != 'submitted'",
            ),
            "day30_upsell": _window(
                28, 33, "delivered_at",
                "AND day30_sent = 0 AND is_responsive = 1",
            ),
            "day60_corporate": _window(
                58, 63, "delivered_at",
                "AND day60_sent = 0",
            ),
            "day75_loyalty": _window(
                73, 78, "delivered_at",
                "AND day75_sent = 0 AND is_responsive = 1",
            ),
            "day95_rfm": _window(
                93, 98, "delivered_at",
                "AND day95_sent = 0",
            ),
        }

    return {
        "shop_domain": shop_domain,
        "as_of": now_dt.isoformat(),
        "cohorts": {k: {"count": len(v), "customers": v} for k, v in cohorts.items()},
    }


@router.post(
    "/journey/messages/log",
    summary="Log a message that was sent via Wabis (called by N8N after send)",
    status_code=status.HTTP_200_OK,
)
def log_message_sent(
    customer_id: str,
    template_name: str,
    journey_stage: str,
    wabis_message_id: str = "",
    variables: dict[str, Any] = {},
) -> dict[str, Any]:
    """
    After N8N sends a message via Wabis, it calls this endpoint to:
    1. Log the message in journey_messages
    2. Set the dayX_sent = 1 and dayX_sent_at = now flags on the customer
    """
    now = _now_iso()
    msg_id = str(uuid.uuid4())

    # Map template/stage to the sent-flag column
    stage_sent_col = {
        "day1": ("day1_sent", "day1_sent_at"),
        "order_confirmed": ("day1_sent", "day1_sent_at"),
        "day2": ("day2_sent", "day2_sent_at"),
        "in_transit": ("day2_sent", "day2_sent_at"),
        "day5": ("day5_sent", "day5_sent_at"),
        "delivered": ("day5_sent", "day5_sent_at"),
        "day15": ("day15_sent", "day15_sent_at"),
        "review": ("day15_sent", "day15_sent_at"),
        "day30": ("day30_sent", "day30_sent_at"),
        "upsell": ("day30_sent", "day30_sent_at"),
        "day60": ("day60_sent", "day60_sent_at"),
        "corporate": ("day60_sent", "day60_sent_at"),
        "day75": ("day75_sent", "day75_sent_at"),
        "loyalty": ("day75_sent", "day75_sent_at"),
        "day95": ("day95_sent", "day95_sent_at"),
        "rfm": ("day95_sent", "day95_sent_at"),
    }.get(journey_stage)

    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO journey_messages
              (id, customer_id, template_name, journey_stage,
               wabis_message_id, delivery_status, variables_json, sent_at, created_at)
            VALUES (?, ?, ?, ?, ?, 'sent', ?, ?, ?)
            """,
            (
                msg_id, customer_id, template_name, journey_stage,
                wabis_message_id or None,
                json.dumps(variables, ensure_ascii=True),
                now, now,
            ),
        )

        if stage_sent_col:
            flag_col, ts_col = stage_sent_col
            conn.execute(
                f"UPDATE journey_customers SET {flag_col} = 1, {ts_col} = ?, updated_at = ? WHERE id = ?",
                (now, now, customer_id),
            )

    return {"status": "ok", "message_id": msg_id, "customer_id": customer_id}


@router.get(
    "/journey/stats",
    summary="Dashboard: journey funnel + engagement stats",
    status_code=status.HTTP_200_OK,
)
def journey_stats(
    shop_domain: str = Query(..., min_length=1),
) -> dict[str, Any]:
    with get_db_connection() as conn:
        total = conn.execute(
            "SELECT COUNT(*) as n FROM journey_customers WHERE shop_domain = ?",
            (shop_domain,),
        ).fetchone()["n"]

        subscribed = conn.execute(
            "SELECT COUNT(*) as n FROM journey_customers WHERE shop_domain = ? AND whatsapp_subscription_status = 'subscribed'",
            (shop_domain,),
        ).fetchone()["n"]

        segments = conn.execute(
            "SELECT customer_segment, COUNT(*) as n FROM journey_customers WHERE shop_domain = ? GROUP BY customer_segment",
            (shop_domain,),
        ).fetchall()

        responsive = conn.execute(
            "SELECT COUNT(*) as n FROM journey_customers WHERE shop_domain = ? AND is_responsive = 1",
            (shop_domain,),
        ).fetchone()["n"]

        avg_score_row = conn.execute(
            "SELECT AVG(engagement_score) as avg FROM journey_customers WHERE shop_domain = ? AND whatsapp_subscription_status = 'subscribed'",
            (shop_domain,),
        ).fetchone()
        avg_score = round(float(avg_score_row["avg"] or 0), 2)

        delivered_count = conn.execute(
            "SELECT COUNT(*) as n FROM journey_customers WHERE shop_domain = ? AND delivery_status = 'delivered'",
            (shop_domain,),
        ).fetchone()["n"]

        reviewed = conn.execute(
            "SELECT COUNT(*) as n FROM journey_customers WHERE shop_domain = ? AND google_review_status = 'submitted'",
            (shop_domain,),
        ).fetchone()["n"]

        # Messages sent last 30 days
        cutoff_30d = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        messages_30d = conn.execute(
            """
            SELECT COUNT(*) as n FROM journey_messages jm
            JOIN journey_customers jc ON jm.customer_id = jc.id
            WHERE jc.shop_domain = ? AND jm.sent_at >= ?
            """,
            (shop_domain, cutoff_30d),
        ).fetchone()["n"]

        # Engagement events last 30 days
        eng_events_30d = conn.execute(
            """
            SELECT event_type, COUNT(*) as n, SUM(points_awarded) as pts
            FROM journey_engagement_events jee
            JOIN journey_customers jc ON jee.customer_id = jc.id
            WHERE jc.shop_domain = ? AND jee.created_at >= ?
            GROUP BY jee.event_type
            """,
            (shop_domain, cutoff_30d),
        ).fetchall()

    return {
        "shop_domain": shop_domain,
        "totals": {
            "all_customers": total,
            "subscribed": subscribed,
            "responsive": responsive,
            "delivered": delivered_count,
            "reviewed": reviewed,
        },
        "segments": {row["customer_segment"]: row["n"] for row in segments},
        "avg_engagement_score": avg_score,
        "messages_last_30d": messages_30d,
        "engagement_last_30d": {
            row["event_type"]: {"count": row["n"], "total_points": round(float(row["pts"] or 0), 2)}
            for row in eng_events_30d
        },
    }


@router.post(
    "/journey/customers/{customer_id}/mark-reviewed",
    summary="Mark customer as having submitted a Google review",
    status_code=status.HTTP_200_OK,
)
def mark_reviewed(customer_id: str) -> dict[str, Any]:
    now = _now_iso()
    with get_db_connection() as conn:
        row = conn.execute("SELECT id FROM journey_customers WHERE id = ?", (customer_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Customer not found")
        conn.execute(
            "UPDATE journey_customers SET google_review_status = 'submitted', updated_at = ? WHERE id = ?",
            (now, customer_id),
        )
        # Bonus points for review submission
        conn.execute(
            """
            INSERT INTO journey_engagement_events
              (id, customer_id, event_type, template_name, journey_stage,
               points_awarded, metadata_json, created_at)
            VALUES (?, ?, 'review_submitted', NULL, 'review', 50.0, '{}', ?)
            """,
            (str(uuid.uuid4()), customer_id, now),
        )
        # Update score directly
        conn.execute(
            "UPDATE journey_customers SET engagement_score = engagement_score + 50, updated_at = ? WHERE id = ?",
            (now, customer_id),
        )

    return {"status": "ok", "customer_id": customer_id, "google_review_status": "submitted", "bonus_points": 50}
