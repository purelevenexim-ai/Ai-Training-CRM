"""
Abandoned Customer Campaign API endpoints

Endpoints:
- POST /api/abandoned/create-lead: Create a test abandoned lead
- POST /api/abandoned/send-campaign: Send next campaign for a lead
- GET /api/abandoned/status: Check campaign status for a lead
- GET /api/abandoned/unsubscribe: Unsubscribe lead
"""

from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timedelta
import uuid
from app.storage import get_db_connection
from app.services.abandoned_campaign_service import AbandonedCampaignService
from app.config import settings

router = APIRouter()


@router.post("/abandoned/create-lead")
def create_abandoned_lead(
    name: str = Query(..., description="Lead name"),
    email: str = Query(..., description="Lead email"),
    phone: str = Query(..., description="Lead phone"),
    product: str = Query(..., description="Interested product (e.g., turmeric, ghee)"),
    category: str = Query("general", description="Product category"),
    ai_context: str = Query("", description="AI personalization context"),
):
    """Create a test abandoned lead"""
    
    lead_id = f"abandoned-{uuid.uuid4().hex[:12]}"
    now = datetime.utcnow().isoformat()
    
    with get_db_connection() as conn:
        # Check if email already exists
        existing = conn.execute(
            "SELECT id FROM abandoned_leads WHERE email = ?",
            (email,)
        ).fetchone()
        
        if existing:
            raise HTTPException(status_code=400, detail=f"Lead with email {email} already exists")
        
        # Create lead
        conn.execute(
            """
            INSERT INTO abandoned_leads 
            (id, shop_domain, name, email, phone, interest_product, interest_category, engagement_score, ai_context, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lead_id,
                "rwxtic-gz.myshopify.com",  # Default shop domain
                name,
                email,
                phone,
                product,
                category,
                0.0,  # Initial score
                ai_context,
                now,
                now,
            )
        )
        conn.commit()
    
    return {
        "success": True,
        "lead_id": lead_id,
        "email": email,
        "product": product,
        "message": f"Lead created. Ready to send campaign 1."
    }


@router.post("/abandoned/send-campaign")
def send_campaign(
    lead_id: str = Query(..., description="Lead ID"),
):
    """Send next campaign for an abandoned lead"""
    
    result = AbandonedCampaignService.send_campaign(lead_id)
    
    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result.get("reason", "Campaign send failed")
        )
    
    return result


@router.get("/abandoned/status")
def get_campaign_status(
    lead_id: str = Query(..., description="Lead ID"),
):
    """Check campaign status for a lead"""
    
    should_send, next_campaign, reason = AbandonedCampaignService.should_send_campaign(lead_id)
    
    with get_db_connection() as conn:
        lead = conn.execute(
            "SELECT * FROM abandoned_leads WHERE id = ?",
            (lead_id,)
        ).fetchone()
        
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        lead = dict(lead)
        
        # Get campaign history
        campaigns = conn.execute(
            """
            SELECT campaign_num, subject, created_at, opened_at, clicked_at 
            FROM abandoned_campaigns 
            WHERE lead_id = ? 
            ORDER BY campaign_num
            """,
            (lead_id,)
        ).fetchall()
        
        campaigns = [dict(c) for c in campaigns]
    
    return {
        "lead_id": lead_id,
        "email": lead["email"],
        "engagement_score": lead["engagement_score"],
        "segment": "warm" if lead["engagement_score"] >= 40 else "cold",
        "campaigns_sent": len(campaigns),
        "next_campaign_num": next_campaign,
        "should_send_now": should_send,
        "reason": reason,
        "campaign_history": campaigns,
    }


@router.get("/abandoned/unsubscribe")
def unsubscribe_lead(
    lead_id: str = Query(..., description="Lead ID"),
):
    """Unsubscribe an abandoned lead from campaigns"""
    
    now = datetime.utcnow().isoformat()
    
    with get_db_connection() as conn:
        lead = conn.execute(
            "SELECT id, email FROM abandoned_leads WHERE id = ?",
            (lead_id,)
        ).fetchone()
        
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        
        lead = dict(lead)
        
        # Update lead
        conn.execute(
            """
            UPDATE abandoned_leads 
            SET do_not_email = 1, do_not_email_reason = 'user_unsubscribe', updated_at = ?
            WHERE id = ?
            """,
            (now, lead_id)
        )
        conn.commit()
    
    return {
        "success": True,
        "lead_id": lead_id,
        "email": lead["email"],
        "message": "Successfully unsubscribed from campaigns"
    }


@router.post("/abandoned/batch-send")
def batch_send_campaigns(
    shop_domain: str = Query("rwxtic-gz.myshopify.com", description="Shop domain to filter by"),
):
    """
    Run batch campaign sending for all eligible leads
    Called by daily orchestration or cron job
    """
    
    with get_db_connection() as conn:
        # Get all active leads
        leads = conn.execute(
            """
            SELECT id FROM abandoned_leads 
            WHERE do_not_email = 0 
            AND shop_domain = ?
            ORDER BY engagement_score DESC
            """,
            (shop_domain,)
        ).fetchall()
    
    results = []
    for lead_row in leads:
        lead_id = lead_row["id"]
        result = AbandonedCampaignService.send_campaign(lead_id)
        results.append(result)
    
    successful = sum(1 for r in results if r["success"])
    failed = sum(1 for r in results if not r["success"])
    
    return {
        "success": True,
        "shop_domain": shop_domain,
        "total_leads_processed": len(results),
        "campaigns_sent": successful,
        "failed_sends": failed,
        "results": results,
    }


@router.post("/abandoned/track-engagement")
def track_engagement(
    lead_id: str = Query(..., description="Lead ID"),
    event_type: str = Query("opened", description="opened or clicked"),
):
    """Track email engagement for an abandoned lead (open/click)"""
    
    if event_type not in ["opened", "clicked"]:
        raise HTTPException(status_code=400, detail="event_type must be 'opened' or 'clicked'")
    
    success = AbandonedCampaignService.track_engagement(lead_id, event_type)
    
    if not success:
        raise HTTPException(status_code=404, detail="Lead or campaign not found")
    
    return {
        "success": True,
        "lead_id": lead_id,
        "event_type": event_type,
        "message": f"Engagement tracked: {event_type}"
    }
