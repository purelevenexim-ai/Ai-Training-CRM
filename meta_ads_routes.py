"""
Meta Ads API Routes
Facebook Pixel tracking, custom audiences, and conversion management
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel
from database import SessionLocal
from meta_ads_integration import (
    MetaPixelEventTracker,
    MetaAudienceManager,
    MetaConversionTracker,
    MetaEventType,
    MetaAudienceType
)

router = APIRouter(prefix="/api/crm", tags=["meta_ads"])


# ============ Pydantic Models ============

class CustomerData(BaseModel):
    """Customer PII for Meta tracking"""
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None


class MetaPixelEvent(BaseModel):
    """Pixel event for tracking"""
    event_name: str  # PageView, Purchase, Lead, Contact, etc
    customer_data: Optional[CustomerData] = None
    content_data: Optional[Dict] = None
    custom_data: Optional[Dict] = None
    event_id: Optional[str] = None


class MetaAudienceCreate(BaseModel):
    """Create custom audience"""
    audience_name: str
    audience_description: Optional[str] = None


class MetaAudienceSync(BaseModel):
    """Sync customers to audience"""
    audience_id: str
    filter_by_status: Optional[str] = None  # lead, customer, prospect


class MetaConversionTrack(BaseModel):
    """Track offline conversion"""
    customer_id: str
    event_name: str
    value: Optional[float] = None
    currency: str = "INR"
    status: Optional[str] = None


# ============ Pixel Event Tracking (4 endpoints) ============

@router.post("/meta/pixel/track")
def track_pixel_event(
    data: MetaPixelEvent,
    db: Session = Depends(SessionLocal)
):
    """
    Send event to Meta Conversions API (server-side pixel tracking)
    
    Events: PageView, ViewContent, Search, AddToCart, Purchase, Lead, Contact
    
    Returns:
    {
        'status': 'success' | 'error',
        'event_id': str,
        'code': int
    }
    """
    
    import os
    
    pixel_id = os.getenv('META_PIXEL_ID')
    access_token = os.getenv('META_ACCESS_TOKEN')
    
    if not pixel_id or not access_token:
        raise HTTPException(
            status_code=500,
            detail="META_PIXEL_ID and META_ACCESS_TOKEN not configured"
        )
    
    tracker = MetaPixelEventTracker(pixel_id, access_token)
    
    result = tracker.track_event(
        event_name=data.event_name,
        customer_data=data.customer_data.dict() if data.customer_data else None,
        content_data=data.content_data,
        custom_data=data.custom_data,
        event_id=data.event_id
    )
    
    return result


@router.post("/meta/pixel/track/{event_type}")
def track_event_by_type(
    event_type: str,
    customer_id: Optional[str] = None,
    value: Optional[float] = None,
    db: Session = Depends(SessionLocal)
):
    """
    Quick event tracking by type
    
    Event types: page_view, view_content, add_to_cart, purchase, lead, contact
    """
    
    import os
    
    pixel_id = os.getenv('META_PIXEL_ID')
    access_token = os.getenv('META_ACCESS_TOKEN')
    
    if not pixel_id or not access_token:
        raise HTTPException(status_code=500, detail="Meta credentials not configured")
    
    tracker = MetaPixelEventTracker(pixel_id, access_token)
    
    # Map event types
    event_map = {
        'page_view': 'PageView',
        'view_content': 'ViewContent',
        'add_to_cart': 'AddToCart',
        'purchase': 'Purchase',
        'lead': 'Lead',
        'contact': 'Contact'
    }
    
    event_name = event_map.get(event_type.lower(), event_type)
    
    # Get customer if provided
    customer_data = None
    if customer_id:
        from crm_models import Customer
        customer = db.query(Customer).filter(
            Customer.id == customer_id
        ).first()
        
        if customer:
            customer_data = {
                'em': customer.email,
                'ph': customer.phone,
                'fn': customer.first_name,
                'ln': customer.last_name
            }
    
    custom_data = {'value': value} if value else {}
    
    result = tracker.track_event(
        event_name=event_name,
        customer_data=customer_data,
        custom_data=custom_data
    )
    
    return result


@router.get("/meta/pixel/health")
def pixel_health():
    """Health check for pixel tracking"""
    
    import os
    
    pixel_id = os.getenv('META_PIXEL_ID')
    
    if pixel_id:
        return {
            'status': 'ok',
            'service': 'meta_pixel',
            'pixel_id': pixel_id
        }
    else:
        return {
            'status': 'error',
            'service': 'meta_pixel',
            'message': 'Pixel not configured'
        }


# ============ Custom Audiences (6 endpoints) ============

@router.post("/meta/audiences")
def create_audience(
    data: MetaAudienceCreate,
    db: Session = Depends(SessionLocal)
):
    """
    Create custom audience in Meta
    
    For pixel data, CRM data, or lookalike audiences
    """
    
    import os
    
    ad_account_id = os.getenv('META_AD_ACCOUNT_ID')
    access_token = os.getenv('META_ACCESS_TOKEN')
    
    if not ad_account_id or not access_token:
        raise HTTPException(
            status_code=500,
            detail="META_AD_ACCOUNT_ID and META_ACCESS_TOKEN not configured"
        )
    
    manager = MetaAudienceManager(ad_account_id, access_token)
    
    result = manager.create_custom_audience(
        audience_name=data.audience_name,
        audience_description=data.audience_description
    )
    
    if result.get('status') == 'created':
        return result
    else:
        raise HTTPException(status_code=400, detail=result.get('message'))


@router.get("/meta/audiences")
def list_audiences(
    db: Session = Depends(SessionLocal)
):
    """
    List Meta custom audiences
    
    Returns audience IDs and names for reference
    """
    
    from crm_models import MetaAudience
    
    audiences = db.query(MetaAudience).filter(
        MetaAudience.is_active == True
    ).order_by(MetaAudience.created_at.desc()).all()
    
    return {
        'total': len(audiences),
        'audiences': [
            {
                'id': a.id,
                'audience_id': a.meta_audience_id,
                'name': a.audience_name,
                'type': a.audience_type,
                'customer_count': a.customer_count,
                'created_at': a.created_at
            }
            for a in audiences
        ]
    }


@router.get("/meta/audiences/{audience_id}")
def get_audience(
    audience_id: str,
    db: Session = Depends(SessionLocal)
):
    """Get audience stats"""
    
    import os
    
    access_token = os.getenv('META_ACCESS_TOKEN')
    
    if not access_token:
        raise HTTPException(status_code=500, detail="Meta token not configured")
    
    manager = MetaAudienceManager("", access_token)
    
    stats = manager.get_audience_stats(audience_id)
    
    return stats


@router.post("/meta/audiences/{audience_id}/sync")
def sync_to_audience(
    audience_id: str,
    data: MetaAudienceSync,
    db: Session = Depends(SessionLocal)
):
    """
    Sync CRM customers to Meta custom audience
    
    Upload customer list to audience for targeting
    
    Returns: {
        'status': 'synced',
        'count': int,
        'failed': int
    }
    """
    
    import os
    
    pixel_id = os.getenv('META_PIXEL_ID')
    ad_account_id = os.getenv('META_AD_ACCOUNT_ID')
    access_token = os.getenv('META_ACCESS_TOKEN')
    
    if not all([pixel_id, ad_account_id, access_token]):
        raise HTTPException(
            status_code=500,
            detail="Meta credentials not configured"
        )
    
    pixel_tracker = MetaPixelEventTracker(pixel_id, access_token)
    audience_manager = MetaAudienceManager(ad_account_id, access_token)
    conversion_tracker = MetaConversionTracker(db, pixel_tracker, audience_manager)
    
    result = conversion_tracker.sync_customers_to_audience(
        audience_id=audience_id,
        filter_by_status=data.filter_by_status
    )
    
    if result.get('status') in ['synced', 'no_customers']:
        return result
    else:
        raise HTTPException(status_code=400, detail=result.get('message'))


@router.post("/meta/audiences/{audience_id}/add-users")
def add_users_to_audience(
    audience_id: str,
    customers: List[Dict],
    db: Session = Depends(SessionLocal)
):
    """
    Add customer list to audience
    
    Body: List of {email, phone, first_name, last_name}
    """
    
    import os
    
    access_token = os.getenv('META_ACCESS_TOKEN')
    
    if not access_token:
        raise HTTPException(status_code=500, detail="Meta token not configured")
    
    manager = MetaAudienceManager("", access_token)
    
    result = manager.add_users_to_audience(audience_id, customers)
    
    return result


# ============ Conversion Tracking (5 endpoints) ============

@router.post("/meta/conversions/track")
def track_conversion(
    data: MetaConversionTrack,
    db: Session = Depends(SessionLocal)
):
    """
    Track offline conversion and sync to Meta
    
    Logs purchase, lead, contact, or custom conversion
    Sends to Meta for attribution
    """
    
    import os
    
    pixel_id = os.getenv('META_PIXEL_ID')
    ad_account_id = os.getenv('META_AD_ACCOUNT_ID')
    access_token = os.getenv('META_ACCESS_TOKEN')
    
    if not all([pixel_id, ad_account_id, access_token]):
        raise HTTPException(
            status_code=500,
            detail="Meta credentials not configured"
        )
    
    pixel_tracker = MetaPixelEventTracker(pixel_id, access_token)
    audience_manager = MetaAudienceManager(ad_account_id, access_token)
    conversion_tracker = MetaConversionTracker(db, pixel_tracker, audience_manager)
    
    result = conversion_tracker.track_conversion(
        customer_id=data.customer_id,
        event_name=data.event_name,
        value=data.value,
        currency=data.currency,
        status=data.status
    )
    
    if result.get('error'):
        raise HTTPException(status_code=400, detail=result['error'])
    
    return result


@router.get("/meta/conversions")
def list_conversions(
    customer_id: Optional[str] = None,
    event_name: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(SessionLocal)
):
    """List tracked conversions"""
    
    from crm_models import MetaConversion
    
    query = db.query(MetaConversion)
    
    if customer_id:
        query = query.filter(MetaConversion.customer_id == customer_id)
    
    if event_name:
        query = query.filter(MetaConversion.event_name == event_name)
    
    total = query.count()
    
    conversions = query.order_by(
        MetaConversion.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    return {
        'total': total,
        'conversions': [
            {
                'id': c.id,
                'customer_id': c.customer_id,
                'event_name': c.event_name,
                'value': c.value,
                'currency': c.currency,
                'synced_to_meta': c.synced_to_meta,
                'created_at': c.created_at
            }
            for c in conversions
        ]
    }


@router.get("/meta/conversions/{conversion_id}")
def get_conversion(
    conversion_id: str,
    db: Session = Depends(SessionLocal)
):
    """Get conversion details"""
    
    from crm_models import MetaConversion
    
    conversion = db.query(MetaConversion).filter(
        MetaConversion.id == conversion_id
    ).first()
    
    if not conversion:
        raise HTTPException(status_code=404, detail="Conversion not found")
    
    return {
        'id': conversion.id,
        'customer_id': conversion.customer_id,
        'event_name': conversion.event_name,
        'value': conversion.value,
        'currency': conversion.currency,
        'status': conversion.status,
        'synced_to_meta': conversion.synced_to_meta,
        'meta_response': conversion.meta_response,
        'created_at': conversion.created_at
    }


# ============ Analytics (4 endpoints) ============

@router.get("/meta/analytics/conversions-by-event")
def get_conversions_by_event(
    days: int = 30,
    db: Session = Depends(SessionLocal)
):
    """Get conversion count by event type"""
    
    from crm_models import MetaConversion
    from sqlalchemy import func
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    data = db.query(
        MetaConversion.event_name,
        func.count(MetaConversion.id).label('count'),
        func.sum(MetaConversion.value).label('total_value')
    ).filter(
        MetaConversion.created_at >= start_date
    ).group_by(
        MetaConversion.event_name
    ).all()
    
    return {
        'period_days': days,
        'conversions_by_event': [
            {
                'event_name': d[0],
                'count': d[1],
                'total_value': d[2]
            }
            for d in data
        ]
    }


@router.get("/meta/analytics/sync-status")
def get_sync_status(
    db: Session = Depends(SessionLocal)
):
    """Get Meta sync status"""
    
    from crm_models import MetaConversion
    from sqlalchemy import func
    
    total = db.query(MetaConversion).count()
    synced = db.query(MetaConversion).filter(
        MetaConversion.synced_to_meta == True
    ).count()
    failed = db.query(MetaConversion).filter(
        MetaConversion.synced_to_meta == False
    ).count()
    
    return {
        'total_conversions': total,
        'synced': synced,
        'failed': failed,
        'sync_rate': round((synced / total * 100) if total > 0 else 0, 2)
    }


@router.get("/meta/analytics/customers-with-conversions")
def get_customers_with_conversions(
    db: Session = Depends(SessionLocal)
):
    """Get unique customers with conversions"""
    
    from crm_models import MetaConversion
    from sqlalchemy import func
    
    data = db.query(
        func.count(func.distinct(MetaConversion.customer_id)).label('unique_customers'),
        func.count(MetaConversion.id).label('total_conversions'),
        func.sum(MetaConversion.value).label('total_value')
    ).all()
    
    if data:
        row = data[0]
        return {
            'unique_customers': row[0],
            'total_conversions': row[1],
            'total_value': row[2],
            'avg_conversion_value': round(
                (row[2] / row[1]) if row[1] > 0 else 0, 2
            )
        }
    
    return {'error': 'No conversion data'}


# ============ Health Check ============

@router.get("/meta/health")
def meta_health(
    db: Session = Depends(SessionLocal)
):
    """Health check for Meta integration"""
    
    try:
        from crm_models import MetaConversion
        
        total_conversions = db.query(MetaConversion).count()
        
        return {
            "status": "ok",
            "service": "meta_ads",
            "total_conversions": total_conversions
        }
    
    except Exception as e:
        return {
            "status": "error",
            "service": "meta_ads",
            "message": str(e)
        }
