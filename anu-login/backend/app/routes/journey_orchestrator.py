"""
Basil Commerce OS — Phase 5
routes/journey_orchestrator.py

Daily cron brain: decides who gets what message today and sends it.

This is the MASTER ORCHESTRATION ENDPOINT. N8N (or a simple cron job) calls:
  POST /api/journey/orchestrate
  {  "shop_domain": "...", "dry_run": false }

Once per day at 10am IST. Processes all 7 active journey stages in one pass.

Additional endpoints:
  POST /api/journey/orchestrate/stage     — run one specific stage only
  POST /api/journey/orchestrate/customer  — send to a single customer (testing)
  POST /api/journey/orchestrate/preview   — dry run (no sends)
  GET  /api/journey/orchestrate/status    — last run stats
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.journey_engine import send_journey_message, should_send
from app.storage import get_db_connection
from app.services.email_service import send_and_record_journey_email

logger = logging.getLogger(__name__)
router = APIRouter()
_IST = timezone(timedelta(hours=5, minutes=30))
_AUTOMATION_START_DEFAULT = "2026-05-23T00:00:00+05:30"


# ─── Models ───────────────────────────────────────────────────────────────────

class OrchestrateRequest(BaseModel):
    shop_domain: str = Field(min_length=1, max_length=200)
    dry_run: bool = False
    stages: list[str] = []  # empty = run all


class StageRequest(BaseModel):
    shop_domain: str = Field(min_length=1, max_length=200)
    stage: str = Field(min_length=1, max_length=50)
    dry_run: bool = False
    limit: int = Field(default=500, ge=1, le=5000)


class SingleCustomerRequest(BaseModel):
    shop_domain: str = Field(min_length=1, max_length=200)
    customer_id: str = Field(min_length=1)
    stage: str = Field(min_length=1, max_length=50)
    dry_run: bool = False


class PreviewRequest(BaseModel):
    shop_domain: str = Field(min_length=1, max_length=200)


# ─── Cohort queries ───────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _automation_start_iso() -> str:
    raw = (os.getenv("WHATSAPP_AUTOMATION_START_ISO") or _AUTOMATION_START_DEFAULT).strip()
    parsed = _parse_iso(raw) or datetime(2026, 5, 23, 0, 0, tzinfo=_IST)
    return parsed.astimezone(timezone.utc).isoformat()


def _cutoff(days: int) -> str:
    return (_now() - timedelta(days=days)).isoformat()


def _fetch_cohort(conn: Any, shop: str, sql_where: str, params: tuple) -> list[dict[str, Any]]:
    base = """
        SELECT * FROM journey_customers
        WHERE shop_domain = ?
          AND do_not_message = 0
          AND whatsapp_subscription_status = 'subscribed'
          AND COALESCE(journey_started_at, created_at) >= ?
    """
    rows = conn.execute(base + " AND " + sql_where, (shop, _automation_start_iso(), *params)).fetchall()
    return [dict(r) for r in rows]


STAGE_COHORT_SQL: dict[str, tuple[str, tuple]] = {
    # Stage key → (WHERE clause after base filters, extra_params)
    # Note: shop_domain is always first param

    "day2": (
        "day2_sent = 0"
        " AND delivery_status NOT IN ('delivered', 'delivery_failed')"
        " AND journey_started_at >= ? AND journey_started_at <= ?",
        (_cutoff, 4, 1),   # 1-4 days since order
    ),
    "day5": (
        "day5_sent = 0"
        " AND delivery_status = 'delivered'"
        " AND delivered_at >= ? AND delivered_at <= ?",
        (_cutoff, 2, 0),   # 0-2 days since delivered
    ),
    "day15": (
        "day15_sent = 0"
        " AND is_responsive = 1"
        " AND google_review_status != 'submitted'"
        " AND delivered_at >= ? AND delivered_at <= ?",
        (_cutoff, 16, 10), # 10-16 days since delivered
    ),
    "day30": (
        "day30_sent = 0"
        " AND is_responsive = 1"
        " AND delivered_at >= ? AND delivered_at <= ?",
        (_cutoff, 33, 28), # 28-33 days since delivered
    ),
    "day60": (
        "day60_sent = 0"
        " AND delivered_at >= ? AND delivered_at <= ?",
        (_cutoff, 63, 58), # 58-63 days since delivered
    ),
    "day75": (
        "day75_sent = 0"
        " AND is_responsive = 1"
        " AND delivered_at >= ? AND delivered_at <= ?",
        (_cutoff, 78, 73), # 73-78 days since delivered
    ),
    "day95": (
        "day95_sent = 0"
        " AND delivered_at >= ? AND delivered_at <= ?",
        (_cutoff, 98, 93), # 93-98 days since delivered
    ),
}

# Map stage key → journey_engine stage name
STAGE_KEY_MAP: dict[str, str] = {
    "day2":  "in_transit",
    "day5":  "delivered",
    "day15": "review",
    "day30": "upsell",
    "day60": "corporate",
    "day75": "loyalty",
    "day95": "rfm",
}

ALL_STAGES = list(STAGE_COHORT_SQL.keys())


def _resolve_cohort(conn: Any, shop: str, stage_key: str) -> list[dict[str, Any]]:
    """Fetch customers eligible for a given stage today."""
    sql_spec = STAGE_COHORT_SQL.get(stage_key)
    if not sql_spec:
        return []
    where_sql, param_spec = sql_spec
    # Build date params dynamically
    params: list[str] = []
    if len(param_spec) == 3:
        cutoff_fn, days_max, days_min = param_spec
        params = [cutoff_fn(days_max), cutoff_fn(days_min)]
    else:
        params = list(param_spec)

    return _fetch_cohort(conn, shop, where_sql, tuple(params))


# ─── Core run logic ───────────────────────────────────────────────────────────

def _run_stage(
    conn: Any,
    shop: str,
    stage_key: str,
    dry_run: bool,
    limit: int = 500,
) -> dict[str, Any]:
    """Run one stage: fetch cohort, apply suppression, send."""
    stage_name = STAGE_KEY_MAP.get(stage_key, stage_key)
    customers  = _resolve_cohort(conn, shop, stage_key)[:limit]

    sent = suppressed = errors = 0
    sample: list[dict[str, Any]] = []

    for customer in customers:
        result = send_journey_message(conn, customer, stage_name, dry_run=dry_run)
        if result.status == "sent":
            sent += 1
        elif result.status in ("suppressed",):
            suppressed += 1
        elif result.status == "dry_run":
            sent += 1  # count as "would send"
        else:
            errors += 1
            logger.warning("Stage %s send error for %s: %s", stage_key, customer["id"], result.error)

        # ── Fire email in parallel (best-effort, non-blocking to WhatsApp result) ──
        if not dry_run and result.status == "sent":
            try:
                email_result = send_and_record_journey_email(conn, customer, stage_name, result.message_id or "")
                if not email_result.success:
                    logger.info(
                        "Email skipped for customer %s stage %s: %s",
                        customer["id"], stage_name, email_result.error,
                    )
            except Exception as exc:
                logger.error("Email dispatch exception for %s: %s", customer.get("id"), exc)

        if len(sample) < 5:
            sample.append({
                "id": result.customer_id,
                "phone_suffix": result.phone[-4:] if result.phone else "",
                "template": result.template_name,
                "status": result.status,
            })

    return {
        "stage": stage_key,
        "eligible": len(customers),
        "sent": sent,
        "suppressed": suppressed,
        "errors": errors,
        "sample": sample,
    }


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.post(
    "/journey/orchestrate",
    summary="Daily cron: process all journey stages and send messages",
    status_code=status.HTTP_200_OK,
)
def orchestrate(payload: OrchestrateRequest) -> dict[str, Any]:
    """
    Master daily orchestration. Call once per day at 10am IST.
    Processes all 7 active stages (day2, day5, day15, day30, day60, day75, day95).

    Set dry_run=true to preview cohort sizes without sending.
    Set stages=["day15","day30"] to run specific stages only.
    """
    started_at = _now().isoformat()
    stages_to_run = payload.stages if payload.stages else ALL_STAGES
    stage_results: list[dict[str, Any]] = []

    with get_db_connection() as conn:
        for stage_key in stages_to_run:
            if stage_key not in STAGE_COHORT_SQL:
                logger.warning("Unknown stage key: %s — skipping", stage_key)
                continue
            result = _run_stage(conn, payload.shop_domain, stage_key, payload.dry_run)
            stage_results.append(result)

    total_sent = sum(r["sent"] for r in stage_results)
    total_eligible = sum(r["eligible"] for r in stage_results)

    return {
        "status":       "dry_run" if payload.dry_run else "ok",
        "shop_domain":  payload.shop_domain,
        "started_at":   started_at,
        "finished_at":  _now().isoformat(),
        "stages_run":   len(stage_results),
        "total_eligible": total_eligible,
        "total_sent":   total_sent,
        "stages":       stage_results,
    }


@router.post(
    "/journey/orchestrate/stage",
    summary="Run a single journey stage (manual trigger or catch-up)",
    status_code=status.HTTP_200_OK,
)
def orchestrate_stage(payload: StageRequest) -> dict[str, Any]:
    with get_db_connection() as conn:
        result = _run_stage(conn, payload.shop_domain, payload.stage, payload.dry_run, payload.limit)
    return {"status": "dry_run" if payload.dry_run else "ok", **result}


@router.post(
    "/journey/orchestrate/customer",
    summary="Send a specific stage message to one customer (testing / manual)",
    status_code=status.HTTP_200_OK,
)
def orchestrate_customer(payload: SingleCustomerRequest) -> dict[str, Any]:
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT * FROM journey_customers WHERE id = ? AND shop_domain = ?",
            (payload.customer_id, payload.shop_domain),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Customer not found")
        customer = dict(row)
        result = send_journey_message(conn, customer, payload.stage, payload.dry_run)

    return {
        "status":       result.status,
        "customer_id":  result.customer_id,
        "template":     result.template_name,
        "stage":        result.stage,
        "message_id":   result.message_id,
        "dry_run":      payload.dry_run,
        "error":        result.error or None,
    }


@router.post(
    "/journey/orchestrate/preview",
    summary="Dry run: show cohort sizes for each stage without sending",
    status_code=status.HTTP_200_OK,
)
def preview_orchestration(payload: PreviewRequest) -> dict[str, Any]:
    """Returns how many customers would be messaged per stage today."""
    preview: list[dict[str, Any]] = []
    with get_db_connection() as conn:
        for stage_key in ALL_STAGES:
            customers = _resolve_cohort(conn, payload.shop_domain, stage_key)
            # Count suppressed
            would_send = 0
            would_suppress = 0
            stage_name = STAGE_KEY_MAP.get(stage_key, stage_key)
            for c in customers:
                ok, _ = should_send(c, stage_name)
                if ok:
                    would_send += 1
                else:
                    would_suppress += 1
            preview.append({
                "stage": stage_key,
                "stage_name": stage_name,
                "eligible": len(customers),
                "would_send": would_send,
                "would_suppress": would_suppress,
            })

    return {
        "shop_domain": payload.shop_domain,
        "as_of":       _now().isoformat(),
        "stages":      preview,
        "total_would_send": sum(s["would_send"] for s in preview),
    }


@router.get(
    "/journey/orchestrate/status",
    summary="Get orchestration status for the last 24h",
    status_code=status.HTTP_200_OK,
)
def orchestration_status(shop_domain: str | None = None) -> dict[str, Any]:
    """Return a quick status view for orchestrations, optionally scoped to one shop."""
    cutoff = (_now() - timedelta(hours=24)).isoformat()

    with get_db_connection() as conn:
        if shop_domain:
            rows = conn.execute(
                """
                SELECT jm.journey_stage, COUNT(*) as sent, jm.delivery_status
                FROM journey_messages jm
                JOIN journey_customers jc ON jm.customer_id = jc.id
                WHERE jc.shop_domain = ? AND jm.sent_at >= ?
                GROUP BY jm.journey_stage, jm.delivery_status
                ORDER BY jm.journey_stage
                """,
                (shop_domain, cutoff),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT journey_stage, COUNT(*) as sent, delivery_status
                FROM journey_messages
                WHERE sent_at >= ?
                GROUP BY journey_stage, delivery_status
                ORDER BY journey_stage
                """,
                (cutoff,),
            ).fetchall()

    stats: dict[str, Any] = {}
    for row in rows:
        stage = row["journey_stage"]
        stats.setdefault(stage, {})[row["delivery_status"]] = row["sent"]

    return {
        "shop_domain": shop_domain,
        "window": "last_24h",
        "as_of": _now().isoformat(),
        "by_stage": stats,
        "total_sent": sum(count for stage_data in stats.values() for count in stage_data.values()),
    }


@router.get(
    "/journey/orchestrate/last-run",
    summary="Get the last orchestration run stats from the message log",
    status_code=status.HTTP_200_OK,
)
def last_run_stats(shop_domain: str) -> dict[str, Any]:
    """Returns counts of messages sent in the last 24 hours per stage."""
    cutoff = (_now() - timedelta(hours=24)).isoformat()
    with get_db_connection() as conn:
        rows = conn.execute(
            """
            SELECT jm.journey_stage, COUNT(*) as sent, jm.delivery_status
            FROM journey_messages jm
            JOIN journey_customers jc ON jm.customer_id = jc.id
            WHERE jc.shop_domain = ? AND jm.sent_at >= ?
            GROUP BY jm.journey_stage, jm.delivery_status
            ORDER BY jm.journey_stage
            """,
            (shop_domain, cutoff),
        ).fetchall()

    stats: dict[str, Any] = {}
    for row in rows:
        stage = row["journey_stage"]
        stats.setdefault(stage, {})[row["delivery_status"]] = row["sent"]

    return {
        "shop_domain": shop_domain,
        "window": "last_24h",
        "as_of": _now().isoformat(),
        "by_stage": stats,
        "total_sent": sum(
            count
            for stage_data in stats.values()
            for count in stage_data.values()
        ),
    }


@router.get(
    "/journey/orchestrate/pipeline",
    summary="Journey stage pipeline: customer counts and send progress per stage",
    status_code=status.HTTP_200_OK,
)
def pipeline_status(shop_domain: str | None = None) -> dict[str, Any]:
    """
    Returns per-stage totals: how many customers exist at each stage,
    how many have been sent each lifecycle message, and how many are
    still eligible today (no date filtering — raw sent flags).
    """
    with get_db_connection() as conn:
        # Stage breakdown from journey_customers
        automation_start = _automation_start_iso()
        sd_params: tuple = (shop_domain, automation_start) if shop_domain else (automation_start,)
        sd_where = "WHERE shop_domain = ? AND COALESCE(journey_started_at, created_at) >= ?" if shop_domain else "WHERE COALESCE(journey_started_at, created_at) >= ?"
        stage_rows = conn.execute(
            f"SELECT journey_stage, COUNT(*) as total FROM journey_customers {sd_where} GROUP BY journey_stage ORDER BY journey_stage",
            sd_params,
        ).fetchall()

        # Per-flag send counts
        flag_cols = ["day1_sent", "day2_sent", "day5_sent", "day15_sent",
                     "day30_sent", "day60_sent", "day75_sent", "day95_sent"]
        flag_counts: dict[str, int] = {}
        for col in flag_cols:
            row = conn.execute(
                f"SELECT COUNT(*) FROM journey_customers {sd_where} AND {col} = 1",
                sd_params,
            ).fetchone()
            flag_counts[col] = row[0] if row else 0

        total_customers = conn.execute(
            f"SELECT COUNT(*) FROM journey_customers {sd_where}", sd_params
        ).fetchone()[0]

        # Recent messages: last 7 days
        cutoff_7d = (_now() - timedelta(days=7)).isoformat()
        if shop_domain:
            recent_msgs = conn.execute(
                """
                SELECT jm.journey_stage, jm.delivery_status, COUNT(*) as cnt
                FROM journey_messages jm
                JOIN journey_customers jc ON jm.customer_id = jc.id
                WHERE jc.shop_domain = ? AND COALESCE(jc.journey_started_at, jc.created_at) >= ? AND jm.sent_at >= ?
                GROUP BY jm.journey_stage, jm.delivery_status
                """,
                (shop_domain, automation_start, cutoff_7d),
            ).fetchall()
        else:
            recent_msgs = conn.execute(
                """
                SELECT jm.journey_stage, jm.delivery_status, COUNT(*) as cnt
                FROM journey_messages jm
                JOIN journey_customers jc ON jm.customer_id = jc.id
                WHERE COALESCE(jc.journey_started_at, jc.created_at) >= ? AND jm.sent_at >= ?
                GROUP BY jm.journey_stage, jm.delivery_status
                """,
                (automation_start, cutoff_7d),
            ).fetchall()

    stage_totals = {row["journey_stage"]: row["total"] for row in stage_rows}
    recent_by_stage: dict[str, dict] = {}
    for row in recent_msgs:
        recent_by_stage.setdefault(row["journey_stage"] if "journey_stage" in row.keys() else row[0], {})[
            row["delivery_status"] if "delivery_status" in row.keys() else row[1]
        ] = row["cnt"] if "cnt" in row.keys() else row[2]

    pipeline = [
        {
            "stage_key":  sk,
            "stage_name": STAGE_KEY_MAP.get(sk, sk),
            "flag":       f"day{sk[3:]}_sent" if sk.startswith("day") else f"{sk}_sent",
            "total_sent_ever": flag_counts.get(f"{sk[3:]}_sent" if False else f"day{sk[3:]}_sent", flag_counts.get(f"{sk}_sent", 0)),
        }
        for sk in ALL_STAGES
    ]

    return {
        "shop_domain": shop_domain,
        "as_of": _now().isoformat(),
        "automation_start": automation_start,
        "total_journey_customers": total_customers,
        "stage_breakdown": stage_totals,
        "send_flags": flag_counts,
        "recent_7d": recent_by_stage,
        "next_run_utc": "04:30",
        "next_run_ist": "10:00",
        "pipeline": pipeline,
    }
