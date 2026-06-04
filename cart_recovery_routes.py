"""
Cart Recovery API Routes
E-commerce abandonment tracking and recovery management
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from database import SessionLocal
from cart_recovery import (
    CartAbandonmentTracker,
    CartRecoveryEmailManager,
    CartRecoveryMetrics,
    CartRecoveryPhase
)

router = APIRouter(prefix="/api/crm", tags=["cart_recovery"])


# Pydantic Models
class CartAbandonmentCreate(BaseModel):
    """Create cart abandonment record"""
    customer_email: str
    customer_id: Optional[str] = None
    cart_token: Optional[str] = None
    cart_value: Optional[float] = None
    items_count: int = 0
    cart_items: Optional[List[dict]] = None
    reason: str = "checkout"


class CartAbandonmentResponse(BaseModel):
    """Cart abandonment detail"""
    id: str
    customer_email: str
    cart_value: float
    items_count: int
    abandoned_at: datetime
    recovery_status: str
    recovery_attempts: int
    recovered_value: float
    recovered_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class CartRecoveryTemplateCreate(BaseModel):
    """Create recovery email template"""
    name: str
    subject: str
    template_html: str
    trigger_hours_after_abandon: int
    cta_text: str = "Complete Your Purchase"
    include_discount_code: bool = False
    discount_code: Optional[str] = None
    discount_percentage: Optional[int] = None


class CartRecoveryTemplateResponse(BaseModel):
    """Recovery template detail"""
    id: str
    name: str
    subject: str
    trigger_hours_after_abandon: int
    is_active: bool
    send_count: int
    click_count: int
    recovery_count: int
    
    class Config:
        from_attributes = True


# ============ Abandonment Tracking ============

@router.post("/carts/abandoned", response_model=dict)
def track_cart_abandonment(
    data: CartAbandonmentCreate,
    db: Session = Depends(SessionLocal)
):
    """
    Track new abandoned cart
    
    Triggers:
    - Webhook from Shopify when checkout is abandoned
    - Manual API call for custom implementations
    
    Returns immediately and schedules recovery in background
    """
    
    tracker = CartAbandonmentTracker(db)
    
    try:
        result = tracker.track_cart_abandonment(
            customer_email=data.customer_email,
            customer_id=data.customer_id,
            cart_token=data.cart_token,
            cart_value=data.cart_value,
            items_count=data.items_count,
            cart_items=data.cart_items,
            reason=data.reason
        )
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Abandonment tracking error: {str(e)}")


@router.get("/carts/abandoned", response_model=dict)
def list_abandoned_carts(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "abandoned_at",  # abandoned_at, cart_value
    db: Session = Depends(SessionLocal)
):
    """
    List abandoned carts (paginated, filtered)
    
    Parameters:
    - status: pending, recovered, expired, lost
    - skip: Offset
    - limit: Max results
    - sort_by: Sort field
    
    Returns: Paginated list with recovery status
    """
    
    from crm_models import CartAbandonment
    
    query = db.query(CartAbandonment)
    
    if status:
        query = query.filter(CartAbandonment.recovery_status == status)
    
    total = query.count()
    
    if sort_by == "cart_value":
        query = query.order_by(CartAbandonment.cart_value.desc())
    else:
        query = query.order_by(CartAbandonment.abandoned_at.desc())
    
    items = query.offset(skip).limit(limit).all()
    
    return {
        'total': total,
        'skip': skip,
        'limit': limit,
        'items': [
            {
                'id': c.id,
                'customer_id': c.customer_id,
                'cart_value': c.cart_value,
                'items_count': c.items_count,
                'abandoned_at': c.abandoned_at,
                'status': c.recovery_status,
                'recovery_attempts': c.recovery_attempts
            }
            for c in items
        ]
    }


@router.get("/carts/abandoned/{cart_id}", response_model=dict)
def get_abandoned_cart(
    cart_id: str,
    db: Session = Depends(SessionLocal)
):
    """Get detailed cart abandonment info"""
    
    from crm_models import CartAbandonment
    
    cart = db.query(CartAbandonment).filter(
        CartAbandonment.id == cart_id
    ).first()
    
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    return {
        'id': cart.id,
        'customer_id': cart.customer_id,
        'cart_value': cart.cart_value,
        'items_count': cart.items_count,
        'items': cart.cart_items,
        'abandoned_at': cart.abandoned_at,
        'status': cart.recovery_status,
        'recovery_attempts': cart.recovery_attempts,
        'recovered_value': cart.recovered_value,
        'recovered_at': cart.recovered_at,
        'emails_sent': cart.recovery_emails_sent
    }


# ============ Recovery Management ============

@router.post("/carts/abandoned/{cart_id}/mark-recovered")
def mark_cart_recovered(
    cart_id: str,
    recovered_value: Optional[float] = None,
    recovery_campaign_id: Optional[str] = None,
    db: Session = Depends(SessionLocal)
):
    """
    Mark cart as recovered (customer completed purchase)
    
    Can be called from:
    - Order creation webhook
    - Manual admin action
    - N8N recovery campaign completion
    """
    
    tracker = CartAbandonmentTracker(db)
    
    try:
        result = tracker.mark_recovered(
            cart_id,
            recovered_value,
            recovery_campaign_id
        )
        
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
        
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/carts/abandoned/{cart_id}/mark-expired")
def mark_cart_expired(
    cart_id: str,
    db: Session = Depends(SessionLocal)
):
    """Mark cart as expired (recovery window passed)"""
    
    tracker = CartAbandonmentTracker(db)
    result = tracker.mark_expired(cart_id)
    
    if 'error' in result:
        raise HTTPException(status_code=404, detail=result['error'])
    
    return result


# ============ Recovery Scheduling ============

@router.get("/carts/recovery/scheduled")
def get_recovery_schedule(
    phase: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(SessionLocal)
):
    """
    Get carts scheduled for recovery in specific phase
    
    Phases:
    - immediate: 1 hour after abandon
    - urgent: 24 hours after abandon
    - last_chance: 72 hours after abandon
    
    Use this to schedule N8N workflows
    """
    
    tracker = CartAbandonmentTracker(db)
    
    try:
        if phase:
            phase_enum = CartRecoveryPhase(phase)
        else:
            phase_enum = None
        
        carts = tracker.get_recoverable_carts(phase_enum, limit)
        
        return {
            'count': len(carts),
            'phase': phase,
            'carts': carts
        }
    
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid phase. Must be: immediate, urgent, or last_chance"
        )


# ============ Email Templates ============

@router.post("/recovery-templates", response_model=dict)
def create_recovery_template(
    data: CartRecoveryTemplateCreate,
    db: Session = Depends(SessionLocal)
):
    """
    Create cart recovery email template
    
    Templates are assigned to phases (1h, 24h, 72h after abandon)
    """
    
    from crm_models import CartRecoveryTemplate
    import uuid
    
    template = CartRecoveryTemplate(
        id=str(uuid.uuid4()),
        name=data.name,
        subject=data.subject,
        template_html=data.template_html,
        trigger_hours_after_abandon=data.trigger_hours_after_abandon,
        cta_text=data.cta_text,
        include_discount_code=data.include_discount_code,
        discount_code=data.discount_code,
        discount_percentage=data.discount_percentage
    )
    
    db.add(template)
    db.commit()
    
    return {
        'id': template.id,
        'name': template.name,
        'status': 'created'
    }


@router.get("/recovery-templates")
def list_recovery_templates(
    is_active: bool = True,
    db: Session = Depends(SessionLocal)
):
    """List available recovery email templates"""
    
    from crm_models import CartRecoveryTemplate
    
    templates = db.query(CartRecoveryTemplate).filter(
        CartRecoveryTemplate.is_active == is_active
    ).all()
    
    return [
        {
            'id': t.id,
            'name': t.name,
            'subject': t.subject,
            'trigger_hours': t.trigger_hours_after_abandon,
            'send_count': t.send_count,
            'recovery_count': t.recovery_count
        }
        for t in templates
    ]


@router.get("/recovery-templates/{template_id}")
def get_recovery_template(
    template_id: str,
    db: Session = Depends(SessionLocal)
):
    """Get full template details (for N8N email sending)"""
    
    from crm_models import CartRecoveryTemplate
    
    template = db.query(CartRecoveryTemplate).filter(
        CartRecoveryTemplate.id == template_id
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return {
        'id': template.id,
        'subject': template.subject,
        'template_html': template.template_html,
        'template_text': template.template_text,
        'cta_text': template.cta_text,
        'discount_code': template.discount_code,
        'discount_percentage': template.discount_percentage
    }


# ============ Email Campaigns ============

@router.post("/recovery-campaigns")
def create_recovery_campaign(
    cart_id: str,
    customer_email: str,
    template_id: str,
    db: Session = Depends(SessionLocal)
):
    """Create recovery email campaign"""
    
    manager = CartRecoveryEmailManager(db)
    
    try:
        campaign = manager.create_recovery_campaign(
            cart_id,
            customer_email,
            template_id
        )
        
        return campaign
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/recovery-campaigns/{campaign_id}/record-sent")
def record_email_sent(
    campaign_id: str,
    db: Session = Depends(SessionLocal)
):
    """Record that recovery email was sent"""
    
    manager = CartRecoveryEmailManager(db)
    result = manager.record_email_sent(campaign_id)
    
    if 'error' in result:
        raise HTTPException(status_code=404, detail=result['error'])
    
    return result


@router.post("/recovery-campaigns/{campaign_id}/record-opened")
def record_email_opened(
    campaign_id: str,
    db: Session = Depends(SessionLocal)
):
    """Record that recovery email was opened (pixel tracking)"""
    
    manager = CartRecoveryEmailManager(db)
    result = manager.record_email_opened(campaign_id)
    
    if 'error' in result:
        raise HTTPException(status_code=404, detail=result['error'])
    
    return result


@router.post("/recovery-campaigns/{campaign_id}/record-clicked")
def record_email_clicked(
    campaign_id: str,
    db: Session = Depends(SessionLocal)
):
    """Record that recovery email link was clicked"""
    
    manager = CartRecoveryEmailManager(db)
    result = manager.record_email_clicked(campaign_id)
    
    if 'error' in result:
        raise HTTPException(status_code=404, detail=result['error'])
    
    return result


# ============ Analytics ============

@router.get("/cart-recovery/analytics/summary")
def get_recovery_analytics(
    db: Session = Depends(SessionLocal)
):
    """
    Cart recovery overview metrics
    
    Returns:
    - Total abandonments
    - Recovery rate
    - Total value lost/recovered
    - Average recovery time
    """
    
    tracker = CartAbandonmentTracker(db)
    analytics = tracker.get_recovery_analytics()
    
    return analytics


@router.get("/cart-recovery/analytics/funnel")
def get_recovery_funnel(
    db: Session = Depends(SessionLocal)
):
    """
    Recovery email funnel metrics
    
    Shows: sent → delivered → opened → clicked → converted
    """
    
    metrics = CartRecoveryMetrics(db)
    funnel = metrics.get_funnel_metrics()
    
    return funnel


@router.get("/cart-recovery/health")
def cart_recovery_health(
    db: Session = Depends(SessionLocal)
):
    """Health check for cart recovery service"""
    
    try:
        from crm_models import CartAbandonment, CartRecoveryCampaign
        
        abandonments = db.query(CartAbandonment).count()
        campaigns = db.query(CartRecoveryCampaign).count()
        
        return {
            "status": "ok",
            "service": "cart_recovery",
            "total_abandonments": abandonments,
            "total_campaigns": campaigns
        }
    
    except Exception as e:
        return {
            "status": "error",
            "service": "cart_recovery",
            "message": str(e)
        }
