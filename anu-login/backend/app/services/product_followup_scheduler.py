from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _run_job() -> None:
    try:
        from app.services.product_followup_service import run_due_product_followups

        processed = run_due_product_followups()
        if processed:
            logger.info("product_followup_scheduler: processed=%d", len(processed))
    except Exception as exc:
        logger.error("product_followup_scheduler error: %s", exc)


def start_product_followup_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(
        _run_job,
        "interval",
        minutes=1,
        id="product_followup_runner",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("Product followup scheduler started (every 1 minute)")


def stop_product_followup_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Product followup scheduler stopped")
