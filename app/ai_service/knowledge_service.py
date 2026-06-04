"""
Knowledge Service - FAQ and KB lookup
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

logger = logging.getLogger(__name__)


class KnowledgeService:
    """Knowledge base lookups"""
    
    def __init__(self, db: Session):
        """Initialize knowledge service"""
        self.db = db
    
    def search_kb(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 5
    ) -> List[dict]:
        """
        Search knowledge base for relevant entries
        
        Uses simple text matching on question + answer
        
        Returns list of dicts with:
        - kb_id
        - question
        - answer
        - category
        """
        try:
            from crm_models import KnowledgeBase
            
            # Start with active entries
            q = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.status == 'active'
            )
            
            # Filter by category if provided
            if category:
                q = q.filter(KnowledgeBase.category.ilike(f"%{category}%"))
            
            # Search by query (question + answer)
            if query:
                search_term = f"%{query}%"
                q = q.filter(
                    or_(
                        KnowledgeBase.question.ilike(search_term),
                        KnowledgeBase.answer.ilike(search_term)
                    )
                )
            
            entries = q.limit(limit).all()
            
            return [
                {
                    "kb_id": e.kb_id,
                    "question": e.question,
                    "answer": e.answer,
                    "category": e.category
                }
                for e in entries
            ]
        
        except Exception as e:
            logger.error(f"Error searching KB: {e}")
            return []
    
    def get_kb_by_category(self, category: str, limit: int = 10) -> List[dict]:
        """
        Get all KB entries in a category
        """
        try:
            from crm_models import KnowledgeBase
            
            entries = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.category.ilike(f"%{category}%"),
                KnowledgeBase.status == 'active'
            ).limit(limit).all()
            
            return [
                {
                    "kb_id": e.kb_id,
                    "question": e.question,
                    "answer": e.answer,
                    "category": e.category
                }
                for e in entries
            ]
        
        except Exception as e:
            logger.error(f"Error getting KB by category: {e}")
            return []
    
    def get_all_kb(self, limit: int = 100) -> List[dict]:
        """
        Get all active KB entries
        """
        try:
            from crm_models import KnowledgeBase
            
            entries = self.db.query(KnowledgeBase).filter(
                KnowledgeBase.status == 'active'
            ).limit(limit).all()
            
            return [
                {
                    "kb_id": e.kb_id,
                    "question": e.question,
                    "answer": e.answer,
                    "category": e.category
                }
                for e in entries
            ]
        
        except Exception as e:
            logger.error(f"Error getting all KB: {e}")
            return []
