"""APScheduler worker for promotional campaign queue processing."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.config import settings
from app.services.promotional_campaign_service import PromotionalCampaignService

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _safe_enqueue_due() -> None:
    try:
        result = PromotionalCampaignService.enqueue_due_campaigns()
        if result.get("count"):
            logger.info("Promotional queue: moved %s scheduled campaign(s) to queue", result["count"])
    except Exception as exc:  # pragma: no cover - defensive scheduler guard
        logger.error("Promotional scheduler enqueue job failed: %s", exc)


def _safe_process_queue() -> None:
    try:
        result = PromotionalCampaignService.process_queue_batch()
        if result.get("processed"):
            logger.info(
                "Promotional queue: processed=%s sent=%s failed=%s",
                result.get("processed"),
                result.get("sent"),
                result.get("failed"),
            )
    except Exception as exc:  # pragma: no cover - defensive scheduler guard
        logger.error("Promotional scheduler process job failed: %s", exc)


def start_promotional_queue_worker() -> None:
    global _scheduler
    if not settings.promo_scheduler_enabled:
        logger.info("Promotional queue scheduler disabled by config")
        return

    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        _safe_enqueue_due,
        IntervalTrigger(seconds=max(5, settings.promo_queue_poll_seconds)),
        id="promo-enqueue-due",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    _scheduler.add_job(
        _safe_process_queue,
        IntervalTrigger(seconds=max(1, settings.promo_queue_poll_seconds)),
        id="promo-process-queue",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    _scheduler.start()
    logger.info("Promotional queue scheduler started")


def stop_promotional_queue_worker() -> None:
    global _scheduler
    if not _scheduler:
        return

    try:
        _scheduler.shutdown(wait=False)
        logger.info("Promotional queue scheduler stopped")
    finally:
        _scheduler = None
