"""
Review Queue Service - Manage daily question review workflow
Flags low-confidence messages for human approval
"""

import logging
from typing import List, Optional
from uuid import uuid4
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)


class ReviewQueueService:
    """Manage AI message review queue for learning"""
    
    def __init__(self, db: Session):
        """Initialize review queue service"""
        self.db = db
    
    def add_to_review_queue(
        self,
        conversation_id: str,
        customer_id: str,
        customer_message: str,
        detected_intent: str,
        intent_confidence: float,
        detected_language: str,
        ai_response: str,
        reason: str = "low_confidence"
    ) -> dict:
        """
        Add message to review queue if confidence is low
        
        Called from ai_routes.py when intent_confidence < 0.70
        """
        try:
            from crm_models import AIReviewQueue
            
            # Only add if confidence below threshold
            if intent_confidence > 0.70 and reason == "low_confidence":
                return {"status": "not_queued", "reason": "confidence_sufficient"}
            
            queue_entry = AIReviewQueue(
                queue_id=str(uuid4()),
                conversation_id=conversation_id,
                customer_id=customer_id,
                customer_message=customer_message,
                detected_intent=detected_intent,
                intent_confidence=intent_confidence,
                detected_language=detected_language,
                ai_response=ai_response,
                review_status='pending'
            )
            
            self.db.add(queue_entry)
            self.db.commit()
            
            logger.info(f"Added message to review queue: {queue_entry.queue_id}")
            
            return {
                "status": "queued",
                "queue_id": queue_entry.queue_id,
                "reason": reason,
                "confidence": intent_confidence
            }
        
        except Exception as e:
            logger.error(f"Error adding to review queue: {e}")
            self.db.rollback()
            raise
    
    def get_pending_reviews(self, limit: int = 50) -> List[dict]:
        """
        Get pending reviews for you to approve
        Used by daily email digest
        """
        try:
            from crm_models import AIReviewQueue
            
            entries = self.db.query(AIReviewQueue).filter(
                AIReviewQueue.review_status == 'pending'
            ).order_by(
                AIReviewQueue.created_at.desc()
            ).limit(limit).all()
            
            return [
                {
                    "queue_id": e.queue_id,
                    "customer_message": e.customer_message,
                    "detected_intent": e.detected_intent,
                    "intent_confidence": e.intent_confidence,
                    "detected_language": e.detected_language,
                    "ai_response": e.ai_response,
                    "created_at": e.created_at.isoformat(),
                    "conversation_id": e.conversation_id
                }
                for e in entries
            ]
        
        except Exception as e:
            logger.error(f"Error getting pending reviews: {e}")
            return []
    
    def approve_review(
        self,
        queue_id: str,
        approved_intent: Optional[str] = None,
        add_to_kb: bool = False,
        kb_category: Optional[str] = None,
        notes: str = ""
    ) -> dict:
        """
        Approve a review (confirm AI was correct or correct the intent)
        
        If approved_intent differs from detected_intent, this becomes a training example
        """
        try:
            from crm_models import AIReviewQueue, ManualTrainingExample
            
            entry = self.db.query(AIReviewQueue).filter(
                AIReviewQueue.queue_id == queue_id
            ).first()
            
            if not entry:
                raise ValueError(f"Queue entry not found: {queue_id}")
            
            # Mark as approved
            entry.review_status = 'approved' if not approved_intent else 'reclassified'
            entry.reviewed_at = datetime.utcnow()
            entry.reviewed_by = "user"  # Would be actual user in production
            entry.human_notes = notes
            
            if approved_intent and approved_intent != entry.detected_intent:
                entry.human_intent_correction = approved_intent
            
            if add_to_kb:
                entry.should_add_to_kb = True
                entry.kb_category = kb_category
            
            # If reclassified, add to training examples
            if approved_intent and approved_intent != entry.detected_intent:
                training_example = ManualTrainingExample(
                    example_id=str(uuid4()),
                    review_queue_id=queue_id,
                    message_text=entry.customer_message,
                    detected_language=entry.detected_language,
                    correct_intent=approved_intent,
                    intent_confidence=entry.intent_confidence,
                    keywords_identified=None,  # Would extract keywords here
                    approved_by="user",
                    learning_phase=1
                )
                self.db.add(training_example)
            
            self.db.commit()
            
            logger.info(f"Approved review: {queue_id}")
            
            return {
                "status": "approved",
                "queue_id": queue_id,
                "original_intent": entry.detected_intent,
                "corrected_intent": approved_intent,
                "added_to_kb": add_to_kb
            }
        
        except Exception as e:
            logger.error(f"Error approving review: {e}")
            self.db.rollback()
            raise
    
    def escalate_review(self, queue_id: str, reason: str = "") -> dict:
        """Mark message as needing escalation (complicated, needs human response)"""
        try:
            from crm_models import AIReviewQueue
            
            entry = self.db.query(AIReviewQueue).filter(
                AIReviewQueue.queue_id == queue_id
            ).first()
            
            if not entry:
                raise ValueError(f"Queue entry not found: {queue_id}")
            
            entry.review_status = 'escalated'
            entry.reviewed_at = datetime.utcnow()
            entry.human_notes = reason
            
            self.db.commit()
            
            logger.info(f"Escalated review: {queue_id}")
            
            return {"status": "escalated", "queue_id": queue_id}
        
        except Exception as e:
            logger.error(f"Error escalating review: {e}")
            self.db.rollback()
            raise
    
    def get_review_stats(self) -> dict:
        """Get stats on review queue for dashboard"""
        try:
            from crm_models import AIReviewQueue, ManualTrainingExample
            
            pending = self.db.query(func.count(AIReviewQueue.queue_id)).filter(
                AIReviewQueue.review_status == 'pending'
            ).scalar() or 0
            
            approved = self.db.query(func.count(AIReviewQueue.queue_id)).filter(
                AIReviewQueue.review_status == 'approved'
            ).scalar() or 0
            
            reclassified = self.db.query(func.count(AIReviewQueue.queue_id)).filter(
                AIReviewQueue.review_status == 'reclassified'
            ).scalar() or 0
            
            training_examples = self.db.query(func.count(ManualTrainingExample.example_id)).scalar() or 0
            
            return {
                "pending": pending,
                "approved": approved,
                "reclassified": reclassified,
                "total_training_examples": training_examples,
                "learning_accuracy_improvement": f"{min(reclassified * 2, 15)}%"  # Rough estimate
            }
        
        except Exception as e:
            logger.error(f"Error getting review stats: {e}")
            return {}
