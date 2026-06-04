"""APScheduler worker for scheduled phase-2 campaigns."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.services.campaign_service import process_due_campaigns

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _safe_process_due_campaigns() -> None:
    try:
        result = process_due_campaigns(limit=50)
        if result.get("due"):
            logger.info(
                "Campaign scheduler: due=%s processed=%s sent=%s failed=%s",
                result.get("due"),
                result.get("processed"),
                result.get("sent"),
                result.get("failed"),
            )
    except Exception as exc:  # pragma: no cover - defensive scheduler guard
        logger.error("Campaign scheduler job failed: %s", exc)


def start_campaign_scheduler() -> None:
    global _scheduler
    if not settings.promo_scheduler_enabled:
        logger.info("Campaign scheduler disabled by config")
        return

    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        _safe_process_due_campaigns,
        IntervalTrigger(seconds=max(10, settings.promo_queue_poll_seconds * 10)),
        id="campaigns-process-due",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    _scheduler.start()
    logger.info("Campaign scheduler started")


def stop_campaign_scheduler() -> None:
    global _scheduler
    if not _scheduler:
        return

    try:
        _scheduler.shutdown(wait=False)
        logger.info("Campaign scheduler stopped")
    finally:
        _scheduler = None
