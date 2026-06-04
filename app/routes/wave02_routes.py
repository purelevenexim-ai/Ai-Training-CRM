"""
Wave 0.2 Complete API Routes
Review queue + Learning engine + Advanced scoring + KB organization + Feature toggles
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from app.ai_service.review_queue_service import ReviewQueueService
from app.ai_service.learning_engine import LearningEngine
from app.ai_service.advanced_scoring_engine import AdvancedScoringEngine
from app.ai_service.kb_organization_service import KBOrganizationService
from app.ai_service.feature_toggle_service import FeatureToggleService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai/wave02", tags=["wave02"])


# ─── PYDANTIC MODELS ────────────────────────────────────────────────────────

class ApproveReviewRequest(BaseModel):
    queue_id: str
    approved_intent: Optional[str] = None
    add_to_kb: bool = False
    kb_category: Optional[str] = None
    notes: str = ""


class EscalateReviewRequest(BaseModel):
    queue_id: str
    reason: str


class ToggleFeatureRequest(BaseModel):
    feature_key: str
    enabled: bool


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: REVIEW QUEUE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/review/pending")
async def get_pending_reviews(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
) -> dict:
    """Get pending reviews for daily approval"""
    try:
        service = ReviewQueueService(db)
        reviews = service.get_pending_reviews(limit=limit)
        return {"count": len(reviews), "reviews": reviews}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/review/approve")
async def approve_review(request: ApproveReviewRequest, db: Session = Depends(get_db)) -> dict:
    """Approve a review"""
    try:
        service = ReviewQueueService(db)
        result = service.approve_review(
            queue_id=request.queue_id,
            approved_intent=request.approved_intent,
            add_to_kb=request.add_to_kb,
            kb_category=request.kb_category,
            notes=request.notes
        )
        return result
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/review/escalate")
async def escalate_review(request: EscalateReviewRequest, db: Session = Depends(get_db)) -> dict:
    """Escalate a review"""
    try:
        service = ReviewQueueService(db)
        result = service.escalate_review(queue_id=request.queue_id, reason=request.reason)
        return result
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/review/stats")
async def get_review_stats(db: Session = Depends(get_db)) -> dict:
    """Get review queue statistics"""
    try:
        service = ReviewQueueService(db)
        return service.get_review_stats()
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/review/daily-summary")
async def get_daily_summary(db: Session = Depends(get_db)) -> dict:
    """Get daily summary for email digest"""
    try:
        service = ReviewQueueService(db)
        return service.get_pending_reviews(limit=10)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: LEARNING ENGINE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/learning/progress")
async def get_learning_progress(db: Session = Depends(get_db)) -> dict:
    """Get learning progress metrics"""
    try:
        engine = LearningEngine(db)
        return engine.get_learning_progress()
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/batch")
async def get_learning_batch(limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db)) -> dict:
    """Get latest training examples"""
    try:
        engine = LearningEngine(db)
        examples = engine.get_learning_batch(limit=limit)
        return {"count": len(examples), "examples": examples}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/intent-distribution")
async def get_intent_distribution(db: Session = Depends(get_db)) -> dict:
    """Intent distribution in training examples"""
    try:
        engine = LearningEngine(db)
        distribution = engine.get_intent_distribution()
        return {"distribution": distribution, "total": sum(distribution.values())}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/learning/keywords/{intent}")
async def get_suggested_keywords(intent: str, limit: int = Query(10, ge=1, le=20), db: Session = Depends(get_db)) -> dict:
    """Get suggested keywords for an intent"""
    try:
        engine = LearningEngine(db)
        keywords = engine.suggest_new_keywords_for_intent(intent, limit=limit)
        return {"intent": intent, "suggested_keywords": keywords}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 3: ADVANCED SCORING ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/scoring/customer/{customer_id}")
async def get_customer_advanced_scores(customer_id: str, db: Session = Depends(get_db)) -> dict:
    """Get advanced scores for a customer"""
    try:
        engine = AdvancedScoringEngine(db)
        result = engine.update_customer_advanced_scores(customer_id)
        return result
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scoring/churn/{customer_id}")
async def get_churn_risk(customer_id: str, db: Session = Depends(get_db)) -> dict:
    """Get churn risk score"""
    try:
        engine = AdvancedScoringEngine(db)
        score = engine.calculate_churn_risk_score(customer_id)
        quality = engine.calculate_response_quality_score(customer_id)
        return {"customer_id": customer_id, "churn_risk": score, "response_quality": quality}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scoring/batch-update")
async def batch_update_scores(db: Session = Depends(get_db)) -> dict:
    """Batch update scores for all customers"""
    try:
        from crm_models import Customer
        engine = AdvancedScoringEngine(db)
        
        customers = db.query(Customer).all()
        updated_count = 0
        
        for customer in customers:
            try:
                engine.update_customer_advanced_scores(customer.id)
                updated_count += 1
            except Exception as e:
                logger.warning(f"Failed to update {customer.id}: {e}")
        
        return {"updated_count": updated_count, "total_customers": len(customers)}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 4: KB ORGANIZATION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/kb/top-performing")
async def get_top_kb_entries(limit: int = Query(10, ge=1, le=50), db: Session = Depends(get_db)) -> dict:
    """Get top performing KB entries"""
    try:
        service = KBOrganizationService(db)
        entries = service.get_top_kb_entries(limit=limit)
        return {"count": len(entries), "entries": entries}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kb/low-performing")
async def get_low_performing_kb(threshold: float = Query(30, ge=0, le=100), db: Session = Depends(get_db)) -> dict:
    """Get low performing KB entries (candidates for archiving)"""
    try:
        service = KBOrganizationService(db)
        entries = service.get_low_performing_entries(threshold=threshold)
        return {"threshold": threshold, "count": len(entries), "entries": entries}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kb/archive/{kb_id}")
async def archive_kb_entry(kb_id: str, reason: str = Query("low_performance"), db: Session = Depends(get_db)) -> dict:
    """Archive a KB entry"""
    try:
        service = KBOrganizationService(db)
        return service.archive_kb_entry(kb_id, reason=reason)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kb/stats")
async def get_kb_stats(db: Session = Depends(get_db)) -> dict:
    """Get KB organization statistics"""
    try:
        service = KBOrganizationService(db)
        return service.get_kb_organization_stats()
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 5: FEATURE TOGGLE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/features/all")
async def get_all_features(db: Session = Depends(get_db)) -> dict:
    """Get all feature toggles"""
    try:
        service = FeatureToggleService(db)
        features = service.get_all_features()
        return {"count": len(features), "features": features}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/features/category/{category}")
async def get_features_by_category(category: str, db: Session = Depends(get_db)) -> dict:
    """Get features in a category"""
    try:
        service = FeatureToggleService(db)
        features = service.get_features_by_category(category)
        return {"category": category, "count": len(features), "features": features}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/features/status")
async def get_feature_status(db: Session = Depends(get_db)) -> dict:
    """Get feature status summary"""
    try:
        service = FeatureToggleService(db)
        return service.get_feature_status_summary()
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/features/toggle")
async def toggle_feature(request: ToggleFeatureRequest, db: Session = Depends(get_db)) -> dict:
    """Toggle a feature on/off"""
    try:
        service = FeatureToggleService(db)
        return service.toggle_feature(request.feature_key, request.enabled)
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/features/check/{feature_key}")
async def check_feature_enabled(feature_key: str, db: Session = Depends(get_db)) -> dict:
    """Check if a specific feature is enabled"""
    try:
        service = FeatureToggleService(db)
        enabled = service.is_feature_enabled(feature_key)
        return {"feature_key": feature_key, "enabled": enabled}
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 6: DASHBOARD ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/dashboard/summary")
async def get_wave_0_2_summary(db: Session = Depends(get_db)) -> dict:
    """Get Wave 0.2 complete summary"""
    try:
        review_service = ReviewQueueService(db)
        learning_engine = LearningEngine(db)
        kb_service = KBOrganizationService(db)
        feature_service = FeatureToggleService(db)
        
        return {
            "review_queue": review_service.get_review_stats(),
            "learning": learning_engine.get_learning_progress(),
            "kb": kb_service.get_kb_organization_stats(),
            "features": feature_service.get_feature_status_summary()
        }
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
