"""
Shopify Attribution Webhook Handler - Phase 4
Listens for orders/paid → finds active journey instances → records JourneyAttribution
Register webhook: POST https://rwxtic-gz.myshopify.com/admin/api/2024-01/webhooks.json
  topic: orders/paid
  address: https://track.pureleven.com/api/crm/webhooks/shopify/order-paid
"""

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger("pureleven.attribution")

for env_path in ["/opt/pureleven/ai-engine/.env", os.path.join(os.path.dirname(__file__), "..", ".env")]:
    if os.path.exists(env_path):
        from dotenv import load_dotenv
        load_dotenv(env_path)
        break

DATABASE_URL = os.getenv("DATABASE_URL") or (
    "postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}".format(
        user=os.getenv("POSTGRES_USER", "pureleven"),
        pw=os.getenv("POSTGRES_PASSWORD", ""),
        host=os.getenv("POSTGRES_HOST", "pureleven-postgres"),
        port=os.getenv("POSTGRES_PORT", 5432),
        db=os.getenv("POSTGRES_DB", "pureleven"),
    )
)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

try:
    from app.crm_models import Customer, JourneyInstance, JourneyAttribution, Journey
except ImportError:
    Customer = JourneyInstance = JourneyAttribution = Journey = None

router = APIRouter(prefix="/api/crm", tags=["attribution"])

SHOPIFY_WEBHOOK_SECRET = os.getenv("SHOPIFY_WEBHOOK_SECRET", "")


def _verify_shopify_hmac(body: bytes, hmac_header: str) -> bool:
    """Verify HMAC-SHA256 from Shopify webhook header"""
    if not SHOPIFY_WEBHOOK_SECRET:
        logger.warning("SHOPIFY_WEBHOOK_SECRET not set — skipping HMAC verification")
        return True
    digest = hmac.new(
        SHOPIFY_WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).digest()
    import base64
    computed = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(computed, hmac_header)


@router.post("/webhooks/shopify/order-paid")
async def shopify_order_paid(request: Request):
    """
    Receive Shopify orders/paid webhook.
    Finds the customer's active journey instances and records attribution.
    """
    body = await request.body()
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")

    if hmac_header and not _verify_shopify_hmac(body, hmac_header):
        raise HTTPException(status_code=403, detail="Invalid HMAC signature")

    try:
        order = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    shopify_order_id = str(order.get("id", ""))
    email = (order.get("email") or order.get("contact_email") or "").lower().strip()
    order_total = float(order.get("total_price", 0) or 0)
    currency = order.get("currency", "INR")
    order_date = order.get("created_at") or datetime.utcnow().isoformat()

    if not email:
        logger.warning(f"Order {shopify_order_id} has no email — skipping attribution")
        return {"status": "skipped", "reason": "no email"}

    db = SessionLocal()
    attributed_count = 0
    try:
        customer = db.query(Customer).filter(Customer.email == email).first()
        if not customer:
            logger.info(f"No CRM customer found for {email}")
            return {"status": "skipped", "reason": "customer not found"}

        # Find all active or recently completed journey instances for this customer
        active_instances = (
            db.query(JourneyInstance)
            .filter(
                JourneyInstance.customer_id == customer.id,
                JourneyInstance.status.in_(["ACTIVE", "COMPLETED"]),
            )
            .all()
        )

        for instance in active_instances:
            # Check if attribution already recorded for this order + instance
            existing = (
                db.query(JourneyAttribution)
                .filter(
                    JourneyAttribution.journey_instance_id == instance.id,
                    JourneyAttribution.order_id == shopify_order_id,
                )
                .first()
            )
            if existing:
                continue

            attribution = JourneyAttribution(
                journey_id=instance.journey_id,
                journey_instance_id=instance.id,
                customer_id=customer.id,
                order_id=shopify_order_id,
                order_value=order_total,
                attributed_revenue=order_total,  # first-touch: full value
                currency=currency,
                attribution_model="first_touch",
                conversion_date=datetime.fromisoformat(order_date.replace("Z", "+00:00")) if isinstance(order_date, str) else datetime.utcnow(),
            )
            db.add(attribution)

            # Mark instance as COMPLETED if it was ACTIVE
            if instance.status == "ACTIVE":
                instance.status = "COMPLETED"
                instance.completed_at = datetime.utcnow()
                instance.result_data = {
                    **(instance.result_data or {}),
                    "converted": True,
                    "order_id": shopify_order_id,
                    "revenue": order_total,
                }

            attributed_count += 1

        db.commit()
        logger.info(f"Order {shopify_order_id}: attributed to {attributed_count} journey instance(s)")

        # Publish Redis metric
        try:
            import redis as _r
            r = _r.Redis.from_url(os.getenv("REDIS_URL", "redis://pureleven-redis:6379/0"), decode_responses=True)
            for instance in active_instances:
                r.publish("pubsub:metrics", json.dumps({
                    "type": "journey_event",
                    "event_type": "converted",
                    "journey_id": instance.journey_id,
                    "data": {
                        "customer_email": email,
                        "order_id": shopify_order_id,
                        "revenue": order_total,
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                }))
        except Exception as re:
            logger.warning(f"Redis publish failed: {re}")

        return {
            "status": "ok",
            "order_id": shopify_order_id,
            "customer_email": email,
            "attributed_instances": attributed_count,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Attribution error for order {shopify_order_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()
