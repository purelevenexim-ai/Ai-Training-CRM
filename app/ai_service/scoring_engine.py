"""
Scoring Engine - 3-part customer score (engagement + intent + value)
"""

import logging
from typing import Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)


class ScoringEngine:
    """Calculate customer AI scores"""
    
    def __init__(self, db: Session):
        """Initialize scoring engine with database session"""
        self.db = db
    
    def calculate_engagement_score(self, customer_id: str) -> int:
        """
        Calculate engagement score (0-100)
        Based on: message count, message frequency, recent activity
        """
        try:
            # Import here to avoid circular imports
            from crm_models import CustomerEvent
            
            # Count messages in last 30 days
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            message_count = self.db.query(CustomerEvent).filter(
                CustomerEvent.customer_id == customer_id,
                CustomerEvent.created_at >= thirty_days_ago
            ).count()
            
            # Score: 0 messages = 0, 10+ messages = 100
            engagement_score = min(100, message_count * 10)
            
            return int(engagement_score)
        
        except Exception as e:
            logger.error(f"Error calculating engagement score: {e}")
            return 0
    
    def calculate_purchase_intent_score(self, customer_id: str) -> int:
        """
        Calculate purchase intent score (0-100)
        Based on: intent type frequency, time since last inquiry
        """
        try:
            from crm_models import CustomerEvent
            
            # Count high-intent events
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            high_intent_events = self.db.query(CustomerEvent).filter(
                CustomerEvent.customer_id == customer_id,
                CustomerEvent.event_type.in_([
                    'PRICE_INQUIRY',
                    'SHIPPING_INQUIRY',
                    'COD_INQUIRY',
                    'PURCHASE',
                    'TRACKING_INQUIRY'
                ]),
                CustomerEvent.created_at >= thirty_days_ago
            ).count()
            
            # Score: base on frequency + recency
            # 5+ high-intent events in 30 days = high score
            intent_score = min(100, high_intent_events * 15)
            
            # Check recency (more recent = higher score)
            latest_event = self.db.query(CustomerEvent).filter(
                CustomerEvent.customer_id == customer_id
            ).order_by(CustomerEvent.created_at.desc()).first()
            
            if latest_event:
                days_since = (datetime.utcnow() - latest_event.created_at).days
                recency_bonus = max(0, 30 - days_since) * 2  # Up to 60 bonus points
                intent_score = min(100, intent_score + recency_bonus)
            
            return int(intent_score)
        
        except Exception as e:
            logger.error(f"Error calculating purchase intent score: {e}")
            return 0
    
    def calculate_customer_value_score(self, customer_id: str) -> int:
        """
        Calculate customer value score (0-100)
        Based on: total spent, order count, repeat purchase rate
        """
        try:
            from crm_models import Order, Customer
            
            customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
            if not customer:
                return 0
            
            # Get order stats
            total_spent = customer.total_spent or 0
            order_count = customer.orders_count or 0
            
            # Score components:
            # Spend score: 0 = 0%, ₹5000+ = 100%
            spend_score = min(100, (total_spent / 5000) * 100) if total_spent > 0 else 0
            
            # Repeat purchase score: 1+ orders = 20%, 5+ orders = 100%
            repeat_score = min(100, order_count * 20)
            
            # Weighted average
            value_score = (spend_score * 0.6) + (repeat_score * 0.4)
            
            return int(value_score)
        
        except Exception as e:
            logger.error(f"Error calculating customer value score: {e}")
            return 0
    
    def get_overall_score(self, customer_id: str) -> int:
        """
        Calculate overall score (0-100)
        Weighted combination:
        - Purchase Intent: 50%
        - Engagement: 25%
        - Customer Value: 25%
        """
        engagement = self.calculate_engagement_score(customer_id)
        intent = self.calculate_purchase_intent_score(customer_id)
        value = self.calculate_customer_value_score(customer_id)
        
        # Weighted average
        overall = (intent * 0.5) + (engagement * 0.25) + (value * 0.25)
        
        return int(overall)
    
    def get_lead_status(self, score: int) -> str:
        """
        Determine lead status from score
        - 0-25: Cold (no interaction)
        - 26-50: Warm (some interest)
        - 51-75: Hot (high interest)
        - 76-100: Ready (very likely to convert)
        """
        if score >= 76:
            return "Ready"
        elif score >= 51:
            return "Hot"
        elif score >= 26:
            return "Warm"
        else:
            return "Cold"
    
    def update_customer_score(self, customer_id: str) -> dict:
        """
        Update customer_ai_profile with new scores
        Returns: updated scores
        """
        try:
            from crm_models import CustomerAIProfile
            
            # Calculate all scores
            engagement = self.calculate_engagement_score(customer_id)
            intent = self.calculate_purchase_intent_score(customer_id)
            value = self.calculate_customer_value_score(customer_id)
            overall = self.get_overall_score(customer_id)
            status = self.get_lead_status(overall)
            
            # Update or create profile
            profile = self.db.query(CustomerAIProfile).filter(
                CustomerAIProfile.customer_id == customer_id
            ).first()
            
            if not profile:
                from crm_models import CustomerAIProfile
                from uuid import uuid4
                profile = CustomerAIProfile(
                    profile_id=str(uuid4()),
                    customer_id=customer_id
                )
                self.db.add(profile)
            
            profile.engagement_score = engagement
            profile.purchase_intent_score = intent
            profile.customer_value_score = value
            profile.overall_score = overall
            profile.lead_status = status
            profile.last_score_update = datetime.utcnow()
            profile.last_activity = datetime.utcnow()
            
            self.db.commit()
            
            return {
                "overall_score": overall,
                "engagement_score": engagement,
                "purchase_intent_score": intent,
                "customer_value_score": value,
                "lead_status": status
            }
        
        except Exception as e:
            logger.error(f"Error updating customer score: {e}")
            self.db.rollback()
            raise
