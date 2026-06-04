"""
Google Audience Sync - Phase 4
Syncs CRM customers to Google Ads Customer Match audiences.
Uses Google Ads API v17 — requires Basic Access tier (not Test Account).

Requires env vars:
  GOOGLE_ADS_DEVELOPER_TOKEN  — from ads.google.com/nav/selectaccount → API Center
  GOOGLE_ADS_CLIENT_ID        — OAuth2 client ID from Google Cloud Console
  GOOGLE_ADS_CLIENT_SECRET    — OAuth2 client secret
  GOOGLE_ADS_REFRESH_TOKEN    — long-lived refresh token from OAuth flow
  GOOGLE_ADS_CUSTOMER_ID      — 7225234563 (Pure Leven account)
  GOOGLE_AUDIENCE_LIST_ID     — Customer Match user list resource name
"""

import hashlib
import logging
import os
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger("pureleven.google_sync")

GOOGLE_ADS_DEVELOPER_TOKEN = os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN", "")
GOOGLE_ADS_CLIENT_ID = os.getenv("GOOGLE_ADS_CLIENT_ID", "")
GOOGLE_ADS_CLIENT_SECRET = os.getenv("GOOGLE_ADS_CLIENT_SECRET", "")
GOOGLE_ADS_REFRESH_TOKEN = os.getenv("GOOGLE_ADS_REFRESH_TOKEN", "")
GOOGLE_ADS_CUSTOMER_ID = os.getenv("GOOGLE_ADS_CUSTOMER_ID", "7225234563")
GOOGLE_AUDIENCE_LIST_ID = os.getenv("GOOGLE_AUDIENCE_LIST_ID", "")
GOOGLE_BATCH_SIZE = 1000  # Google recommends ≤ 1000 per request


def _sha256_normalize(value: str) -> str:
    """Normalize and hash a string per Google Customer Match requirements."""
    return hashlib.sha256(value.strip().lower().encode("utf-8")).hexdigest()


def _get_google_ads_client():
    """Build a Google Ads API client from env credentials."""
    try:
        from google.ads.googleads.client import GoogleAdsClient

        config = {
            "developer_token": GOOGLE_ADS_DEVELOPER_TOKEN,
            "client_id": GOOGLE_ADS_CLIENT_ID,
            "client_secret": GOOGLE_ADS_CLIENT_SECRET,
            "refresh_token": GOOGLE_ADS_REFRESH_TOKEN,
            "use_proto_plus": True,
        }
        return GoogleAdsClient.load_from_dict(config)
    except ImportError:
        logger.error("google-ads package not installed. Run: pip install google-ads")
        return None
    except Exception as exc:
        logger.error(f"Failed to build Google Ads client: {exc}")
        return None


def _build_user_identifiers(customers: list[dict]) -> list:
    """Build UserIdentifier protos for Customer Match upload."""
    try:
        from google.ads.googleads.client import GoogleAdsClient
        from google.ads.googleads.v17.common.types.user_data import (
            UserIdentifier,
            CustomerMatchUserListMetadata,
        )
    except ImportError:
        return []

    identifiers = []
    for c in customers:
        email = (c.get("email") or "").strip().lower()
        phone = (c.get("phone") or "").strip().replace(" ", "").replace("-", "")

        if email:
            uid = UserIdentifier()
            uid.hashed_email = _sha256_normalize(email)
            identifiers.append(uid)

        if phone:
            uid = UserIdentifier()
            uid.hashed_phone_number = _sha256_normalize(phone)
            identifiers.append(uid)

    return identifiers


def sync_customers_to_google(
    customers: list[dict],
    user_list_id: Optional[str] = None,
    customer_id: Optional[str] = None,
) -> dict:
    """
    Upload customer list to Google Ads Customer Match user list.
    Returns: { status, added, failed, user_list_id }
    """
    target_list = user_list_id or GOOGLE_AUDIENCE_LIST_ID
    cid = customer_id or GOOGLE_ADS_CUSTOMER_ID

    if not GOOGLE_ADS_DEVELOPER_TOKEN:
        logger.warning("GOOGLE_ADS_DEVELOPER_TOKEN not set — skipping Google sync")
        return {"status": "skipped", "reason": "GOOGLE_ADS_DEVELOPER_TOKEN not set"}

    if not target_list:
        logger.warning("GOOGLE_AUDIENCE_LIST_ID not set — skipping Google sync")
        return {"status": "skipped", "reason": "GOOGLE_AUDIENCE_LIST_ID not set"}

    client = _get_google_ads_client()
    if not client:
        return {"status": "error", "reason": "Failed to build Google Ads client"}

    if not customers:
        return {"status": "ok", "added": 0, "failed": 0, "user_list_id": target_list}

    try:
        service = client.get_service("UserDataService")
        total_added = 0
        total_failed = 0

        for i in range(0, len(customers), GOOGLE_BATCH_SIZE):
            batch = customers[i : i + GOOGLE_BATCH_SIZE]

            # Build request
            from google.ads.googleads.v17.services.types.user_data_service import (
                UploadUserDataRequest,
                UserDataOperation,
                UserData,
            )
            from google.ads.googleads.v17.common.types.user_data import CustomerMatchUserListMetadata

            operations = []
            for c in batch:
                email = (c.get("email") or "").strip().lower()
                phone = (c.get("phone") or "").strip()

                user_data = UserData()
                if email:
                    uid = client.get_type("UserIdentifier")
                    uid.hashed_email = _sha256_normalize(email)
                    user_data.user_identifiers.append(uid)
                if phone:
                    uid = client.get_type("UserIdentifier")
                    uid.hashed_phone_number = _sha256_normalize(phone)
                    user_data.user_identifiers.append(uid)

                if user_data.user_identifiers:
                    op = UserDataOperation()
                    op.create = user_data
                    operations.append(op)

            metadata = CustomerMatchUserListMetadata()
            metadata.user_list = target_list

            request = UploadUserDataRequest()
            request.customer_id = cid.replace("-", "")
            request.operations = operations
            request.customer_match_user_list_metadata = metadata

            response = service.upload_user_data(request=request)
            total_added += len(operations)
            logger.info(
                f"Google batch {i//GOOGLE_BATCH_SIZE + 1}: uploaded {len(operations)} records"
            )

            # Rate limit
            time.sleep(1)

        return {
            "status": "ok",
            "added": total_added,
            "failed": total_failed,
            "user_list_id": target_list,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as exc:
        logger.error(f"Google Ads API error: {exc}")
        return {"status": "error", "error": str(exc)}


def get_all_crm_customers_for_google_sync() -> list[dict]:
    """Pull CRM customers from database (reuse logic from meta sync)."""
    try:
        from app.meta_audience_sync import get_all_crm_customers_for_sync
        return get_all_crm_customers_for_sync()
    except ImportError:
        pass

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
        return [{"email": r[0], "first_name": r[1] or "", "last_name": r[2] or "", "phone": r[3] or ""} for r in rows]
    finally:
        db.close()
        engine.dispose()


async def run_google_audience_sync() -> dict:
    """
    Full Google Customer Match sync pipeline:
    1. Fetch all CRM customers
    2. Upload to Google Ads Customer Match list
    Returns result dict.
    """
    import asyncio

    logger.info("Starting Google audience sync...")
    try:
        customers = await asyncio.to_thread(get_all_crm_customers_for_google_sync)
        logger.info(f"Fetched {len(customers)} customers for Google sync")

        result = await asyncio.to_thread(sync_customers_to_google, customers)
        logger.info(f"Google sync result: {result}")
        return result

    except Exception as exc:
        logger.error(f"Google audience sync failed: {exc}")
        return {"status": "error", "error": str(exc)}
