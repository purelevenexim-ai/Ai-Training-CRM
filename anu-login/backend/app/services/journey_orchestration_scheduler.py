"""
Journey Orchestration Scheduler

Runs the daily journey stage orchestration at 10am IST (04:30 UTC).
Calls _run_stage for all 7 lifecycle stages against the live DB.
"""
from __future__ import annotations

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None

SHOP_DOMAIN = "rwxtic-gz.myshopify.com"


def _run_orchestration() -> None:
    try:
        from app.routes.journey_orchestrator import _run_stage, ALL_STAGES
        from app.storage import get_db_connection

        stage_results = []
        with get_db_connection() as conn:
            for stage_key in ALL_STAGES:
                result = _run_stage(conn, SHOP_DOMAIN, stage_key, dry_run=False)
                stage_results.append(result)
                if result["eligible"] > 0:
                    logger.info(
                        "journey_orchestrator: stage=%s eligible=%d sent=%d suppressed=%d errors=%d",
                        stage_key,
                        result["eligible"],
                        result["sent"],
                        result["suppressed"],
                        result["errors"],
                    )

        total_sent = sum(r["sent"] for r in stage_results)
        total_eligible = sum(r["eligible"] for r in stage_results)
        logger.info(
            "journey_orchestrator: complete total_eligible=%d total_sent=%d",
            total_eligible,
            total_sent,
        )
    except Exception as exc:
        logger.error("journey_orchestration_scheduler error: %s", exc, exc_info=True)


def start_journey_orchestration_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    _scheduler = BackgroundScheduler(daemon=True)
    # 10am IST = 04:30 UTC
    _scheduler.add_job(
        _run_orchestration,
        CronTrigger(hour=4, minute=30, timezone="UTC"),
        id="journey_daily_orchestration",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    _scheduler.start()
    logger.info("Journey orchestration scheduler started (daily 10am IST / 04:30 UTC)")


def stop_journey_orchestration_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Journey orchestration scheduler stopped")
