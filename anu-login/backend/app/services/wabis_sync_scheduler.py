"""
APScheduler worker: syncs Wabis subscribers into the CRM every 30 minutes.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None
_INTERVAL_SECONDS = 1800  # 30 minutes


def _safe_sync() -> None:
    try:
        from app.services.wabis_lead_sync import sync_wabis_leads
        sync_wabis_leads()
    except Exception as exc:
        logger.error("Wabis sync scheduler job failed: %s", exc)


def start_wabis_sync_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        _safe_sync,
        IntervalTrigger(seconds=_INTERVAL_SECONDS),
        id="wabis-lead-sync",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    _scheduler.start()
    logger.info("Wabis sync scheduler started (interval=%ds)", _INTERVAL_SECONDS)


def stop_wabis_sync_scheduler() -> None:
    global _scheduler
    if not _scheduler:
        return
    try:
        _scheduler.shutdown(wait=False)
        logger.info("Wabis sync scheduler stopped")
    finally:
        _scheduler = None
