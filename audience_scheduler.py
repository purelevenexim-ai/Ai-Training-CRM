"""
Audience Sync Scheduler - Phase 4
APScheduler runs daily:
  - 2:00 AM UTC: Meta audience sync (account 237007475595482)
  - 2:30 AM UTC: Google audience sync (customer 7225234563)
Manual trigger endpoints: POST /api/crm/sync/meta/now, POST /api/crm/sync/google/now
"""

import logging
import os
from datetime import datetime

from fastapi import APIRouter
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger("pureleven.scheduler")

router = APIRouter(prefix="/api/crm", tags=["scheduler"])

# Single shared scheduler instance
scheduler = AsyncIOScheduler(timezone="UTC")

META_ACCOUNT_ID = "237007475595482"
GOOGLE_CUSTOMER_ID = "7225234563"


# ─── Sync Functions ───────────────────────────────────────────────────────────

async def _sync_meta_audiences():
    """
    Push latest CRM segments to Meta Custom Audiences.
    Calls the meta_audience_sync module.
    """
    logger.info(f"[{datetime.utcnow().isoformat()}] Starting Meta audience sync for account {META_ACCOUNT_ID}")
    try:
        try:
            from app.meta_audience_sync import run_meta_audience_sync
        except ImportError:
            from meta_audience_sync import run_meta_audience_sync
        result = await run_meta_audience_sync()
        logger.info(f"Meta audience sync completed: {result}")
        return result
    except ImportError:
        logger.warning("meta_audience_sync module not found — skipping Meta sync")
        return {"status": "skipped"}
    except Exception as e:
        logger.error(f"Meta audience sync failed: {e}")
        return {"status": "error", "error": str(e)}


async def _sync_google_audiences():
    """
    Push latest CRM segments to Google Ads Customer Match audiences.
    Calls the google_audience_sync module.
    """
    logger.info(f"[{datetime.utcnow().isoformat()}] Starting Google audience sync for customer {GOOGLE_CUSTOMER_ID}")
    try:
        try:
            from app.google_audience_sync import run_google_audience_sync
        except ImportError:
            from google_audience_sync import run_google_audience_sync
        result = await run_google_audience_sync()
        logger.info(f"Google audience sync completed: {result}")
        return result
    except ImportError:
        logger.warning("google_audience_sync module not found — skipping Google sync")
        return {"status": "skipped"}
    except Exception as e:
        logger.error(f"Google audience sync failed: {e}")
        return {"status": "error", "error": str(e)}


# ─── Scheduler Lifecycle ──────────────────────────────────────────────────────

def start_scheduler():
    """Register all scheduled jobs and start the scheduler. Call on app startup."""
    if scheduler.running:
        return

    # Meta: 2:00 AM UTC daily
    scheduler.add_job(
        _sync_meta_audiences,
        trigger=CronTrigger(hour=2, minute=0),
        id="meta_audience_sync",
        replace_existing=True,
        name="Daily Meta Audience Sync",
    )

    # Google: 2:30 AM UTC daily
    scheduler.add_job(
        _sync_google_audiences,
        trigger=CronTrigger(hour=2, minute=30),
        id="google_audience_sync",
        replace_existing=True,
        name="Daily Google Audience Sync",
    )

    scheduler.start()
    logger.info("Audience sync scheduler started (Meta 02:00 UTC, Google 02:30 UTC)")


def stop_scheduler():
    """Gracefully shut down the scheduler. Call on app shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Audience sync scheduler stopped")


# ─── Manual Trigger Endpoints ─────────────────────────────────────────────────

@router.post("/sync/meta/now")
async def trigger_meta_sync():
    """Manually trigger Meta audience sync immediately"""
    result = await _sync_meta_audiences()
    return {
        "status": result.get("status", "ok"),
        "message": "Meta audience sync triggered",
        "account_id": META_ACCOUNT_ID,
        "result": result,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.post("/sync/google/now")
async def trigger_google_sync():
    """Manually trigger Google audience sync immediately"""
    result = await _sync_google_audiences()
    return {
        "status": result.get("status", "ok"),
        "message": "Google audience sync triggered",
        "customer_id": GOOGLE_CUSTOMER_ID,
        "result": result,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/sync/status")
async def get_sync_status():
    """Get current scheduler status and next run times"""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
        })
    return {
        "scheduler_running": scheduler.running,
        "jobs": jobs,
        "timestamp": datetime.utcnow().isoformat(),
    }
