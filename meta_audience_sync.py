"""
Meta Audience Sync - Phase 4
Syncs CRM customers to Meta Custom Audiences using the Marketing API.
Hashes PII (email, phone) with SHA-256 before uploading per Meta requirements.

Account: Facebook Pure Leven Exim (237007475595482)
Requires env vars:
  FACEBOOK_ACCESS_TOKEN    — User / system-user token with ads_management scope
  FACEBOOK_AD_ACCOUNT_ID   — 237007475595482
  META_AUDIENCE_ID         — Custom audience ID to update (create once in Ads Manager)
"""

import hashlib
import json
import logging
import os
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger("pureleven.meta_sync")

FACEBOOK_ACCESS_TOKEN = os.getenv("FACEBOOK_ACCESS_TOKEN", "")
FACEBOOK_AD_ACCOUNT_ID = os.getenv("FACEBOOK_AD_ACCOUNT_ID", "237007475595482")
META_AUDIENCE_ID = os.getenv("META_AUDIENCE_ID", "")
META_GRAPH_API_VERSION = "v20.0"
META_BATCH_SIZE = 10_000  # Max per API call


def _sha256(value: str) -> str:
    """Hash a string value with SHA-256 (Meta requirement for PII)."""
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


def _build_user_data(customers: list[dict]) -> list[dict]:
    """
    Build the META user data schema from customer records.
    Each entry: { schema: [EMAIL, FN, LN, PHONE], data: [[hashed...]] }
    """
    result = []
    for c in customers:
        row = []
        email = (c.get("email") or "").strip().lower()
        first_name = (c.get("first_name") or "").strip().lower()
        last_name = (c.get("last_name") or "").strip().lower()
        phone = (c.get("phone") or "").strip().replace(" ", "").replace("-", "")

        if email:
            row.append(_sha256(email))
        else:
            row.append("")

        row.append(_sha256(first_name) if first_name else "")
        row.append(_sha256(last_name) if last_name else "")
        row.append(_sha256(phone) if phone else "")

        result.append(row)
    return result


def sync_customers_to_meta(customers: list[dict], audience_id: Optional[str] = None) -> dict:
    """
    Upload customer list to Meta Custom Audience.
    Returns: { status, added, failed, audience_id }
    """
    import requests

    target_audience = audience_id or META_AUDIENCE_ID
    token = FACEBOOK_ACCESS_TOKEN

    if not token:
        logger.warning("FACEBOOK_ACCESS_TOKEN not set — skipping Meta sync")
        return {"status": "skipped", "reason": "FACEBOOK_ACCESS_TOKEN not set"}

    if not target_audience:
        logger.warning("META_AUDIENCE_ID not set — skipping Meta sync")
        return {"status": "skipped", "reason": "META_AUDIENCE_ID not set"}

    if not customers:
        return {"status": "ok", "added": 0, "failed": 0, "audience_id": target_audience}

    url = f"https://graph.facebook.com/{META_GRAPH_API_VERSION}/{target_audience}/users"

    total_added = 0
    total_failed = 0

    # Upload in batches
    for i in range(0, len(customers), META_BATCH_SIZE):
        batch = customers[i : i + META_BATCH_SIZE]
        user_data = _build_user_data(batch)

        payload = {
            "payload": {
                "schema": ["EMAIL", "FN", "LN", "PHONE"],
                "data": user_data,
            },
            "access_token": token,
        }

        try:
            resp = requests.post(url, json=payload, timeout=60)
            result = resp.json()

            if resp.status_code == 200 and "num_received" in result:
                added = result.get("num_received", 0) - result.get("num_invalid_entries", 0)
                failed = result.get("num_invalid_entries", 0)
                total_added += added
                total_failed += failed
                logger.info(
                    f"Meta batch {i//META_BATCH_SIZE + 1}: added={added}, failed={failed}"
                )
            else:
                error = result.get("error", {}).get("message", "Unknown error")
                logger.error(f"Meta API error: {error}")
                total_failed += len(batch)
                # Don't abort — continue with remaining batches

        except Exception as exc:
            logger.error(f"Meta sync request failed: {exc}")
            total_failed += len(batch)

        # Rate limit: 1 batch per second
        time.sleep(1)

    return {
        "status": "ok",
        "added": total_added,
        "failed": total_failed,
        "audience_id": target_audience,
        "timestamp": datetime.utcnow().isoformat(),
    }


def get_all_crm_customers_for_sync() -> list[dict]:
    """Pull all customers from the CRM database for audience sync."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text

    db_url = os.getenv("DATABASE_URL") or (
        "postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}".format(
            user=os.getenv("POSTGRES_USER", "pureleven"),
            pw=os.getenv("POSTGRES_PASSWORD", ""),
            host=os.getenv("POSTGRES_HOST", "pureleven-postgres"),
            port=os.getenv("POSTGRES_PORT", 5432),
            db=os.getenv("POSTGRES_DB", "pureleven"),
        )
    )
    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        rows = db.execute(text(
            "SELECT email, first_name, last_name, phone FROM crm_customers "
            "WHERE email IS NOT NULL ORDER BY created_at DESC LIMIT 100000"
        )).fetchall()
        return [
            {
                "email": r[0],
                "first_name": r[1] or "",
                "last_name": r[2] or "",
                "phone": r[3] or "",
            }
            for r in rows
        ]
    finally:
        db.close()
        engine.dispose()


async def run_meta_audience_sync() -> dict:
    """
    Full Meta audience sync pipeline:
    1. Fetch all CRM customers
    2. Upload to Meta Custom Audience
    Returns result dict.
    """
    import asyncio

    logger.info("Starting Meta audience sync...")
    try:
        customers = await asyncio.to_thread(get_all_crm_customers_for_sync)
        logger.info(f"Fetched {len(customers)} customers for Meta sync")

        result = await asyncio.to_thread(sync_customers_to_meta, customers)
        logger.info(f"Meta sync result: {result}")
        return result

    except Exception as exc:
        logger.error(f"Meta audience sync failed: {exc}")
        return {"status": "error", "error": str(exc)}
