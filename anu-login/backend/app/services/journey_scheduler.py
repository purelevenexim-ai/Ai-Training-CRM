"""
Journey Scheduler

APScheduler task that runs journey step sends every 5 minutes.
"""
from __future__ import annotations

import logging
from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _run_job() -> None:
    try:
        from app.services.journey_engine_v2 import run_due_steps
        results = run_due_steps()
        if results:
            sent = sum(1 for r in results if r.status == 'sent')
            logger.info('journey_scheduler: processed=%d sent=%d', len(results), sent)
    except Exception as exc:
        logger.error('journey_scheduler error: %s', exc)


def start_journey_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.add_job(_run_job, 'interval', minutes=5, id='journey_step_runner', replace_existing=True)
    _scheduler.start()
    logger.info('Journey scheduler started (every 5 minutes)')


def stop_journey_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info('Journey scheduler stopped')
