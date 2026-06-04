"""
Propensity Scoring API Routes
ML-based customer scoring and segmentation endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel
from database import SessionLocal
from propensity_scoring import PropensityCalculator, PropensityModelTrainer, PropensitySegment
import uuid

router = APIRouter(prefix="/api/crm", tags=["propensity_scoring"])


# Pydantic Models
class PropensityScoreBreakdown(BaseModel):
    """Breakdown of propensity score components"""
    recency_score: float
    frequency_score: float
    monetary_score: float
    engagement_score: float
    lead_quality_score: float


class PropensityScoreResponse(BaseModel):
    """Response for propensity score calculation"""
    customer_id: str
    propensity_score: float
    segment: str
    breakdown: PropensityScoreBreakdown
    factors: dict
    model_version: str
    calculated_at: datetime
    
    class Config:
        from_attributes = True


class PropensityBatchResponse(BaseModel):
    """Response for batch scoring"""
    status: str
    processed: int
    errors: Optional[List[str]] = None


class PropensitySegmentDistribution(BaseModel):
    """Distribution across propensity segments"""
    total: int
    very_high: dict
    high: dict
    medium: dict
    low: dict
    low: dict


class HighPropensityLead(BaseModel):
    """High propensity lead for outreach"""
    customer_id: str
    email: Optional[str]
    phone: Optional[str]
    name: str
    propensity_score: float
    segment: str
    lead_status: str
    lead_source: Optional[str]
    recommendation: str


# ============ Single Customer Scoring ============

@router.post("/customers/{customer_id}/propensity-score", response_model=PropensityScoreResponse)
def calculate_propensity_score(
    customer_id: str,
    db: Session = Depends(SessionLocal)
):
    """
    Calculate propensity score for single customer
    
    Returns comprehensive scoring breakdown with:
    - Overall propensity score (0.0-1.0)
    - Segment classification
    - Component breakdown (recency, frequency, monetary, etc)
    - Supporting factors
    """
    
    calculator = PropensityCalculator(db)
    
    try:
        score_data = calculator.calculate_propensity_score(customer_id)
        
        if 'error' in score_data:
            raise HTTPException(status_code=404, detail=score_data['error'])
        
        return score_data
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring error: {str(e)}")


@router.get("/customers/{customer_id}/propensity-score", response_model=PropensityScoreResponse)
def get_propensity_score(
    customer_id: str,
    db: Session = Depends(SessionLocal)
):
    """Get previously calculated propensity score for customer"""
    
    from crm_models import Customer
    
    customer = db.query(Customer).filter(
        Customer.id == customer_id
    ).first()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    if not customer.propensity_score:
        raise HTTPException(
            status_code=400,
            detail="Propensity score not yet calculated. Use POST to calculate."
        )
    
    calculator = PropensityCalculator(db)
    return calculator.calculate_propensity_score(customer_id)


# ============ Batch Scoring ============

@router.post("/propensity-scores/batch-calculate", response_model=PropensityBatchResponse)
def batch_calculate_propensity(
    customer_ids: Optional[List[str]] = None,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(SessionLocal)
):
    """
    Batch calculate propensity scores
    
    Parameters:
    - customer_ids: Optional list of specific customer IDs to score
                    If None, scores all active customers
    
    Processing:
    - Runs asynchronously
    - Updates customer.propensity_score in database
    - Updates customer.propensity_updated_at timestamp
    
    Returns immediately with status
    """
    
    trainer = PropensityModelTrainer(db)
    
    try:
        result = trainer.batch_calculate_propensity(customer_ids)
        return result
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch scoring error: {str(e)}")


# ============ Analytics & Insights ============

@router.get("/propensity-scores/analytics/segment-distribution")
def get_segment_distribution(
    db: Session = Depends(SessionLocal)
):
    """
    Get distribution of customers across propensity segments
    
    Returns:
    {
        total: 5000,
        very_high: { count: 250, percentage: 5.0 },
        high: { count: 1500, percentage: 30.0 },
        medium: { count: 2000, percentage: 40.0 },
        low: { count: 800, percentage: 16.0 },
        very_low: { count: 450, percentage: 9.0 }
    }
    """
    
    trainer = PropensityModelTrainer(db)
    
    try:
        distribution = trainer.get_segment_distribution()
        return distribution
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analytics error: {str(e)}")


@router.get("/propensity-scores/high-propensity-leads", response_model=List[HighPropensityLead])
def get_high_propensity_leads(
    limit: int = 100,
    segment: Optional[str] = None,
    db: Session = Depends(SessionLocal)
):
    """
    Get high propensity leads ready for outreach
    
    Parameters:
    - limit: Max results (default 100)
    - segment: Filter by segment (very_high, high, etc)
    
    Returns:
    List of leads sorted by propensity score (highest first)
    with recommended action for each
    """
    
    from crm_models import Customer
    
    if limit > 1000:
        limit = 1000
    
    trainer = PropensityModelTrainer(db)
    leads = trainer.get_high_propensity_leads(limit)
    
    # Optional segment filter
    if segment:
        leads = [l for l in leads if l['segment'] == segment]
    
    return leads


@router.get("/propensity-scores/analytics/by-segment/{segment}")
def get_customers_by_segment(
    segment: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(SessionLocal)
):
    """
    Get customers in specific propensity segment
    
    Parameters:
    - segment: very_high, high, medium, low, very_low
    - skip: Offset
    - limit: Max results
    
    Returns:
    {
        total: 1500,
        skip: 0,
        limit: 100,
        segment: "high",
        items: [
            {
                customer_id,
                email,
                name,
                propensity_score,
                lead_status
            }
        ]
    }
    """
    
    from crm_models import Customer
    
    # Validate segment
    try:
        PropensitySegment(segment)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid segment. Must be one of: {[s.value for s in PropensitySegment]}"
        )
    
    # Map segment to score range
    score_ranges = {
        'very_high': (0.8, 1.0),
        'high': (0.6, 0.8),
        'medium': (0.4, 0.6),
        'low': (0.2, 0.4),
        'very_low': (0.0, 0.2)
    }
    
    min_score, max_score = score_ranges[segment]
    
    # Query
    query = db.query(Customer).filter(
        Customer.propensity_score >= min_score,
        Customer.propensity_score < max_score,
        Customer.deleted_at.is_(None)
    )
    
    total = query.count()
    
    items = query.order_by(
        Customer.propensity_score.desc()
    ).offset(skip).limit(limit).all()
    
    return {
        'total': total,
        'skip': skip,
        'limit': limit,
        'segment': segment,
        'items': [
            {
                'customer_id': c.id,
                'email': c.email,
                'phone': c.phone,
                'name': c.first_name or c.last_name or 'N/A',
                'propensity_score': round(c.propensity_score, 4),
                'lead_status': c.lead_status,
                'total_spent': round(c.total_spent or 0, 2),
                'orders_count': c.orders_count or 0
            }
            for c in items
        ]
    }


@router.get("/propensity-scores/analytics/funnel")
def get_propensity_funnel(
    db: Session = Depends(SessionLocal)
):
    """
    Get propensity to conversion funnel
    
    Shows conversion rates by propensity segment
    
    Returns:
    {
        total_customers: 5000,
        total_converters: 1500,
        funnel: [
            {
                segment: "very_high",
                count: 250,
                converters: 200,
                conversion_rate: 80.0
            }
        ]
    }
    """
    
    from crm_models import Customer
    
    total = db.query(Customer).filter(
        Customer.deleted_at.is_(None)
    ).count()
    
    # Count converters (customers with orders)
    converters = db.query(Customer).filter(
        Customer.orders_count > 0,
        Customer.deleted_at.is_(None)
    ).count()
    
    funnel = []
    
    for segment in PropensitySegment:
        score_ranges = {
            'very_high': (0.8, 1.0),
            'high': (0.6, 0.8),
            'medium': (0.4, 0.6),
            'low': (0.2, 0.4),
            'very_low': (0.0, 0.2)
        }
        
        min_score, max_score = score_ranges[segment.value]
        
        segment_count = db.query(Customer).filter(
            Customer.propensity_score >= min_score,
            Customer.propensity_score < max_score,
            Customer.deleted_at.is_(None)
        ).count()
        
        segment_converters = db.query(Customer).filter(
            Customer.propensity_score >= min_score,
            Customer.propensity_score < max_score,
            Customer.orders_count > 0,
            Customer.deleted_at.is_(None)
        ).count()
        
        conversion_rate = (segment_converters / segment_count * 100) if segment_count > 0 else 0
        
        funnel.append({
            'segment': segment.value,
            'count': segment_count,
            'converters': segment_converters,
            'conversion_rate': round(conversion_rate, 2)
        })
    
    return {
        'total_customers': total,
        'total_converters': converters,
        'funnel': funnel
    }


@router.get("/propensity-scores/analytics/roi-by-segment")
def get_roi_by_segment(
    db: Session = Depends(SessionLocal)
):
    """
    Get ROI metrics by propensity segment
    
    Returns spending and conversion metrics for each segment
    
    Returns:
    {
        segment: "high",
        customers: 1500,
        total_spent: 7500000,
        avg_spent_per_customer: 5000,
        conversion_rate: 75.0,
        customers_spent: 1125,
        roi_index: 150  (relative to overall avg)
    }
    """
    
    from crm_models import Customer
    from sqlalchemy import func
    
    overall_avg_spent = db.query(
        func.avg(Customer.total_spent)
    ).filter(
        Customer.deleted_at.is_(None)
    ).scalar() or 0
    
    segments_data = []
    
    for segment in PropensitySegment:
        score_ranges = {
            'very_high': (0.8, 1.0),
            'high': (0.6, 0.8),
            'medium': (0.4, 0.6),
            'low': (0.2, 0.4),
            'very_low': (0.0, 0.2)
        }
        
        min_score, max_score = score_ranges[segment.value]
        
        customers = db.query(Customer).filter(
            Customer.propensity_score >= min_score,
            Customer.propensity_score < max_score,
            Customer.deleted_at.is_(None)
        ).all()
        
        count = len(customers)
        total_spent = sum([c.total_spent or 0 for c in customers])
        customers_spent = len([c for c in customers if c.total_spent and c.total_spent > 0])
        
        avg_spent = total_spent / count if count > 0 else 0
        conversion_rate = customers_spent / count * 100 if count > 0 else 0
        
        # ROI Index: segment avg vs overall avg
        roi_index = (avg_spent / overall_avg_spent * 100) if overall_avg_spent > 0 else 0
        
        segments_data.append({
            'segment': segment.value,
            'customers': count,
            'total_spent': round(total_spent, 2),
            'avg_spent_per_customer': round(avg_spent, 2),
            'customers_with_purchases': customers_spent,
            'conversion_rate': round(conversion_rate, 2),
            'roi_index': round(roi_index, 2)
        })
    
    return {
        'overall_avg_spent': round(overall_avg_spent, 2),
        'segments': segments_data
    }


# ============ Scheduled Tasks ============

@router.post("/propensity-scores/schedule-daily-recalculation")
def schedule_daily_recalculation(
    background_tasks: BackgroundTasks,
    db: Session = Depends(SessionLocal)
):
    """
    Schedule daily propensity score recalculation
    
    Should be called once daily (e.g., via cron or scheduler)
    Recalculates all active customers' propensity scores
    """
    
    background_tasks.add_task(_daily_recalculation_task)
    
    return {
        "status": "scheduled",
        "message": "Daily recalculation scheduled",
        "scheduled_for": datetime.utcnow()
    }


@router.post("/propensity-scores/health")
def propensity_scoring_health(
    db: Session = Depends(SessionLocal)
):
    """Health check for propensity scoring service"""
    
    try:
        from crm_models import Customer
        
        # Check database
        count = db.query(Customer).count()
        
        # Count scored customers
        scored = db.query(Customer).filter(
            Customer.propensity_score.isnot(None)
        ).count()
        
        return {
            "status": "ok",
            "service": "propensity_scoring",
            "total_customers": count,
            "scored_customers": scored,
            "coverage": round(scored / count * 100, 2) if count > 0 else 0
        }
    
    except Exception as e:
        return {
            "status": "error",
            "service": "propensity_scoring",
            "message": str(e)
        }


# ============ Background Tasks ============

def _daily_recalculation_task():
    """Background task for daily propensity recalculation"""
    
    db = SessionLocal()
    try:
        trainer = PropensityModelTrainer(db)
        result = trainer.batch_calculate_propensity()
        print(f"Daily recalculation completed: {result['processed']} customers")
    
    except Exception as e:
        print(f"Daily recalculation error: {str(e)}")
    
    finally:
        db.close()
