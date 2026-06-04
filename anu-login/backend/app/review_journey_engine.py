"""
app/review_journey_engine.py

Post-purchase review journey orchestration engine.

Psychology sequence:
  Day 15: Appreciation → Review CTA (pure, no discount)
  Day 18: If reviewed  → Thank you + cross-sell  (review_thanks_day18)
           If NOT reviewed → Subtle cross-sell   (crosssell_day18)
  Day 45: Replenishment reminder
  Day 75: VIP exclusive offer (for engaged customers)

Public API:
  process_review_journey(conn, customer) → list[ReviewStageResult]
  send_review_stage(conn, customer, stage, channel, dry_run) → ReviewStageResult
  update_customer_status(conn, customer_id) → str
  record_review_event(conn, customer_id, event_type, meta) → None
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any

from app import wabis_client
from app.whatsapp_templates import build_message_vars

logger = logging.getLogger(__name__)


# ─── Review journey stage definitions ────────────────────────────────────────

REVIEW_JOURNEY_STAGES = [
    "review_pure_day15",    # Day 15 from delivery: appreciation + review CTA
    "review_thanks_day18",  # Day 18: thank you (if reviewed)
    "crosssell_day18",      # Day 18: cross-sell (if NOT reviewed)
    "replenishment_day45",  # Day 45: replenishment reminder
    "vip_day75",            # Day 75: VIP exclusive
]


# ─── Customer status scoring ──────────────────────────────────────────────────
# cold → warm → hot → purchased → vip
# Status auto-upgrades as engagement increases.

def _compute_customer_status(customer: dict[str, Any]) -> str:
    score = float(customer.get("engagement_score", 0))
    is_responsive = bool(customer.get("is_responsive"))
    has_reviewed = bool(customer.get("review_submitted_at"))
    repeat_purchase = bool(customer.get("repeat_purchase_triggered"))
    total_paise = int(customer.get("total_spent_paise", 0) or 0)
    order_paise = int(customer.get("order_value_paise", 0) or 0)

    if repeat_purchase and total_paise >= 100000:  # ₹1000+ total, repeat
        return "vip"
    if repeat_purchase:
        return "purchased"
    if has_reviewed or (is_responsive and score >= 40):
        return "hot"
    if is_responsive or score >= 20 or order_paise >= 80000:  # ₹800+
        return "warm"
    return "cold"


# ─── Suppression check ───────────────────────────────────────────────────────

def _should_send_review_stage(customer: dict[str, Any], stage: str) -> tuple[bool, str]:
    """Returns (ok, reason). ok=False means suppressed."""
    if customer.get("do_not_message"):
        return False, "do_not_message"
    sub = customer.get("whatsapp_subscription_status", "subscribed")
    if sub == "unsubscribed":
        return False, "unsubscribed"

    # Stage-specific idempotency checks
    sent_flags = {
        "review_pure_day15":  "day15_sent",
        "review_thanks_day18": "crosssell_day18_sent",
        "crosssell_day18":     "crosssell_day18_sent",
        "replenishment_day45": "replenishment_day45_sent",
        "vip_day75":           "vip_day75_sent",
    }
    flag = sent_flags.get(stage)
    if flag and customer.get(flag):
        return False, f"already_sent ({flag})"

    # Day 15 requires delivery
    if stage == "review_pure_day15":
        if customer.get("delivery_status") not in ("delivered",):
            return False, "not_yet_delivered"

    # Day 75 only for warm/hot/purchased/vip customers
    if stage == "vip_day75":
        status = customer.get("customer_status", "cold")
        if status == "cold":
            return False, "cold_customer_skip_vip"

    return True, ""


# ─── Time eligibility ─────────────────────────────────────────────────────────

def _days_since_delivery(customer: dict[str, Any]) -> int | None:
    delivered_at = customer.get("delivered_at")
    if not delivered_at:
        return None
    try:
        dt = datetime.fromisoformat(delivered_at.replace("Z", "+00:00"))
        return int((datetime.now(timezone.utc) - dt).total_seconds() / 86400)
    except (ValueError, AttributeError):
        return None


def _is_eligible_today(customer: dict[str, Any], stage: str) -> tuple[bool, str]:
    """Check if customer is in the correct delivery-day window for this stage."""
    days = _days_since_delivery(customer)
    if days is None:
        return False, "no_delivery_date"

    WINDOWS = {
        "review_pure_day15":   (13, 18),  # 13-18 days since delivery
        "review_thanks_day18": (16, 22),  # 16-22 days
        "crosssell_day18":     (16, 22),
        "replenishment_day45": (42, 50),  # 42-50 days
        "vip_day75":           (70, 82),  # 70-82 days
    }
    window = WINDOWS.get(stage)
    if not window:
        return True, ""  # Unknown stages pass through

    lo, hi = window
    if lo <= days <= hi:
        return True, ""
    if days < lo:
        return False, f"too_early (day {days}, need {lo})"
    return False, f"too_late (day {days}, window was {lo}-{hi})"


# ─── Result ──────────────────────────────────────────────────────────────────

@dataclass
class ReviewStageResult:
    customer_id: str
    phone: str
    stage: str
    template_name: str = ""
    status: str = ""       # sent | suppressed | dry_run | error
    message_id: str = ""
    error: str = ""
    channel: str = "whatsapp"
    points_awarded: float = 0.0


# ─── Core send ────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def send_review_stage(
    conn: Any,
    customer: dict[str, Any],
    stage: str,
    channel: str = "whatsapp",
    dry_run: bool = False,
) -> ReviewStageResult:
    """
    Send one review journey stage message to a customer.

    Checks:
      1. Suppression (do_not_message, unsubscribe, already_sent)
      2. Builds WhatsApp template vars
      3. Sends via Meta API (via wabis_client which routes to Meta first)
      4. Logs to journey_messages + review_journey_events
      5. Updates sent flag on journey_customers
      6. Updates customer_status
    """
    cid   = customer["id"]
    phone = customer.get("phone", "")

    # ── Suppression ──────────────────────────────────────────────────────────
    ok, reason = _should_send_review_stage(customer, stage)
    if not ok:
        return ReviewStageResult(cid, phone, stage, status="suppressed", error=reason)

    # ── Build template vars ──────────────────────────────────────────────────
    try:
        template_name, body_params, button_params = build_message_vars(stage, customer)
    except Exception as exc:
        logger.exception("Failed to build vars for %s at %s", cid, stage)
        return ReviewStageResult(cid, phone, stage, status="error", error=str(exc))

    if dry_run:
        return ReviewStageResult(
            cid, phone, stage, template_name=template_name,
            status="dry_run", message_id="dry_run",
        )

    # ── Send ─────────────────────────────────────────────────────────────────
    message_id = ""
    try:
        resp = wabis_client.send_template_message(
            phone=phone,
            template_name=template_name,
            body_params=body_params,
            button_params=button_params,
            shop_domain=customer.get("shop_domain") or "rwxtic-gz.myshopify.com",
        )
        message_id = wabis_client.extract_message_id(resp) or ""
    except Exception as exc:
        logger.error("Send failed for %s stage=%s: %s", cid, stage, exc)
        return ReviewStageResult(
            cid, phone, stage, template_name=template_name,
            status="error", error=str(exc),
        )

    now = _now()

    # ── Log to journey_messages ──────────────────────────────────────────────
    conn.execute(
        """
        INSERT INTO journey_messages
          (id, customer_id, template_name, journey_stage,
           wabis_message_id, delivery_status, variables_json,
           sent_at, created_at, channel)
        VALUES (?, ?, ?, ?, ?, 'sent', ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()), cid, template_name, stage,
            message_id or None,
            json.dumps({"body": body_params}),
            now, now, channel,
        ),
    )

    # ── Update sent flag on journey_customers ─────────────────────────────────
    flag_map = {
        "review_pure_day15":   ("day15_sent", "day15_sent_at", "review_requested_at"),
        "review_thanks_day18": ("crosssell_day18_sent", "crosssell_day18_sent_at", None),
        "crosssell_day18":     ("crosssell_day18_sent", "crosssell_day18_sent_at", None),
        "replenishment_day45": ("replenishment_day45_sent", "replenishment_day45_sent_at", None),
        "vip_day75":           ("vip_day75_sent", "vip_day75_sent_at", None),
    }
    flags = flag_map.get(stage)
    if flags:
        flag_col, ts_col, extra_col = flags
        if extra_col:
            conn.execute(
                f"UPDATE journey_customers SET {flag_col}=1, {ts_col}=?, {extra_col}=?, updated_at=? WHERE id=?",
                (now, now, now, cid),
            )
        else:
            conn.execute(
                f"UPDATE journey_customers SET {flag_col}=1, {ts_col}=?, updated_at=? WHERE id=?",
                (now, now, cid),
            )

    # ── Award engagement points ───────────────────────────────────────────────
    points = 0.5
    conn.execute(
        """
        INSERT INTO review_journey_events
          (id, customer_id, event_type, journey_stage, channel, template_name, metadata_json, created_at)
        VALUES (?, ?, 'message_sent', ?, ?, ?, '{}', ?)
        """,
        (str(uuid.uuid4()), cid, stage, channel, template_name, now),
    )
    conn.execute(
        """
        UPDATE journey_customers
        SET engagement_score = engagement_score + ?, last_engagement_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (points, now, now, cid),
    )

    # ── Refresh customer_status ───────────────────────────────────────────────
    # Re-read freshened customer row
    updated_row = conn.execute(
        "SELECT * FROM journey_customers WHERE id = ?", (cid,)
    ).fetchone()
    if updated_row:
        fresh = dict(updated_row)
        new_status = _compute_customer_status(fresh)
        if new_status != fresh.get("customer_status"):
            conn.execute(
                "UPDATE journey_customers SET customer_status=?, updated_at=? WHERE id=?",
                (new_status, now, cid),
            )

    logger.info("Review journey sent: %s → %s | stage=%s | wamid=%s",
                template_name, phone, stage, message_id)

    return ReviewStageResult(
        cid, phone, stage,
        template_name=template_name,
        status="sent",
        message_id=message_id,
        channel=channel,
        points_awarded=points,
    )


# ─── Daily orchestration helper ──────────────────────────────────────────────

def get_review_journey_cohort(
    conn: Any,
    shop: str,
    stage: str,
) -> list[dict[str, Any]]:
    """
    Return the list of customers eligible for a given review journey stage today.
    Uses delivered_at for day-window calculations.
    """
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)

    def cutoff(days: int) -> str:
        return (now - timedelta(days=days)).isoformat()

    base = """
        SELECT * FROM journey_customers
        WHERE shop_domain = ?
          AND do_not_message = 0
          AND whatsapp_subscription_status = 'subscribed'
          AND delivery_status = 'delivered'
          AND delivered_at IS NOT NULL
    """

    cohort_sql: dict[str, tuple[str, list]] = {
        "review_pure_day15": (
            "AND day15_sent = 0"
            " AND delivered_at BETWEEN ? AND ?",
            [cutoff(18), cutoff(13)],
        ),
        "review_thanks_day18": (
            "AND crosssell_day18_sent = 0"
            " AND review_submitted_at IS NOT NULL"   # reviewed = yes
            " AND delivered_at BETWEEN ? AND ?",
            [cutoff(22), cutoff(16)],
        ),
        "crosssell_day18": (
            "AND crosssell_day18_sent = 0"
            " AND review_submitted_at IS NULL"       # reviewed = no
            " AND day15_sent = 1"                    # must have received day15
            " AND delivered_at BETWEEN ? AND ?",
            [cutoff(22), cutoff(16)],
        ),
        "replenishment_day45": (
            "AND replenishment_day45_sent = 0"
            " AND delivered_at BETWEEN ? AND ?",
            [cutoff(50), cutoff(42)],
        ),
        "vip_day75": (
            "AND vip_day75_sent = 0"
            " AND customer_status IN ('warm','hot','purchased','vip')"
            " AND delivered_at BETWEEN ? AND ?",
            [cutoff(82), cutoff(70)],
        ),
    }

    spec = cohort_sql.get(stage)
    if not spec:
        return []

    where, params = spec
    rows = conn.execute(base + " " + where, [shop] + params).fetchall()
    return [dict(r) for r in rows]


# ─── Review submission handler ────────────────────────────────────────────────

def record_review_submission(
    conn: Any,
    customer_id: str,
    rating: int,
    review_text: str = "",
    channel: str = "google",
) -> None:
    """
    Called when a customer submits a review (via Google or internal form).
    Updates journey_customers + awards loyalty points (+20).
    """
    now = _now()
    conn.execute(
        """
        UPDATE journey_customers
        SET review_submitted_at = ?,
            review_submitted_channel = ?,
            review_rating = ?,
            review_text = ?,
            google_review_status = 'submitted',
            engagement_score = engagement_score + 20,
            is_responsive = 1,
            customer_status = CASE
                WHEN customer_status IN ('cold','warm') THEN 'hot'
                ELSE customer_status
            END,
            updated_at = ?
        WHERE id = ?
        """,
        (now, channel, rating, review_text, now, customer_id),
    )
    conn.execute(
        """
        INSERT INTO review_journey_events
          (id, customer_id, event_type, journey_stage, channel,
           metadata_json, created_at)
        VALUES (?, ?, 'review_submitted', 'review', ?,
                ?, ?)
        """,
        (
            str(uuid.uuid4()), customer_id, channel,
            json.dumps({"rating": rating, "text": review_text[:200]}),
            now,
        ),
    )
    logger.info("Review submitted for customer %s — rating=%d channel=%s", customer_id, rating, channel)


def record_review_event(
    conn: Any,
    customer_id: str,
    event_type: str,
    stage: str = "",
    channel: str = "whatsapp",
    metadata: dict | None = None,
) -> None:
    """Generic event recorder for review journey tracking."""
    now = _now()
    conn.execute(
        """
        INSERT INTO review_journey_events
          (id, customer_id, event_type, journey_stage, channel,
           metadata_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()), customer_id, event_type, stage, channel,
            json.dumps(metadata or {}),
            now,
        ),
    )

    # Also update opened_at / clicked_at on the most recent journey_messages row
    if event_type == "message_opened":
        conn.execute(
            """
            UPDATE journey_messages SET opened_at = ?
            WHERE id = (
                SELECT id FROM journey_messages
                WHERE customer_id = ? AND journey_stage = ? AND opened_at IS NULL
                ORDER BY sent_at DESC
                LIMIT 1
            )
            """,
            (now, customer_id, stage),
        )
    elif event_type == "link_clicked":
        conn.execute(
            """
            UPDATE journey_messages SET clicked_at = ?
            WHERE id = (
                SELECT id FROM journey_messages
                WHERE customer_id = ? AND journey_stage = ? AND clicked_at IS NULL
                ORDER BY sent_at DESC
                LIMIT 1
            )
            """,
            (now, customer_id, stage),
        )

    # Points for open or click
    pts_map = {"message_opened": 2.0, "link_clicked": 5.0, "review_link_clicked": 8.0}
    pts = pts_map.get(event_type, 0.0)
    if pts:
        conn.execute(
            "UPDATE journey_customers SET engagement_score=engagement_score+?, last_engagement_at=?, updated_at=? WHERE id=?",
            (pts, now, now, customer_id),
        )
