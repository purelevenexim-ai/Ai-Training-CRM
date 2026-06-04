"""Scheduler for refreshing customer intelligence scores."""

from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)
_scheduler: BackgroundScheduler | None = None


def _run_job() -> None:
    try:
        from app.services.customer_intelligence_service import recompute_all_customer_scores
        result = recompute_all_customer_scores(limit=5000)
        logger.info(
            "customer_score_scheduler: checked=%s updated=%s",
            result.get("checked"),
            result.get("updated"),
        )
    except Exception as exc:  # pragma: no cover - defensive scheduler guard
        logger.error("customer_score_scheduler error: %s", exc)


def _run_shopify_sync_job() -> None:
    try:
        from app.services.shopify_sync_service import backfill_customers
        result = backfill_customers()
        logger.info(
            "shopify_sync_scheduler: created=%s updated=%s",
            result.get("created"),
            result.get("updated"),
        )
    except Exception as exc:  # pragma: no cover
        logger.error("shopify_sync_scheduler error: %s", exc)


def _run_meta_audience_sync_job() -> None:
    try:
        from app.services.meta_audience_sync import sync_meta_audiences
        result = sync_meta_audiences()
        logger.info(
            "meta_audience_sync_scheduler: ok=%s tiers=%s",
            result.get("ok"),
            list(result.get("tiers", {}).keys()),
        )
    except Exception as exc:  # pragma: no cover
        logger.error("meta_audience_sync_scheduler error: %s", exc)


def start_customer_score_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        return
    _scheduler = BackgroundScheduler(daemon=True, timezone="UTC")
    _scheduler.add_job(
        _run_job,
        "interval",
        hours=1,
        id="customer_score_refresh",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    _scheduler.add_job(
        _run_shopify_sync_job,
        "interval",
        minutes=30,
        id="shopify_customer_sync",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    _scheduler.add_job(
        _run_meta_audience_sync_job,
        "interval",
        hours=6,
        id="meta_audience_sync",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    _scheduler.start()
    logger.info("Customer score scheduler started (hourly) + Shopify sync (every 30 min) + Meta audience sync (every 6 h)")


def stop_customer_score_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Customer score scheduler stopped")
    _scheduler = None
