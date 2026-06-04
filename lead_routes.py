"""
Lead Management API Endpoints
Handles lead CRUD, status workflow, scoring, and enrollment
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Header
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy.orm import Session
from sqlalchemy import func, text, desc
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

try:
    from database import SessionLocal, engine
    from crm_models import Base, Customer, Journey, JourneyInstance, Event, Segment
    from auth import verify_access_token
except ImportError:
    from app.database import SessionLocal, engine
    from app.crm_models import Base, Customer, Journey, JourneyInstance, Event, Segment
    from app.auth import verify_access_token

logger = logging.getLogger("pureleven.leads")

router = APIRouter(prefix="/api/crm/leads", tags=["leads"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def verify_token(authorization: Optional[str] = Header(None)):
    """Verify JWT token from Authorization header"""
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return verify_access_token(parts[1])
    return None

# ============= PYDANTIC SCHEMAS =============

class LeadCreate(BaseModel):
    """Schema for creating a lead"""
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    industry: Optional[str] = None
    lead_source: Optional[str] = None  # contact_form, google_forms, meta_ads, etc.
    lead_score: Optional[float] = None
    meta_data: Optional[Dict[str, Any]] = None
    
    @validator('email')
    def email_required_or_phone(cls, v):
        """At least email or phone must be provided"""
        # This is a partial validation, full check in endpoint
        return v


class LeadUpdate(BaseModel):
    """Schema for updating a lead"""
    name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    job_title: Optional[str] = None
    industry: Optional[str] = None
    lead_score: Optional[float] = None
    meta_data: Optional[Dict[str, Any]] = None


class LeadStatusUpdate(BaseModel):
    """Schema for changing lead status"""
    status: str  # new, contacted, qualified, customer, lost
    notes: Optional[str] = None


class LeadResponse(BaseModel):
    """Schema for lead response"""
    id: str
    email: Optional[str]
    name: Optional[str]
    phone: Optional[str]
    company: Optional[str]
    job_title: Optional[str]
    industry: Optional[str]
    lead_source: Optional[str]
    lead_status: Optional[str]
    lead_score: Optional[float]
    propensity_score: float
    created_at: str
    contacted_at: Optional[str]
    qualified_at: Optional[str]
    
    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    """Schema for lead list response"""
    total: int
    skip: int
    limit: int
    items: List[LeadResponse]


# ============= LEAD CRUD ENDPOINTS =============

@router.post("", response_model=LeadResponse, summary="Create a new lead")
async def create_lead(
    payload: LeadCreate,
    db: Session = Depends(get_db),
    token: Optional[Dict] = Depends(verify_token)
):
    """
    Create a new lead.
    
    Args:
        payload: LeadCreate object with lead details
    
    Returns:
        Created LeadResponse
    """
    # Validate at least email or phone
    if not payload.email and not payload.phone:
        raise HTTPException(
            status_code=400,
            detail="Either email or phone must be provided"
        )
    
    # Check if lead already exists (by email or phone)
    if payload.email:
        existing = db.query(Customer).filter(Customer.email == payload.email).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Lead with email {payload.email} already exists"
            )
    
    if payload.phone:
        existing = db.query(Customer).filter(Customer.phone == payload.phone).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Lead with phone {payload.phone} already exists"
            )
    
    # Create lead
    lead = Customer(
        email=payload.email,
        first_name=payload.name.split()[0] if payload.name else None,
        last_name=" ".join(payload.name.split()[1:]) if payload.name and len(payload.name.split()) > 1 else None,
        phone=payload.phone,
        company=payload.company,
        job_title=payload.job_title,
        industry=payload.industry,
        is_lead=True,
        lead_source=payload.lead_source or "manual",
        lead_status="new",
        lead_score=payload.lead_score or 0.0,
        lead_created_at=datetime.utcnow(),
        meta_data=payload.meta_data or {},
        email_subscribed=True,  # Default to subscribed
        sms_subscribed=True
    )
    
    db.add(lead)
    db.commit()
    db.refresh(lead)
    
    logger.info(f"Created lead: {lead.id} ({lead.email or lead.phone})")
    
    return LeadResponse.from_orm(lead)


@router.get("", response_model=LeadListResponse, summary="List all leads")
async def list_leads(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    source: Optional[str] = None,
    score_min: Optional[float] = None,
    sort_by: Optional[str] = "created_at",  # created_at, lead_score, contacted_at
    db: Session = Depends(get_db),
    token: Optional[Dict] = Depends(verify_token)
):
    """
    List all leads with optional filtering and sorting.
    
    Query Parameters:
        skip: Pagination skip (default 0)
        limit: Pagination limit (default 100, max 1000)
        status: Filter by lead_status (new, contacted, qualified, customer, lost)
        source: Filter by lead_source
        score_min: Filter by minimum lead_score
        sort_by: Sort column (created_at, lead_score, contacted_at)
    
    Returns:
        LeadListResponse with paginated leads
    """
    # Limit max results
    limit = min(limit, 1000)
    
    # Build query
    query = db.query(Customer).filter(Customer.is_lead == True)
    
    # Apply filters
    if status:
        query = query.filter(Customer.lead_status == status)
    if source:
        query = query.filter(Customer.lead_source == source)
    if score_min is not None:
        query = query.filter(Customer.lead_score >= score_min)
    
    # Count total
    total = query.count()
    
    # Apply sorting
    if sort_by == "lead_score":
        query = query.order_by(desc(Customer.lead_score))
    elif sort_by == "contacted_at":
        query = query.order_by(desc(Customer.contacted_at))
    else:
        query = query.order_by(desc(Customer.created_at))
    
    # Apply pagination
    leads = query.offset(skip).limit(limit).all()
    
    return LeadListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=[LeadResponse.from_orm(lead) for lead in leads]
    )


@router.get("/{lead_id}", response_model=LeadResponse, summary="Get lead details")
async def get_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    token: Optional[Dict] = Depends(verify_token)
):
    """
    Get a specific lead by ID.
    
    Path Parameters:
        lead_id: Lead ID
    
    Returns:
        LeadResponse
    """
    lead = db.query(Customer).filter(
        Customer.id == lead_id,
        Customer.is_lead == True
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    return LeadResponse.from_orm(lead)


@router.put("/{lead_id}", response_model=LeadResponse, summary="Update lead")
async def update_lead(
    lead_id: str,
    payload: LeadUpdate,
    db: Session = Depends(get_db),
    token: Optional[Dict] = Depends(verify_token)
):
    """
    Update lead details.
    
    Path Parameters:
        lead_id: Lead ID
    
    Body:
        LeadUpdate object with fields to update
    
    Returns:
        Updated LeadResponse
    """
    lead = db.query(Customer).filter(
        Customer.id == lead_id,
        Customer.is_lead == True
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Update fields
    if payload.name:
        parts = payload.name.split()
        lead.first_name = parts[0]
        lead.last_name = " ".join(parts[1:]) if len(parts) > 1 else None
    if payload.phone:
        lead.phone = payload.phone
    if payload.company:
        lead.company = payload.company
    if payload.job_title:
        lead.job_title = payload.job_title
    if payload.industry:
        lead.industry = payload.industry
    if payload.lead_score is not None:
        lead.lead_score = payload.lead_score
    if payload.meta_data:
        lead.meta_data = payload.meta_data
    
    lead.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(lead)
    
    logger.info(f"Updated lead: {lead_id}")
    
    return LeadResponse.from_orm(lead)


@router.delete("/{lead_id}", summary="Delete lead")
async def delete_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    token: Optional[Dict] = Depends(verify_token)
):
    """
    Delete a lead (soft delete - mark as lost).
    
    Path Parameters:
        lead_id: Lead ID
    """
    lead = db.query(Customer).filter(
        Customer.id == lead_id,
        Customer.is_lead == True
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Soft delete: mark as lost
    lead.lead_status = "lost"
    lead.updated_at = datetime.utcnow()
    db.commit()
    
    logger.info(f"Deleted lead: {lead_id}")
    
    return {"status": "deleted", "lead_id": lead_id}


# ============= LEAD STATUS WORKFLOW =============

@router.put("/{lead_id}/status", response_model=LeadResponse, summary="Update lead status")
async def update_lead_status(
    lead_id: str,
    payload: LeadStatusUpdate,
    db: Session = Depends(get_db),
    token: Optional[Dict] = Depends(verify_token)
):
    """
    Move lead through status workflow.
    
    Valid transitions:
        new → contacted → qualified → customer → lost
    
    Path Parameters:
        lead_id: Lead ID
    
    Body:
        LeadStatusUpdate with new status
    
    Returns:
        Updated LeadResponse
    """
    lead = db.query(Customer).filter(
        Customer.id == lead_id,
        Customer.is_lead == True
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Validate status transition
    valid_statuses = ["new", "contacted", "qualified", "customer", "lost"]
    if payload.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    # Update status and timestamp
    old_status = lead.lead_status
    lead.lead_status = payload.status
    
    # Update relevant timestamps
    if payload.status == "contacted":
        lead.contacted_at = datetime.utcnow()
    elif payload.status == "qualified":
        lead.qualified_at = datetime.utcnow()
    elif payload.status == "customer":
        # Will be handled by convert endpoint
        lead.qualified_at = lead.qualified_at or datetime.utcnow()
    
    lead.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lead)
    
    logger.info(f"Lead {lead_id} status changed: {old_status} → {payload.status}")
    
    return LeadResponse.from_orm(lead)


# ============= LEAD TO CUSTOMER CONVERSION =============

@router.post("/{lead_id}/convert", response_model=LeadResponse, summary="Convert lead to customer")
async def convert_lead_to_customer(
    lead_id: str,
    db: Session = Depends(get_db),
    token: Optional[Dict] = Depends(verify_token)
):
    """
    Mark a lead as converted to customer.
    Sets status to 'customer' and records conversion timestamp.
    
    Path Parameters:
        lead_id: Lead ID
    
    Returns:
        Updated LeadResponse
    """
    lead = db.query(Customer).filter(
        Customer.id == lead_id,
        Customer.is_lead == True
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Mark as customer
    lead.lead_status = "customer"
    lead.is_lead = False  # No longer a lead
    lead.qualified_at = datetime.utcnow()
    lead.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(lead)
    
    logger.info(f"Lead {lead_id} converted to customer")
    
    return LeadResponse.from_orm(lead)


# ============= LEAD SCORING & ENRICHMENT =============

@router.post("/{lead_id}/calculate-score", response_model=LeadResponse, summary="Calculate lead propensity score")
async def calculate_lead_score(
    lead_id: str,
    db: Session = Depends(get_db),
    token: Optional[Dict] = Depends(verify_token)
):
    """
    Recalculate propensity score for a lead based on profile.
    Uses company, job title, industry, and interaction history.
    
    Path Parameters:
        lead_id: Lead ID
    
    Returns:
        Updated LeadResponse with new score
    """
    lead = db.query(Customer).filter(
        Customer.id == lead_id,
        Customer.is_lead == True
    ).first()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Simple propensity scoring based on profile completeness and engagement
    score = 0.5  # Default
    
    # Add points for profile completeness
    if lead.company:
        score += 0.1
    if lead.job_title:
        score += 0.1
    if lead.industry:
        score += 0.05
    if lead.phone:
        score += 0.05
    
    # Add points for engagement
    events = db.query(Event).filter(Event.customer_id == lead_id).count()
    if events > 0:
        score += min(0.2, events * 0.05)  # Cap at 0.2
    
    # Add points for status progression
    if lead.contacted_at:
        score += 0.1
    if lead.qualified_at:
        score += 0.15
    
    # Cap at 1.0
    score = min(1.0, score)
    
    lead.propensity_score = score
    lead.propensity_updated_at = datetime.utcnow()
    lead.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(lead)
    
    logger.info(f"Updated propensity score for lead {lead_id}: {score:.2f}")
    
    return LeadResponse.from_orm(lead)


# ============= LEAD BULK OPERATIONS =============

@router.post("/bulk/import-csv", summary="Import leads from CSV")
async def bulk_import_leads_csv(
    csv_data: List[LeadCreate],
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    token: Optional[Dict] = Depends(verify_token)
):
    """
    Bulk import leads from CSV data.
    Processed asynchronously in the background.
    
    Body:
        List of LeadCreate objects
    
    Returns:
        Job status
    """
    if not csv_data:
        raise HTTPException(status_code=400, detail="No leads provided")
    
    if len(csv_data) > 10000:
        raise HTTPException(status_code=400, detail="Maximum 10,000 leads per import")
    
    # Process in background
    background_tasks.add_task(
        _process_bulk_lead_import,
        csv_data,
        db
    )
    
    return {
        "status": "processing",
        "count": len(csv_data),
        "message": "Lead import started"
    }


def _process_bulk_lead_import(csv_data: List[LeadCreate], db: Session):
    """Background task for bulk lead import"""
    imported = 0
    failed = 0
    
    for payload in csv_data:
        try:
            # Check if exists
            if payload.email:
                existing = db.query(Customer).filter(
                    Customer.email == payload.email
                ).first()
                if existing:
                    failed += 1
                    continue
            
            # Create lead
            lead = Customer(
                email=payload.email,
                first_name=payload.name.split()[0] if payload.name else None,
                phone=payload.phone,
                company=payload.company,
                job_title=payload.job_title,
                industry=payload.industry,
                is_lead=True,
                lead_source=payload.lead_source or "csv_import",
                lead_status="new",
                lead_created_at=datetime.utcnow(),
                email_subscribed=True,
                sms_subscribed=True
            )
            db.add(lead)
            imported += 1
        except Exception as e:
            logger.error(f"Failed to import lead: {e}")
            failed += 1
    
    db.commit()
    logger.info(f"Bulk import complete: {imported} imported, {failed} failed")


# ============= LEAD ANALYTICS =============

@router.get("/analytics/funnel", summary="Get lead conversion funnel")
async def lead_funnel_analytics(
    db: Session = Depends(get_db),
    token: Optional[Dict] = Depends(verify_token)
):
    """
    Get lead conversion funnel metrics.
    
    Returns:
        Funnel with counts at each stage
    """
    total_leads = db.query(func.count(Customer.id)).filter(
        Customer.is_lead == True
    ).scalar()
    
    contacted = db.query(func.count(Customer.id)).filter(
        Customer.is_lead == True,
        Customer.contacted_at != None
    ).scalar()
    
    qualified = db.query(func.count(Customer.id)).filter(
        Customer.is_lead == True,
        Customer.qualified_at != None
    ).scalar()
    
    converted = db.query(func.count(Customer.id)).filter(
        Customer.lead_status == "customer"
    ).scalar()
    
    return {
        "total_leads": total_leads,
        "contacted": contacted,
        "contacted_rate": (contacted / total_leads * 100) if total_leads > 0 else 0,
        "qualified": qualified,
        "qualified_rate": (qualified / total_leads * 100) if total_leads > 0 else 0,
        "converted": converted,
        "conversion_rate": (converted / total_leads * 100) if total_leads > 0 else 0
    }


@router.get("/analytics/by-source", summary="Get lead analytics by source")
async def lead_analytics_by_source(
    db: Session = Depends(get_db),
    token: Optional[Dict] = Depends(verify_token)
):
    """
    Get lead statistics grouped by lead_source.
    
    Returns:
        List of sources with lead counts
    """
    results = db.query(
        Customer.lead_source,
        func.count(Customer.id).label("count"),
        func.avg(Customer.lead_score).label("avg_score"),
        func.sum((Customer.lead_status == "qualified").cast(int)).label("qualified_count")
    ).filter(
        Customer.is_lead == True
    ).group_by(
        Customer.lead_source
    ).all()
    
    return [
        {
            "source": r[0],
            "total_leads": r[1],
            "avg_score": float(r[2]) if r[2] else 0.0,
            "qualified_count": r[3] or 0
        }
        for r in results
    ]


# ============= HEALTH CHECK =============

@router.get("/health", summary="Health check")
async def health():
    """Simple health check endpoint"""
    return {"status": "ok", "service": "leads"}
