"""
Advanced Scoring Engine v2 - Enhanced 6D Customer Scoring (Wave 0.2)
Adds response_quality_score and churn_risk_score to base scoring
"""

import logging
from typing import Dict
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger(__name__)


class AdvancedScoringEngine:
    """Enhanced customer scoring with quality and churn metrics"""
    
    def __init__(self, db: Session):
        """Initialize advanced scoring engine"""
        self.db = db
    
    def calculate_response_quality_score(self, customer_id: str) -> float:
        """
        Calculate average response quality (1-5 stars)
        Based on customer feedback on AI responses
        
        Returns: 0-5 (average rating)
        """
        try:
            from crm_models import ResponseQualityFeedback
            
            ratings = self.db.query(
                func.avg(ResponseQualityFeedback.rating)
            ).filter(
                ResponseQualityFeedback.customer_id == customer_id,
                ResponseQualityFeedback.rating.isnot(None)
            ).scalar()
            
            # If no ratings, default to 3.5 (neutral)
            return float(ratings) if ratings else 3.5
        
        except Exception as e:
            logger.error(f"Error calculating response quality score: {e}")
            return 3.5
    
    def calculate_churn_risk_score(self, customer_id: str) -> int:
        """
        Calculate churn risk (0-100 scale)
        
        Factors:
        - Days since last activity (most important)
        - Message frequency trend
        - Order frequency trend
        - Purchase intent score
        
        Returns: 0-100 (0=no risk, 100=certain churn)
        """
        try:
            from crm_models import Customer, CustomerEvent, Order
            from datetime import datetime, timedelta
            
            customer = self.db.query(Customer).filter(
                Customer.id == customer_id
            ).first()
            
            if not customer:
                return 0
            
            now = datetime.utcnow()
            
            # 1. Days since last activity
            last_message = self.db.query(
                func.max(CustomerEvent.created_at)
            ).filter(
                CustomerEvent.customer_id == customer_id
            ).scalar()
            
            if last_message:
                days_inactive = (now - last_message).days
            else:
                days_inactive = 365  # Never messaged = high risk
            
            # Scoring: 0 days = 0 risk, 7 days = 20, 14 = 50, 30 = 80, 60+ = 100
            if days_inactive <= 7:
                activity_risk = days_inactive * 3  # 0-21
            elif days_inactive <= 14:
                activity_risk = 20 + (days_inactive - 7) * 4  # 20-48
            elif days_inactive <= 30:
                activity_risk = 50 + (days_inactive - 14) * 2  # 50-82
            else:
                activity_risk = min(85 + (days_inactive - 30), 100)  # 85-100
            
            # 2. Order recency
            last_order = self.db.query(
                func.max(Order.created_at)
            ).filter(
                Order.customer_id == customer_id
            ).scalar()
            
            if last_order:
                days_since_order = (now - last_order).days
            else:
                days_since_order = 365  # Never ordered
            
            # Scoring: 0-90 days = 0 risk, 90-180 = 30-70, 180+ = 100
            if days_since_order <= 90:
                order_risk = 0
            elif days_since_order <= 180:
                order_risk = (days_since_order - 90) * 0.67  # 0-60
            else:
                order_risk = min(70 + (days_since_order - 180) / 5, 100)
            
            # 3. Message frequency (declining messages = churn signal)
            messages_last_7d = self.db.query(
                func.count(CustomerEvent.event_id)
            ).filter(
                CustomerEvent.customer_id == customer_id,
                CustomerEvent.created_at >= (now - timedelta(days=7))
            ).scalar() or 0
            
            messages_prev_7d = self.db.query(
                func.count(CustomerEvent.event_id)
            ).filter(
                CustomerEvent.customer_id == customer_id,
                CustomerEvent.created_at >= (now - timedelta(days=14)),
                CustomerEvent.created_at < (now - timedelta(days=7))
            ).scalar() or 0
            
            # If declining messages trend, increase risk
            if messages_last_7d < messages_prev_7d / 2:
                frequency_risk = 20  # Engagement dropping
            elif messages_last_7d == 0 and messages_prev_7d > 0:
                frequency_risk = 40  # Stopped messaging
            else:
                frequency_risk = 0
            
            # Calculate weighted churn risk
            # Activity: 50% (most important)
            # Order recency: 30%
            # Message frequency trend: 20%
            churn_risk = (
                activity_risk * 0.5 +
                order_risk * 0.3 +
                frequency_risk * 0.2
            )
            
            return min(int(churn_risk), 100)
        
        except Exception as e:
            logger.error(f"Error calculating churn risk score: {e}")
            return 50  # Default to moderate risk on error
    
    def get_next_best_action(self, customer_id: str, profile: Dict) -> str:
        """
        Determine recommended action based on customer scores
        
        Logic:
        - High value + Cold → "Call Now"
        - Warm + High intent → "Send Offer"
        - Hot + Active → "Nurture"
        - Churn risk high → "Win Back Campaign"
        - Low quality response → "Manual Review Needed"
        """
        try:
            overall_score = profile.get('overall_score', 50)
            churn_risk = profile.get('churn_risk_score', 50)
            response_quality = profile.get('response_quality_score', 3.5)
            
            # High value at risk
            if profile.get('customer_value_score', 0) >= 70 and churn_risk > 70:
                return "⚠️ VIP Churn Risk - Call Now"
            
            # Recent high intent = send offer
            if profile.get('purchase_intent_score', 0) >= 70 and overall_score >= 50:
                return "🎯 Send Hot Offer"
            
            # Poor response quality
            if response_quality < 3.0:
                return "⚠️ Manual Review Needed"
            
            # High churn risk
            if churn_risk > 70:
                return "💔 Win Back Campaign"
            
            # Warm engagement
            if overall_score >= 40 and churn_risk < 50:
                return "🌱 Nurture & Engage"
            
            # New customer
            if profile.get('engagement_score', 0) < 20:
                return "👋 Welcome Series"
            
            # Default
            return "📊 Monitor"
        
        except Exception as e:
            logger.error(f"Error determining next action: {e}")
            return "Monitor"
    
    def update_customer_advanced_scores(self, customer_id: str) -> dict:
        """
        Update customer_ai_profile with all scores including advanced metrics
        
        This is the main entry point for score updates
        """
        try:
            from crm_models import CustomerAIProfile
            from app.ai_service.scoring_engine import ScoringEngine
            
            # Get base scoring engine
            base_engine = ScoringEngine(self.db)
            
            # Calculate all scores
            engagement_score = base_engine.calculate_engagement_score(customer_id)
            purchase_intent_score = base_engine.calculate_purchase_intent_score(customer_id)
            customer_value_score = base_engine.calculate_customer_value_score(customer_id)
            response_quality_score = self.calculate_response_quality_score(customer_id)
            churn_risk_score = self.calculate_churn_risk_score(customer_id)
            
            # Calculate overall score (base 3D scoring)
            overall_score = (
                purchase_intent_score * 0.5 +
                engagement_score * 0.25 +
                customer_value_score * 0.25
            )
            
            # Get lead status from base engine
            lead_status = base_engine.get_lead_status(int(overall_score))
            
            # Determine next action
            profile = {
                'overall_score': overall_score,
                'engagement_score': engagement_score,
                'purchase_intent_score': purchase_intent_score,
                'customer_value_score': customer_value_score,
                'response_quality_score': response_quality_score,
                'churn_risk_score': churn_risk_score
            }
            next_action = self.get_next_best_action(customer_id, profile)
            
            # Update or create profile
            profile_record = self.db.query(CustomerAIProfile).filter(
                CustomerAIProfile.customer_id == customer_id
            ).first()
            
            if profile_record:
                profile_record.overall_score = int(overall_score)
                profile_record.engagement_score = engagement_score
                profile_record.purchase_intent_score = purchase_intent_score
                profile_record.customer_value_score = customer_value_score
                profile_record.response_quality_score = response_quality_score
                profile_record.churn_risk_score = churn_risk_score
                profile_record.lead_status = lead_status
                profile_record.next_action = next_action
                profile_record.updated_at = datetime.utcnow()
            else:
                from uuid import uuid4
                profile_record = CustomerAIProfile(
                    profile_id=str(uuid4()),
                    customer_id=customer_id,
                    overall_score=int(overall_score),
                    engagement_score=engagement_score,
                    purchase_intent_score=purchase_intent_score,
                    customer_value_score=customer_value_score,
                    response_quality_score=response_quality_score,
                    churn_risk_score=churn_risk_score,
                    lead_status=lead_status,
                    next_action=next_action
                )
                self.db.add(profile_record)
            
            self.db.commit()
            
            logger.info(f"Updated advanced scores for {customer_id}: Overall={int(overall_score)}, ChurnRisk={churn_risk_score}, Quality={response_quality_score}")
            
            return {
                "customer_id": customer_id,
                "overall_score": int(overall_score),
                "engagement_score": engagement_score,
                "purchase_intent_score": purchase_intent_score,
                "customer_value_score": customer_value_score,
                "response_quality_score": response_quality_score,
                "churn_risk_score": churn_risk_score,
                "lead_status": lead_status,
                "next_action": next_action
            }
        
        except Exception as e:
            logger.error(f"Error updating advanced scores: {e}")
            self.db.rollback()
            raise
