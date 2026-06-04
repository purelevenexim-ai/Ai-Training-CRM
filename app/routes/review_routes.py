"""
Wave 0.2 Review & Learning API Routes
Daily review workflow endpoints + learning progress tracking
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from database import get_db
from crm_models import AIReviewQueue
from app.ai_service.review_queue_service import ReviewQueueService
from app.ai_service.learning_engine import LearningEngine

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai/review", tags=["review"])


# ─── PYDANTIC MODELS ────────────────────────────────────────────────────────

class ApproveReviewRequest(BaseModel):
    """Approve a review"""
    queue_id: str
    approved_intent: Optional[str] = None  # If different from detected
    add_to_kb: bool = False
    kb_category: Optional[str] = None
    notes: str = ""


class EscalateReviewRequest(BaseModel):
    """Escalate a review"""
    queue_id: str
    reason: str


# ─── ENDPOINT 1: GET /api/ai/review/pending ─────────────────────────────────

@router.get("/pending")
async def get_pending_reviews(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get pending reviews for daily approval workflow
    Shows messages that AI had low confidence on
    """
    try:
        service = ReviewQueueService(db)
        reviews = service.get_pending_reviews(limit=limit)
        
        return {
            "count": len(reviews),
            "reviews": reviews
        }
    
    except Exception as e:
        logger.error(f"Error getting pending reviews: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── ENDPOINT 2: POST /api/ai/review/approve ────────────────────────────────

@router.post("/approve")
async def approve_review(
    request: ApproveReviewRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Approve a review (confirm AI was correct or correct the intent)
    If you correct the intent, it becomes a training example
    """
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
        logger.error(f"Error approving review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── ENDPOINT 3: POST /api/ai/review/escalate ───────────────────────────────

@router.post("/escalate")
async def escalate_review(
    request: EscalateReviewRequest,
    db: Session = Depends(get_db)
) -> dict:
    """
    Escalate a review (mark as needing manual response)
    """
    try:
        service = ReviewQueueService(db)
        result = service.escalate_review(
            queue_id=request.queue_id,
            reason=request.reason
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error escalating review: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── ENDPOINT 4: GET /api/ai/review/stats ───────────────────────────────────

@router.get("/stats")
async def get_review_stats(db: Session = Depends(get_db)) -> dict:
    """Get review queue statistics"""
    try:
        service = ReviewQueueService(db)
        stats = service.get_review_stats()
        
        return stats
    
    except Exception as e:
        logger.error(f"Error getting review stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── ENDPOINT 5: GET /api/ai/learning/progress ──────────────────────────────

@router.get("/learning/progress")
async def get_learning_progress(db: Session = Depends(get_db)) -> dict:
    """
    Get learning progress metrics
    Shows accuracy improvement from manual training
    """
    try:
        engine = LearningEngine(db)
        progress = engine.get_learning_progress()
        
        return progress
    
    except Exception as e:
        logger.error(f"Error getting learning progress: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── ENDPOINT 6: GET /api/ai/learning/batch ─────────────────────────────────

@router.get("/learning/batch")
async def get_learning_batch(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
) -> dict:
    """Get latest training examples for analysis"""
    try:
        engine = LearningEngine(db)
        examples = engine.get_learning_batch(limit=limit)
        
        return {
            "count": len(examples),
            "examples": examples
        }
    
    except Exception as e:
        logger.error(f"Error getting learning batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── ENDPOINT 7: GET /api/ai/learning/intent-distribution ───────────────────

@router.get("/learning/intent-distribution")
async def get_intent_distribution(db: Session = Depends(get_db)) -> dict:
    """
    Show which intents are most common in training examples
    Helps identify where rule engine needs improvement
    """
    try:
        engine = LearningEngine(db)
        distribution = engine.get_intent_distribution()
        
        return {
            "distribution": distribution,
            "total": sum(distribution.values())
        }
    
    except Exception as e:
        logger.error(f"Error getting intent distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── ENDPOINT 8: GET /api/ai/learning/keywords/{intent} ─────────────────────

@router.get("/learning/keywords/{intent}")
async def get_suggested_keywords(
    intent: str,
    limit: int = Query(10, ge=1, le=20),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get suggested keywords for an intent from training examples
    These could be added to rule engine later
    """
    try:
        engine = LearningEngine(db)
        keywords = engine.suggest_new_keywords_for_intent(intent, limit=limit)
        
        return {
            "intent": intent,
            "suggested_keywords": keywords
        }
    
    except Exception as e:
        logger.error(f"Error getting keywords: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── ENDPOINT 9: GET /api/ai/learning/language-distribution ────────────────

@router.get("/learning/language-distribution")
async def get_language_distribution(db: Session = Depends(get_db)) -> dict:
    """
    Show language distribution in training examples
    """
    try:
        engine = LearningEngine(db)
        distribution = engine.get_language_distribution()
        
        return {
            "distribution": distribution,
            "total": sum(distribution.values())
        }
    
    except Exception as e:
        logger.error(f"Error getting language distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ─── ENDPOINT 10: GET /api/ai/review/daily-summary ─────────────────────────

@router.get("/daily-summary")
async def get_daily_summary(db: Session = Depends(get_db)) -> dict:
    """
    Get daily summary for email digest
    Shows: pending reviews, learning progress, new KB entries
    """
    try:
        review_service = ReviewQueueService(db)
        learning_engine = LearningEngine(db)
        
        pending_reviews = review_service.get_pending_reviews(limit=10)
        review_stats = review_service.get_review_stats()
        learning_progress = learning_engine.get_learning_progress()
        
        return {
            "date": str(__import__('datetime').datetime.utcnow().date()),
            "pending_count": len(pending_reviews),
            "pending_samples": pending_reviews[:3],  # First 3 for email
            "review_stats": review_stats,
            "learning_progress": learning_progress
        }
    
    except Exception as e:
        logger.error(f"Error getting daily summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))
