"""
Offline Conversions API Routes
Handles Meta CAPI offline event matching and submission
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, EmailStr
from crm_models import OfflineConversion, Customer
from database import SessionLocal
from offline_conversions import (
    OfflineConversionMatcher, 
    build_hashed_fields,
    ConversionStatus,
    normalize_phone,
    normalize_email
)
import uuid
import asyncio

router = APIRouter(prefix="/api/crm", tags=["offline_conversions"])


# Pydantic Models
class OfflineConversionCreate(BaseModel):
    """Input for creating offline conversion"""
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    
    conversion_type: str = "Purchase"  # Purchase, Lead, ViewContent, AddToCart, etc
    conversion_value: Optional[float] = None
    currency: str = "INR"
    source: str = "manual"  # meta_ads, google_ads, shopify, etc
    conversion_timestamp: Optional[datetime] = None
    
    metadata: Optional[dict] = None


class OfflineConversionUpdate(BaseModel):
    """Update offline conversion details"""
    conversion_value: Optional[float] = None
    conversion_type: Optional[str] = None
    metadata: Optional[dict] = None


class OfflineConversionResponse(BaseModel):
    """Response model for offline conversion"""
    id: str
    customer_id: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    
    conversion_type: str
    conversion_value: Optional[float]
    currency: str
    source: str
    
    status: str
    match_algorithm: Optional[str]
    match_confidence: float
    match_fields: Optional[list]
    
    capi_status: Optional[str]
    capi_event_id: Optional[str]
    
    retry_count: int
    error_message: Optional[str]
    
    created_at: datetime
    matched_at: Optional[datetime]
    submitted_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class OfflineConversionListResponse(BaseModel):
    """Paginated list response"""
    total: int
    skip: int
    limit: int
    items: List[OfflineConversionResponse]


class OfflineConversionBatchResponse(BaseModel):
    """Response for batch operations"""
    status: str
    created_count: int
    matched_count: int
    unmatched_count: int
    errors: Optional[List[str]] = None


class CapiSubmissionResponse(BaseModel):
    """Response from Meta CAPI"""
    event_id: str
    events_received: int
    fbp: Optional[str]
    fbp_data: Optional[dict]


# ============ CRUD Endpoints ============

@router.post("/offline-conversions", response_model=OfflineConversionResponse)
def create_offline_conversion(
    data: OfflineConversionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(SessionLocal)
):
    """
    Create offline conversion event
    
    Steps:
    1. Validate input (email OR phone required)
    2. Create OfflineConversion record
    3. Match to existing customer
    4. Return result with match status
    """
    
    # Validation
    if not data.email and not data.phone:
        raise HTTPException(
            status_code=400,
            detail="Either email or phone is required"
        )
    
    # Create conversion record
    conversion = OfflineConversion(
        id=str(uuid.uuid4()),
        email=data.email,
        phone=data.phone,
        first_name=data.first_name,
        last_name=data.last_name,
        city=data.city,
        state=data.state,
        postal_code=data.postal_code,
        country=data.country,
        conversion_type=data.conversion_type,
        conversion_value=data.conversion_value,
        currency=data.currency,
        source=data.source,
        conversion_timestamp=data.conversion_timestamp or datetime.utcnow(),
        metadata=data.metadata,
        status=ConversionStatus.PENDING.value
    )
    
    db.add(conversion)
    db.flush()
    
    # Match to customer in background
    background_tasks.add_task(
        _match_offline_conversion,
        conversion.id
    )
    
    db.commit()
    return conversion


@router.get("/offline-conversions", response_model=OfflineConversionListResponse)
def list_offline_conversions(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    source: Optional[str] = None,
    customer_id: Optional[str] = None,
    sort_by: str = "created_at",  # created_at, matched_at, conversion_value
    db: Session = Depends(SessionLocal)
):
    """
    List offline conversions with filtering and pagination
    
    Query parameters:
    - skip: Offset (default 0)
    - limit: Max results (default 100, max 1000)
    - status: Filter by status (pending, matched, unmatched, failed, retrying)
    - source: Filter by source (meta_ads, google_ads, shopify, etc)
    - customer_id: Filter by matched customer
    - sort_by: Sort field (created_at, matched_at, conversion_value)
    """
    
    limit = min(limit, 1000)
    
    query = db.query(OfflineConversion)
    
    # Apply filters
    if status:
        query = query.filter(OfflineConversion.status == status)
    
    if source:
        query = query.filter(OfflineConversion.source == source)
    
    if customer_id:
        query = query.filter(OfflineConversion.customer_id == customer_id)
    
    # Get total
    total = query.count()
    
    # Sort and paginate
    if sort_by == "matched_at":
        query = query.order_by(OfflineConversion.matched_at.desc())
    elif sort_by == "conversion_value":
        query = query.order_by(OfflineConversion.conversion_value.desc())
    else:  # created_at
        query = query.order_by(OfflineConversion.created_at.desc())
    
    items = query.offset(skip).limit(limit).all()
    
    return OfflineConversionListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=items
    )


@router.get("/offline-conversions/{conversion_id}", response_model=OfflineConversionResponse)
def get_offline_conversion(
    conversion_id: str,
    db: Session = Depends(SessionLocal)
):
    """Get single offline conversion detail"""
    
    conversion = db.query(OfflineConversion).filter(
        OfflineConversion.id == conversion_id
    ).first()
    
    if not conversion:
        raise HTTPException(status_code=404, detail="Offline conversion not found")
    
    return conversion


@router.put("/offline-conversions/{conversion_id}", response_model=OfflineConversionResponse)
def update_offline_conversion(
    conversion_id: str,
    data: OfflineConversionUpdate,
    db: Session = Depends(SessionLocal)
):
    """Update offline conversion details"""
    
    conversion = db.query(OfflineConversion).filter(
        OfflineConversion.id == conversion_id
    ).first()
    
    if not conversion:
        raise HTTPException(status_code=404, detail="Offline conversion not found")
    
    # Can only update if not yet submitted to CAPI
    if conversion.capi_status == "sent":
        raise HTTPException(
            status_code=400,
            detail="Cannot update conversion already sent to CAPI"
        )
    
    # Update fields
    if data.conversion_value is not None:
        conversion.conversion_value = data.conversion_value
    
    if data.conversion_type is not None:
        conversion.conversion_type = data.conversion_type
    
    if data.metadata is not None:
        conversion.metadata = data.metadata
    
    conversion.updated_at = datetime.utcnow()
    db.commit()
    
    return conversion


@router.delete("/offline-conversions/{conversion_id}")
def delete_offline_conversion(
    conversion_id: str,
    db: Session = Depends(SessionLocal)
):
    """Delete offline conversion"""
    
    conversion = db.query(OfflineConversion).filter(
        OfflineConversion.id == conversion_id
    ).first()
    
    if not conversion:
        raise HTTPException(status_code=404, detail="Offline conversion not found")
    
    # Cannot delete if already submitted
    if conversion.capi_status == "sent":
        raise HTTPException(
            status_code=400,
            detail="Cannot delete conversion already sent to CAPI"
        )
    
    db.delete(conversion)
    db.commit()
    
    return {"status": "deleted"}


# ============ Matching Endpoints ============

@router.post("/offline-conversions/{conversion_id}/match")
def trigger_match(
    conversion_id: str,
    db: Session = Depends(SessionLocal)
):
    """Manually trigger matching for a conversion"""
    
    conversion = db.query(OfflineConversion).filter(
        OfflineConversion.id == conversion_id
    ).first()
    
    if not conversion:
        raise HTTPException(status_code=404, detail="Offline conversion not found")
    
    # Perform matching
    matcher = OfflineConversionMatcher(db)
    
    match_result = matcher.match_customer({
        'email': conversion.email,
        'phone': conversion.phone,
        'name': f"{conversion.first_name or ''} {conversion.last_name or ''}".strip(),
        'city': conversion.city,
        'state': conversion.state,
        'postal': conversion.postal_code,
        'country': conversion.country
    })
    
    # Update conversion
    conversion.status = ConversionStatus.MATCHED.value if match_result['matched_customer_id'] else ConversionStatus.UNMATCHED.value
    conversion.customer_id = match_result['matched_customer_id']
    conversion.match_algorithm = match_result['algorithm_used']
    conversion.match_confidence = match_result['confidence']
    conversion.match_fields = match_result['match_fields']
    conversion.matched_at = datetime.utcnow()
    db.commit()
    
    return {
        "status": conversion.status,
        "customer_id": conversion.customer_id,
        "confidence": conversion.match_confidence,
        "algorithm": conversion.match_algorithm
    }


@router.post("/offline-conversions/batch/create", response_model=OfflineConversionBatchResponse)
def batch_create_conversions(
    conversions: List[OfflineConversionCreate],
    background_tasks: BackgroundTasks,
    db: Session = Depends(SessionLocal)
):
    """
    Batch create offline conversions
    
    Steps:
    1. Validate each conversion (email OR phone required)
    2. Create all records
    3. Match in background
    """
    
    if len(conversions) > 10000:
        raise HTTPException(
            status_code=400,
            detail="Batch limit is 10,000 conversions"
        )
    
    created = 0
    errors = []
    
    for idx, conv_data in enumerate(conversions):
        try:
            if not conv_data.email and not conv_data.phone:
                errors.append(f"Item {idx}: Either email or phone required")
                continue
            
            conversion = OfflineConversion(
                id=str(uuid.uuid4()),
                email=conv_data.email,
                phone=conv_data.phone,
                first_name=conv_data.first_name,
                last_name=conv_data.last_name,
                city=conv_data.city,
                state=conv_data.state,
                postal_code=conv_data.postal_code,
                country=conv_data.country,
                conversion_type=conv_data.conversion_type,
                conversion_value=conv_data.conversion_value,
                currency=conv_data.currency,
                source=conv_data.source,
                conversion_timestamp=conv_data.conversion_timestamp or datetime.utcnow(),
                metadata=conv_data.metadata,
                status=ConversionStatus.PENDING.value
            )
            
            db.add(conversion)
            created += 1
        
        except Exception as e:
            errors.append(f"Item {idx}: {str(e)}")
    
    db.commit()
    
    # Batch match in background
    background_tasks.add_task(_batch_match_conversions, db)
    
    return OfflineConversionBatchResponse(
        status="processing",
        created_count=created,
        matched_count=0,
        unmatched_count=0,
        errors=errors if errors else None
    )


# ============ CAPI Integration ============

@router.post("/offline-conversions/{conversion_id}/submit-capi")
def submit_to_capi(
    conversion_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(SessionLocal)
):
    """
    Submit offline conversion to Meta CAPI
    
    Steps:
    1. Verify conversion matched to customer
    2. Build hashed fields
    3. Submit to Meta CAPI
    4. Store event ID and response
    """
    
    conversion = db.query(OfflineConversion).filter(
        OfflineConversion.id == conversion_id
    ).first()
    
    if not conversion:
        raise HTTPException(status_code=404, detail="Offline conversion not found")
    
    # Must be matched to customer
    if not conversion.customer_id:
        raise HTTPException(
            status_code=400,
            detail="Conversion must be matched to customer before CAPI submission"
        )
    
    # Already submitted?
    if conversion.capi_status == "sent":
        raise HTTPException(
            status_code=400,
            detail="Conversion already sent to CAPI"
        )
    
    # Get customer data
    customer = db.query(Customer).filter(
        Customer.id == conversion.customer_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    # Schedule async submission
    background_tasks.add_task(
        _submit_to_capi_async,
        conversion_id,
        customer.id
    )
    
    return {
        "status": "queued_for_submission",
        "conversion_id": conversion_id,
        "message": "Will be submitted to CAPI asynchronously"
    }


@router.get("/offline-conversions/analytics/funnel")
def get_conversion_funnel(
    db: Session = Depends(SessionLocal)
):
    """
    Get conversion funnel metrics
    
    Returns:
    {
        total_conversions,
        pending (count, %),
        matched (count, %),
        unmatched (count, %),
        submitted (count, %),
        failed (count, %)
    }
    """
    
    total = db.query(OfflineConversion).count()
    
    if total == 0:
        return {
            "total_conversions": 0,
            "funnel": []
        }
    
    statuses = [
        ConversionStatus.PENDING.value,
        ConversionStatus.MATCHED.value,
        ConversionStatus.UNMATCHED.value,
        ConversionStatus.FAILED.value,
        ConversionStatus.RETRYING.value
    ]
    
    funnel = []
    for status in statuses:
        count = db.query(OfflineConversion).filter(
            OfflineConversion.status == status
        ).count()
        
        funnel.append({
            "status": status,
            "count": count,
            "percentage": round(count / total * 100, 2)
        })
    
    return {
        "total_conversions": total,
        "funnel": funnel
    }


@router.get("/offline-conversions/analytics/by-source")
def get_conversions_by_source(
    db: Session = Depends(SessionLocal)
):
    """
    Get conversion metrics by source
    
    Returns:
    [{
        source,
        total,
        matched_count,
        match_rate,
        avg_conversion_value
    }]
    """
    
    from sqlalchemy import func
    
    sources = db.query(OfflineConversion.source).distinct().all()
    
    analytics = []
    for (source,) in sources:
        if not source:
            continue
        
        source_conversions = db.query(OfflineConversion).filter(
            OfflineConversion.source == source
        ).all()
        
        total = len(source_conversions)
        matched = len([c for c in source_conversions if c.status == ConversionStatus.MATCHED.value])
        avg_value = sum([c.conversion_value or 0 for c in source_conversions]) / total if total > 0 else 0
        
        analytics.append({
            "source": source,
            "total_conversions": total,
            "matched_count": matched,
            "match_rate": round(matched / total * 100, 2) if total > 0 else 0,
            "avg_conversion_value": round(avg_value, 2)
        })
    
    return sorted(analytics, key=lambda x: x['total_conversions'], reverse=True)


@router.post("/offline-conversions/health")
def offline_conversions_health(
    db: Session = Depends(SessionLocal)
):
    """Health check for offline conversions service"""
    
    try:
        # Check database connectivity
        count = db.query(OfflineConversion).count()
        
        # Count pending retries
        pending_retries = db.query(OfflineConversion).filter(
            OfflineConversion.status == ConversionStatus.RETRYING.value
        ).count()
        
        return {
            "status": "ok",
            "service": "offline_conversions",
            "total_conversions": count,
            "pending_retries": pending_retries
        }
    
    except Exception as e:
        return {
            "status": "error",
            "service": "offline_conversions",
            "message": str(e)
        }


# ============ Background Tasks ============

def _match_offline_conversion(conversion_id: str):
    """Background task to match offline conversion to customer"""
    
    db = SessionLocal()
    try:
        conversion = db.query(OfflineConversion).filter(
            OfflineConversion.id == conversion_id
        ).first()
        
        if not conversion:
            return
        
        # Perform matching
        matcher = OfflineConversionMatcher(db)
        
        match_result = matcher.match_customer({
            'email': conversion.email,
            'phone': conversion.phone,
            'name': f"{conversion.first_name or ''} {conversion.last_name or ''}".strip(),
            'city': conversion.city,
            'state': conversion.state,
            'postal': conversion.postal_code,
            'country': conversion.country
        })
        
        # Update conversion
        conversion.status = ConversionStatus.MATCHED.value if match_result['matched_customer_id'] else ConversionStatus.UNMATCHED.value
        conversion.customer_id = match_result['matched_customer_id']
        conversion.match_algorithm = match_result['algorithm_used']
        conversion.match_confidence = match_result['confidence']
        conversion.match_fields = match_result['match_fields']
        conversion.matched_at = datetime.utcnow()
        db.commit()
    
    finally:
        db.close()


def _batch_match_conversions(db: Session):
    """Background task to match pending conversions"""
    
    pending = db.query(OfflineConversion).filter(
        OfflineConversion.status == ConversionStatus.PENDING.value
    ).all()
    
    matcher = OfflineConversionMatcher(db)
    
    for conversion in pending:
        match_result = matcher.match_customer({
            'email': conversion.email,
            'phone': conversion.phone,
            'name': f"{conversion.first_name or ''} {conversion.last_name or ''}".strip(),
            'city': conversion.city,
            'state': conversion.state,
            'postal': conversion.postal_code,
            'country': conversion.country
        })
        
        conversion.status = ConversionStatus.MATCHED.value if match_result['matched_customer_id'] else ConversionStatus.UNMATCHED.value
        conversion.customer_id = match_result['matched_customer_id']
        conversion.match_algorithm = match_result['algorithm_used']
        conversion.match_confidence = match_result['confidence']
        conversion.match_fields = match_result['match_fields']
        conversion.matched_at = datetime.utcnow()
    
    db.commit()


def _submit_to_capi_async(conversion_id: str, customer_id: str):
    """Background task to submit conversion to Meta CAPI"""
    
    db = SessionLocal()
    try:
        conversion = db.query(OfflineConversion).filter(
            OfflineConversion.id == conversion_id
        ).first()
        
        if not conversion:
            return
        
        customer = db.query(Customer).filter(
            Customer.id == customer_id
        ).first()
        
        if not customer:
            return
        
        # Build hashed fields for CAPI
        hashed_fields = build_hashed_fields(
            email=conversion.email or customer.email,
            phone=conversion.phone or customer.phone,
            first_name=conversion.first_name,
            last_name=conversion.last_name,
            city=conversion.city or customer.city,
            state=conversion.state or customer.state,
            postal=conversion.postal_code or customer.postal_code,
            country=conversion.country or customer.country,
            external_id=customer.id
        )
        
        # Here you would call Meta CAPI
        # This is placeholder - actual CAPI integration would go here
        # Example: response = meta_capi_client.send_event(...)
        
        conversion.capi_status = "sent"
        conversion.capi_event_id = str(uuid.uuid4())
        conversion.submitted_at = datetime.utcnow()
        conversion.capi_response = {
            "event_id": conversion.capi_event_id,
            "hashed_fields": list(hashed_fields.keys()),
            "status": "received"
        }
        db.commit()
    
    except Exception as e:
        conversion.capi_status = "failed"
        conversion.error_message = str(e)
        db.commit()
    
    finally:
        db.close()
