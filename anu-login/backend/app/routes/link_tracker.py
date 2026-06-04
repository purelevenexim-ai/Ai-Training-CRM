"""
Basil Commerce OS — Phase 5
routes/link_tracker.py

WhatsApp click-through tracker. Replaces GA → CRM sync.

Every link sent in a WhatsApp template body should route through:
  GET /r?c={customer_id}&t={template_name}&n={destination_url}

Flow:
  1. Customer taps link in WhatsApp message
  2. Browser hits this endpoint
  3. We log the click (+5 engagement points, mark is_responsive)
  4. Immediately HTTP 302 → destination_url

Usage in template body variables:
  {{3}} = https://api.pureleven.com/r?c=CUST_ID&t=review_incentive_v1&n=https%3A%2F%2Fg.page%2Fr%2Fpureleven%2Freview

Endpoints:
  GET /r          — main redirect + track
  GET /r/health   — confirm endpoint is live
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse, JSONResponse

from app.review_journey_engine import record_review_event
from app.storage import get_db_connection

router = APIRouter()

CLICK_POINTS = 5.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_click(customer_id: str, template_name: str, destination: str) -> None:
    """Log the click and update engagement score + is_responsive flag."""
    event_id = str(uuid.uuid4())
    now = _now()

    with get_db_connection() as conn:
        # Check customer exists
        row = conn.execute(
            "SELECT id, engagement_score FROM journey_customers WHERE id = ?",
            (customer_id,),
        ).fetchone()

        if not row:
            # Unknown customer — log but don't crash the redirect
            return

        new_score = (row["engagement_score"] or 0.0) + CLICK_POINTS

        # Log the engagement event
        conn.execute(
            """
            INSERT INTO journey_engagement_events
              (id, customer_id, event_type, template_name, points_awarded, metadata_json, created_at)
            VALUES (?, ?, 'link_click', ?, ?, ?, ?)
            """,
            (
                event_id,
                customer_id,
                template_name or "",
                CLICK_POINTS,
                json.dumps({"destination": destination, "source": "link_tracker"}),
                now,
            ),
        )

        # Update customer engagement score + mark responsive
        conn.execute(
            """
            UPDATE journey_customers
               SET engagement_score    = ?,
                   is_responsive       = 1,
                   last_engagement_at  = ?,
                   updated_at          = ?
             WHERE id = ?
            """,
            (new_score, now, now, customer_id),
        )

        # If this click belongs to a review-journey message, mirror it into
        # review_journey_events and journey_messages.clicked_at for dashboarding.
        review_row = conn.execute(
            """
            SELECT journey_stage
            FROM journey_messages
            WHERE customer_id = ? AND template_name = ?
              AND journey_stage IN (
                'review_pure_day15','review_thanks_day18','crosssell_day18',
                'replenishment_day45','vip_day75'
              )
            ORDER BY sent_at DESC
            LIMIT 1
            """,
            (customer_id, template_name or ""),
        ).fetchone()
        if review_row:
            stage = review_row["journey_stage"]
            event_type = "review_link_clicked" if "g.page" in (destination or "") or "/review" in (destination or "") else "link_clicked"
            record_review_event(
                conn=conn,
                customer_id=customer_id,
                event_type=event_type,
                stage=stage,
                channel="whatsapp",
                metadata={"destination": destination, "template_name": template_name},
            )
        conn.commit()


@router.get("/r", summary="WhatsApp link tracker + redirect", include_in_schema=True)
def track_and_redirect(
    c: str = Query(description="journey_customers.id"),
    t: str = Query(default="", description="Template name (for analytics)"),
    n: str = Query(description="Destination URL to redirect to"),
) -> RedirectResponse:
    """
    Track a WhatsApp link click then redirect the user.
    Called when a customer taps a link in a WhatsApp message.
    """
    try:
        _record_click(customer_id=c, template_name=t, destination=n)
    except Exception:
        # Never break the redirect — tracking is best-effort
        pass

    return RedirectResponse(url=n, status_code=302)


@router.get("/r/health", include_in_schema=False)
def tracker_health() -> dict[str, str]:
    return {"status": "ok", "endpoint": "/r"}
