"""
Customer Enrichment Routes
11 REST API endpoints for enrichment, profiles, intent signals
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel
from app.database import get_db
from app.customer_enrichment_integration import (
    LinkedInProfileClient, CompanyEnrichmentClient, CustomerEnrichmentManager,
    BulkEnrichmentManager, EnrichmentStatus
)
from app.crm_models import Customer, CustomerEnrichment, CompanyData, IntentSignal
import os

router = APIRouter(prefix="/api/crm/enrichment", tags=["Customer Enrichment"])

# Initialize clients
LINKEDIN_API_KEY = os.getenv("LINKEDIN_API_KEY", "")
CLEARBIT_API_KEY = os.getenv("CLEARBIT_API_KEY", "")
HUNTER_API_KEY = os.getenv("HUNTER_API_KEY", "")

linkedin_client = LinkedInProfileClient(LINKEDIN_API_KEY)
company_client = CompanyEnrichmentClient(CLEARBIT_API_KEY, HUNTER_API_KEY)


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class EnrichmentResponse(BaseModel):
    """Enrichment response"""
    enrichment_id: str
    customer_id: str
    enrichment_type: str
    status: str
    enriched_fields: List[str]
    created_at: str
    completed_at: Optional[str]


class CompanyDataResponse(BaseModel):
    """Company data response"""
    company_name: str
    industry: Optional[str]
    employees: Optional[int]
    revenue: Optional[str]
    founded_year: Optional[int]
    website: Optional[str]
    location: Optional[str]
    data_source: str
    enriched_at: str


class IntentSignalResponse(BaseModel):
    """Intent signal response"""
    signal_id: str
    signal_type: str
    score: float
    source: str
    detected_at: str


class EnrichmentStatusResponse(BaseModel):
    """Enrichment status summary"""
    customer_id: str
    enrichment_jobs: int
    completed_enrichments: int
    intent_signals_detected: int
    company_data_enriched: bool
    overall_enrichment_score: float


class BulkEnrichmentRequest(BaseModel):
    """Bulk enrichment request"""
    customer_ids: List[str]
    enrichment_type: str  # linkedin, company, signals


# ============================================================================
# LINKEDIN ENRICHMENT
# ============================================================================

@router.post("/linkedin/{customer_id}", response_model=EnrichmentResponse)
async def enrich_linkedin(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """Enrich customer with LinkedIn profile"""
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    success, profile = CustomerEnrichmentManager.enrich_customer_linkedin(
        db, customer_id, linkedin_client
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="LinkedIn enrichment failed")
    
    enrichment = db.query(CustomerEnrichment).filter(
        CustomerEnrichment.customer_id == customer_id,
        CustomerEnrichment.enrichment_type == "linkedin"
    ).first()
    
    return EnrichmentResponse(
        enrichment_id=enrichment.id,
        customer_id=enrichment.customer_id,
        enrichment_type=enrichment.enrichment_type,
        status=enrichment.status,
        enriched_fields=enrichment.enriched_fields,
        created_at=enrichment.created_at.isoformat(),
        completed_at=enrichment.updated_at.isoformat()
    )


@router.get("/linkedin/{customer_id}")
async def get_linkedin_profile(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """Get LinkedIn profile for customer"""
    enrichment = db.query(CustomerEnrichment).filter(
        CustomerEnrichment.customer_id == customer_id,
        CustomerEnrichment.enrichment_type == "linkedin"
    ).first()
    
    if not enrichment or not enrichment.metadata:
        raise HTTPException(status_code=404, detail="LinkedIn profile not found")
    
    return enrichment.metadata


# ============================================================================
# COMPANY ENRICHMENT
# ============================================================================

@router.post("/company/{customer_id}", response_model=CompanyDataResponse)
async def enrich_company(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """Enrich customer with company data"""
    success, company_data = CustomerEnrichmentManager.enrich_customer_company(
        db, customer_id, company_client
    )
    
    if not success:
        raise HTTPException(status_code=400, detail="Company enrichment failed")
    
    return CompanyDataResponse(
        company_name=company_data.get("company_name"),
        industry=company_data.get("industry"),
        employees=company_data.get("employees"),
        revenue=company_data.get("revenue"),
        founded_year=company_data.get("founded_year"),
        website=company_data.get("website"),
        location=company_data.get("location"),
        data_source=company_data.get("data_source"),
        enriched_at=datetime.utcnow().isoformat()
    )


@router.get("/company/{customer_id}", response_model=CompanyDataResponse)
async def get_company_data(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """Get enriched company data for customer"""
    company = db.query(CompanyData).filter(
        CompanyData.customer_id == customer_id
    ).first()
    
    if not company:
        raise HTTPException(status_code=404, detail="Company data not found")
    
    return CompanyDataResponse(
        company_name=company.company_name,
        industry=company.industry,
        employees=company.employees,
        revenue=company.revenue,
        founded_year=company.founded_year,
        website=company.website,
        location=company.location,
        data_source=company.data_source,
        enriched_at=company.enriched_at.isoformat()
    )


# ============================================================================
# INTENT SIGNALS
# ============================================================================

@router.post("/signals/{customer_id}", response_model=List[IntentSignalResponse])
async def detect_intent_signals(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """Detect intent signals for customer"""
    signals = CustomerEnrichmentManager.enrich_with_intent_signals(db, customer_id)
    
    signal_objects = db.query(IntentSignal).filter(
        IntentSignal.customer_id == customer_id
    ).order_by(IntentSignal.detected_at.desc()).limit(len(signals)).all()
    
    return [
        IntentSignalResponse(
            signal_id=s.id,
            signal_type=s.signal_type,
            score=s.score,
            source=s.source,
            detected_at=s.detected_at.isoformat()
        )
        for s in signal_objects
    ]


@router.get("/signals/{customer_id}", response_model=List[IntentSignalResponse])
async def get_intent_signals(
    customer_id: str,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get all intent signals for customer"""
    signals = db.query(IntentSignal).filter(
        IntentSignal.customer_id == customer_id
    ).order_by(
        IntentSignal.score.desc()
    ).offset(skip).limit(limit).all()
    
    return [
        IntentSignalResponse(
            signal_id=s.id,
            signal_type=s.signal_type,
            score=s.score,
            source=s.source,
            detected_at=s.detected_at.isoformat()
        )
        for s in signals
    ]


@router.get("/signals/high-intent")
async def get_high_intent_customers(
    min_score: float = 0.7,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Get customers with high intent signals"""
    signals = db.query(IntentSignal).filter(
        IntentSignal.score >= min_score
    ).order_by(
        IntentSignal.score.desc()
    ).offset(skip).limit(limit).all()
    
    # Group by customer
    customer_signals = {}
    for signal in signals:
        if signal.customer_id not in customer_signals:
            customer_signals[signal.customer_id] = []
        customer_signals[signal.customer_id].append(signal)
    
    return {
        "high_intent_customers": len(customer_signals),
        "min_score": min_score,
        "customers": [
            {
                "customer_id": cid,
                "signal_count": len(sigs),
                "avg_score": sum(s.score for s in sigs) / len(sigs)
            }
            for cid, sigs in customer_signals.items()
        ]
    }


# ============================================================================
# STATUS & ANALYTICS
# ============================================================================

@router.get("/status/{customer_id}", response_model=EnrichmentStatusResponse)
async def get_enrichment_status(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """Get enrichment status for customer"""
    status = CustomerEnrichmentManager.get_enrichment_status(db, customer_id)
    
    return EnrichmentStatusResponse(
        customer_id=status["customer_id"],
        enrichment_jobs=status["enrichment_jobs"],
        completed_enrichments=status["completed_enrichments"],
        intent_signals_detected=status["intent_signals_detected"],
        company_data_enriched=status["company_data_enriched"],
        overall_enrichment_score=status["overall_enrichment_score"]
    )


# ============================================================================
# BULK OPERATIONS
# ============================================================================

@router.post("/bulk")
async def bulk_enrich(
    request: BulkEnrichmentRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Enrich multiple customers in background"""
    if len(request.customer_ids) > 5000:
        raise HTTPException(status_code=400, detail="Maximum 5000 customers per operation")
    
    background_tasks.add_task(
        BulkEnrichmentManager.enrich_bulk_customers,
        db=db,
        customer_ids=request.customer_ids,
        enrichment_type=request.enrichment_type,
        linkedin_client=linkedin_client,
        company_client=company_client
    )
    
    return {
        "status": "processing",
        "customer_count": len(request.customer_ids),
        "enrichment_type": request.enrichment_type,
        "message": "Bulk enrichment started in background"
    }


@router.get("/analytics")
async def enrichment_analytics(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get enrichment analytics"""
    from datetime import timedelta
    
    start_date = datetime.utcnow() - timedelta(days=days)
    
    enrichments = db.query(CustomerEnrichment).filter(
        CustomerEnrichment.created_at >= start_date
    ).all()
    
    signals = db.query(IntentSignal).filter(
        IntentSignal.detected_at >= start_date
    ).all()
    
    company_data = db.query(CompanyData).filter(
        CompanyData.enriched_at >= start_date
    ).all()
    
    return {
        "period_days": days,
        "total_enrichments": len(enrichments),
        "completed_enrichments": sum(
            1 for e in enrichments if e.status == EnrichmentStatus.COMPLETED.value
        ),
        "total_intent_signals": len(signals),
        "avg_intent_score": (
            sum(s.score for s in signals) / len(signals) if signals else 0
        ),
        "company_records_enriched": len(company_data),
        "enrichment_types": {}
    }


# ============================================================================
# HEALTH CHECK
# ============================================================================

@router.get("/health")
async def enrichment_health():
    """Health check for enrichment service"""
    return {
        "status": "healthy",
        "service": "Customer Enrichment",
        "timestamp": datetime.utcnow().isoformat(),
        "linkedin_configured": bool(LINKEDIN_API_KEY),
        "clearbit_configured": bool(CLEARBIT_API_KEY),
        "hunter_configured": bool(HUNTER_API_KEY)
    }
