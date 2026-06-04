from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _run_job() -> None:
    try:
        from app.services.ai_reply_queue_service import run_due_ai_reply_jobs

        processed = run_due_ai_reply_jobs()
        if processed:
            logger.info("ai_reply_queue_scheduler: processed=%d", len(processed))
    except Exception as exc:
        logger.error("ai_reply_queue_scheduler error: %s", exc)


def start_ai_reply_queue_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    _scheduler = BackgroundScheduler(daemon=True, timezone="UTC")
    _scheduler.add_job(
        _run_job,
        "interval",
        seconds=15,
        id="ai_reply_queue_runner",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info("AI reply queue scheduler started (every 15 seconds)")


def stop_ai_reply_queue_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("AI reply queue scheduler stopped")
    _scheduler = None
