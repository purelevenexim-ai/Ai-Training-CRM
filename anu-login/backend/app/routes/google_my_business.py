"""
Google My Business API endpoints

Endpoints:
- POST /api/gmb/post-review: Post a customer review to GMB
- POST /api/gmb/post-offer: Post a promotional offer
- POST /api/gmb/post-product: Post product update
- GET /api/gmb/pending-posts: Get pending posts
- POST /api/gmb/publish-post: Publish a post
- GET /api/gmb/analytics: Get GMB performance metrics
"""

from fastapi import APIRouter, Header, HTTPException, Query
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.config import settings
from app.review_journey_engine import record_review_submission
from app.services.google_my_business import GoogleMyBusinessService
from app.storage import get_db_connection

router = APIRouter()


def _normalize_phone(raw: str | None) -> str:
    if not raw:
        return ""
    digits = "".join(c for c in str(raw) if c.isdigit())
    if len(digits) == 10:
        return "91" + digits
    if len(digits) == 12 and digits.startswith("91"):
        return digits
    return digits


class ReviewWebhookPayload(BaseModel):
    customer_id: str | None = None
    phone: str | None = None
    email: str | None = None
    rating: int = 5
    review_text: str = ""
    source: str = "google"


@router.post("/gmb/post-review")
def post_customer_review(
    customer_id: str = Query(..., description="Journey customer ID"),
    review_text: str = Query(..., description="Customer review/testimonial"),
    rating: int = Query(5, description="Star rating (1-5)"),
):
    """Post a customer review/testimonial to GMB"""
    
    if not (1 <= rating <= 5):
        raise HTTPException(status_code=400, detail="Rating must be between 1-5")
    
    result = GoogleMyBusinessService.post_customer_review_to_gmb(
        customer_id,
        review_text,
        rating
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    
    return result


@router.post("/gmb/post-offer")
def post_promotional_offer(
    title: str = Query(..., description="Offer title e.g., '20% Off Organic Turmeric'"),
    description: str = Query(..., description="Offer description"),
    discount: int = Query(0, description="Discount percentage"),
    days_valid: int = Query(1, description="Days the offer is valid"),
):
    """Post a promotional offer to GMB"""
    
    expiry = (datetime.utcnow() + timedelta(days=days_valid)).isoformat()
    
    result = GoogleMyBusinessService.post_offer_to_gmb(
        title,
        description,
        discount,
        expiry
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    
    return result


@router.post("/gmb/post-product")
def post_product_update(
    product_name: str = Query(..., description="Product name"),
    description: str = Query(..., description="Product description"),
    price: float = Query(..., description="Product price"),
    image_url: str = Query(None, description="Product image URL"),
):
    """Post a product update to GMB"""
    
    result = GoogleMyBusinessService.post_product_update_to_gmb(
        product_name,
        description,
        price,
        image_url
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    
    return result


@router.get("/gmb/pending-posts")
def get_pending_gmb_posts():
    """Get all pending GMB posts waiting to be published"""
    
    posts = GoogleMyBusinessService.get_pending_posts()
    
    return {
        "success": True,
        "pending_count": len(posts),
        "posts": posts
    }


@router.post("/gmb/publish-post")
def publish_gmb_post(
    post_id: str = Query(..., description="GMB post ID to publish"),
):
    """Publish a pending GMB post"""
    
    # Verify post exists
    with get_db_connection() as conn:
        post = conn.execute(
            "SELECT id FROM gmb_posts WHERE id = ?",
            (post_id,)
        ).fetchone()
        
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
    
    result = GoogleMyBusinessService.publish_post(post_id)
    
    return result


@router.get("/gmb/analytics")
def get_gmb_performance():
    """Get Google My Business performance metrics"""
    
    analytics = GoogleMyBusinessService.get_gmb_analytics()
    
    return {
        "success": True,
        "analytics": analytics,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.post("/gmb/auto-post-daily-offer")
def trigger_daily_offer_post():
    """Manually trigger daily offer post to GMB"""
    
    result = GoogleMyBusinessService.auto_post_daily_offer()
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message"))
    
    return result


@router.post("/gmb/auto-post-reviews")
def trigger_auto_post_reviews():
    """Manually trigger auto-posting of top reviews to GMB"""
    
    result = GoogleMyBusinessService.auto_post_top_reviews()
    
    return result


@router.post("/gmb/webhooks/review-submitted")
def gmb_review_submitted_webhook(
    payload: ReviewWebhookPayload,
    token: str = Query(default=""),
    x_admin_secret: str = Header(default="", alias="x-admin-secret"),
):
    """
    Intake webhook for live Google review submission events.

    Security:
    - If ANU_LOGIN_ADMIN_SECRET is set, caller must pass either:
      - query param token=<secret>
      - or x-admin-secret header
    """
    if settings.admin_secret:
        if token != settings.admin_secret and x_admin_secret != settings.admin_secret:
            raise HTTPException(status_code=403, detail="Unauthorized webhook token")

    if not (1 <= payload.rating <= 5):
        raise HTTPException(status_code=422, detail="Rating must be 1-5")

    with get_db_connection() as conn:
        customer_row = None
        if payload.customer_id:
            customer_row = conn.execute(
                "SELECT id FROM journey_customers WHERE id = ?",
                (payload.customer_id,),
            ).fetchone()

        if not customer_row and payload.phone:
            normalized = _normalize_phone(payload.phone)
            candidates = [normalized]
            if normalized.startswith("91") and len(normalized) == 12:
                candidates.append(normalized[2:])
            customer_row = conn.execute(
                """
                SELECT id FROM journey_customers
                WHERE phone IN (?, ?)
                ORDER BY delivered_at DESC
                LIMIT 1
                """,
                (candidates[0], candidates[1] if len(candidates) > 1 else candidates[0]),
            ).fetchone()

        if not customer_row and payload.email:
            customer_row = conn.execute(
                """
                SELECT id FROM journey_customers
                WHERE lower(email) = lower(?) OR lower(email_address) = lower(?)
                ORDER BY delivered_at DESC
                LIMIT 1
                """,
                (payload.email, payload.email),
            ).fetchone()

        if not customer_row:
            raise HTTPException(status_code=404, detail="Customer not found for webhook payload")

        customer_id = str(customer_row["id"])
        record_review_submission(
            conn=conn,
            customer_id=customer_id,
            rating=payload.rating,
            review_text=payload.review_text,
            channel=payload.source or "google",
        )

    return {"ok": True, "customer_id": customer_id, "source": payload.source}
