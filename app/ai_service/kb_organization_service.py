"""
KB Auto-Organization Service - Track and optimize Knowledge Base (Wave 0.2)
Tracks KB performance, identifies high/low performers, suggests archiving
"""

import logging
from typing import List, Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)


class KBOrganizationService:
    """Manage KB performance tracking and organization"""
    
    def __init__(self, db: Session):
        """Initialize KB organization service"""
        self.db = db
    
    def track_kb_suggestion(self, kb_id: str) -> dict:
        """
        Record that this KB entry was suggested in a response
        Called from ai_routes when KB entry is used
        """
        try:
            from crm_models import KBPerformance
            from uuid import uuid4
            
            # Find or create performance record
            perf = self.db.query(KBPerformance).filter(
                KBPerformance.kb_id == kb_id
            ).first()
            
            if not perf:
                perf = KBPerformance(
                    perf_id=str(uuid4()),
                    kb_id=kb_id,
                    times_suggested=0
                )
                self.db.add(perf)
            
            # Increment suggestion count
            perf.times_suggested += 1
            perf.last_updated = datetime.utcnow()
            
            self.db.commit()
            
            return {
                "kb_id": kb_id,
                "times_suggested": perf.times_suggested,
                "tracked": True
            }
        
        except Exception as e:
            logger.error(f"Error tracking KB suggestion: {e}")
            self.db.rollback()
            return {"tracked": False, "error": str(e)}
    
    def record_kb_rating(self, kb_id: str, helpful: bool, rating: int = None) -> dict:
        """
        Record customer feedback on KB entry
        Called when customer rates response (👍/👎)
        """
        try:
            from crm_models import KBPerformance
            
            perf = self.db.query(KBPerformance).filter(
                KBPerformance.kb_id == kb_id
            ).first()
            
            if not perf:
                from uuid import uuid4
                perf = KBPerformance(
                    perf_id=str(uuid4()),
                    kb_id=kb_id
                )
                self.db.add(perf)
            
            if helpful:
                perf.times_clicked_helpful += 1
            else:
                perf.times_marked_unhelpful += 1
            
            # Update average rating if provided
            if rating:
                if perf.average_rating == 0:
                    perf.average_rating = float(rating)
                else:
                    # Moving average
                    total_ratings = perf.times_clicked_helpful + perf.times_marked_unhelpful
                    perf.average_rating = (
                        (perf.average_rating * (total_ratings - 1) + rating) / total_ratings
                    )
            
            perf.last_updated = datetime.utcnow()
            self.db.commit()
            
            return {
                "kb_id": kb_id,
                "helpful": helpful,
                "rating": rating,
                "recorded": True
            }
        
        except Exception as e:
            logger.error(f"Error recording KB rating: {e}")
            self.db.rollback()
            return {"recorded": False, "error": str(e)}
    
    def get_kb_effectiveness_score(self, kb_id: str) -> float:
        """
        Calculate KB entry effectiveness (0-100)
        
        Formula:
        - helpfulness_rate = helpful / (helpful + unhelpful)
        - suggestion_frequency = times_suggested / 30 days
        - Effectiveness = (helpfulness_rate * 60) + (suggestion_frequency * 40)
        """
        try:
            from crm_models import KBPerformance
            
            perf = self.db.query(KBPerformance).filter(
                KBPerformance.kb_id == kb_id
            ).first()
            
            if not perf or perf.times_suggested == 0:
                return 50  # Default: neutral
            
            # Helpfulness rate
            total_ratings = perf.times_clicked_helpful + perf.times_marked_unhelpful
            if total_ratings > 0:
                helpfulness_rate = perf.times_clicked_helpful / total_ratings
            else:
                helpfulness_rate = 0.5  # Neutral if no ratings yet
            
            # Suggestion frequency (suggestions per week)
            if perf.created_at:
                days_old = (datetime.utcnow() - perf.created_at).days
                if days_old > 0:
                    suggestions_per_week = (perf.times_suggested / days_old) * 7
                else:
                    suggestions_per_week = 0
            else:
                suggestions_per_week = 0
            
            # Normalize frequency to 0-1 scale (assume 5+ per week is max)
            frequency_score = min(suggestions_per_week / 5, 1.0)
            
            # Composite score
            effectiveness = (helpfulness_rate * 0.6) + (frequency_score * 0.4)
            
            return effectiveness * 100
        
        except Exception as e:
            logger.error(f"Error calculating KB effectiveness: {e}")
            return 50
    
    def get_top_kb_entries(self, limit: int = 10) -> List[dict]:
        """
        Get top performing KB entries ranked by effectiveness
        """
        try:
            from crm_models import KBPerformance, KnowledgeBase
            
            # Get all KB entries with their performance
            entries = self.db.query(
                KnowledgeBase.kb_id,
                KnowledgeBase.question,
                KBPerformance.times_suggested,
                KBPerformance.times_clicked_helpful,
                KBPerformance.times_marked_unhelpful,
                KBPerformance.average_rating
            ).join(
                KBPerformance, KnowledgeBase.kb_id == KBPerformance.kb_id
            ).filter(
                KnowledgeBase.status == 'active'
            ).all()
            
            # Calculate effectiveness for each
            results = []
            for entry in entries:
                effectiveness = self.get_kb_effectiveness_score(entry.kb_id)
                results.append({
                    "kb_id": entry.kb_id,
                    "question": entry.question,
                    "times_suggested": entry.times_suggested,
                    "helpful_count": entry.times_clicked_helpful,
                    "unhelpful_count": entry.times_marked_unhelpful,
                    "average_rating": entry.average_rating or 0,
                    "effectiveness_score": round(effectiveness, 1)
                })
            
            # Sort by effectiveness and return top N
            results.sort(key=lambda x: x['effectiveness_score'], reverse=True)
            return results[:limit]
        
        except Exception as e:
            logger.error(f"Error getting top KB entries: {e}")
            return []
    
    def get_low_performing_entries(self, threshold: float = 30) -> List[dict]:
        """
        Get KB entries with effectiveness below threshold
        These are candidates for archiving or improvement
        """
        try:
            from crm_models import KBPerformance, KnowledgeBase
            
            entries = self.db.query(
                KnowledgeBase.kb_id,
                KnowledgeBase.question,
                KBPerformance.times_suggested,
                KBPerformance.times_clicked_helpful,
                KBPerformance.times_marked_unhelpful
            ).join(
                KBPerformance, KnowledgeBase.kb_id == KBPerformance.kb_id
            ).filter(
                KnowledgeBase.status == 'active'
            ).all()
            
            # Calculate effectiveness and filter
            results = []
            for entry in entries:
                effectiveness = self.get_kb_effectiveness_score(entry.kb_id)
                
                if effectiveness < threshold:
                    results.append({
                        "kb_id": entry.kb_id,
                        "question": entry.question,
                        "times_suggested": entry.times_suggested,
                        "helpful_count": entry.times_clicked_helpful,
                        "unhelpful_count": entry.times_marked_unhelpful,
                        "effectiveness_score": round(effectiveness, 1),
                        "recommendation": "archive" if entry.times_suggested < 5 else "improve"
                    })
            
            return results
        
        except Exception as e:
            logger.error(f"Error getting low performing entries: {e}")
            return []
    
    def archive_kb_entry(self, kb_id: str, reason: str = "low_performance") -> dict:
        """
        Archive a KB entry (soft delete, keep for analytics)
        """
        try:
            from crm_models import KnowledgeBase
            
            entry = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.kb_id == kb_id
            ).first()
            
            if not entry:
                return {"archived": False, "error": "KB entry not found"}
            
            entry.status = 'archived'
            entry.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Archived KB entry {kb_id}: {reason}")
            
            return {
                "archived": True,
                "kb_id": kb_id,
                "reason": reason
            }
        
        except Exception as e:
            logger.error(f"Error archiving KB entry: {e}")
            self.db.rollback()
            return {"archived": False, "error": str(e)}
    
    def get_kb_organization_stats(self) -> dict:
        """
        Get overall KB organization statistics
        """
        try:
            from crm_models import KnowledgeBase, KBPerformance
            
            total_entries = self.db.query(
                func.count(KnowledgeBase.kb_id)
            ).filter(
                KnowledgeBase.status == 'active'
            ).scalar() or 0
            
            archived_entries = self.db.query(
                func.count(KnowledgeBase.kb_id)
            ).filter(
                KnowledgeBase.status == 'archived'
            ).scalar() or 0
            
            total_suggestions = self.db.query(
                func.sum(KBPerformance.times_suggested)
            ).scalar() or 0
            
            total_helpful = self.db.query(
                func.sum(KBPerformance.times_clicked_helpful)
            ).scalar() or 0
            
            total_unhelpful = self.db.query(
                func.sum(KBPerformance.times_marked_unhelpful)
            ).scalar() or 0
            
            helpfulness_rate = (
                total_helpful / (total_helpful + total_unhelpful) * 100
                if (total_helpful + total_unhelpful) > 0
                else 0
            )
            
            return {
                "total_active_entries": total_entries,
                "archived_entries": archived_entries,
                "total_suggestions": total_suggestions,
                "total_helpful_votes": total_helpful,
                "total_unhelpful_votes": total_unhelpful,
                "overall_helpfulness_rate": round(helpfulness_rate, 1)
            }
        
        except Exception as e:
            logger.error(f"Error getting KB stats: {e}")
            return {}
