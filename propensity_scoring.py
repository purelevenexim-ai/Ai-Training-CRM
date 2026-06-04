"""
ML Propensity Scoring Engine
Predicts customer likelihood to convert using RFM + engagement features
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import math
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import func


class PropensitySegment(str, Enum):
    """Propensity-based customer segments"""
    VERY_HIGH = "very_high"      # 0.8-1.0 - Likely converters
    HIGH = "high"                 # 0.6-0.8 - Good prospects
    MEDIUM = "medium"             # 0.4-0.6 - Nurture needed
    LOW = "low"                   # 0.2-0.4 - Cold leads
    VERY_LOW = "very_low"        # 0.0-0.2 - Not ready


class PropensityCalculator:
    """
    ML Propensity Score Calculator
    
    Algorithm: RFM + Engagement + Temporal Features
    Formula: Normalized weighted combination of all factors
    
    Components:
    - Recency (40%): Days since last event (lower = better)
    - Frequency (30%): Total events (higher = better)
    - Monetary (20%): Total spend (higher = better)
    - Engagement (10%): Email/SMS engagement (higher = better)
    """
    
    def __init__(self, db: Session):
        """Initialize calculator with database session"""
        self.db = db
        
    def calculate_propensity_score(self, customer_id: str) -> Dict:
        """
        Calculate comprehensive propensity score for customer
        
        Args:
            customer_id: Customer UUID
        
        Returns:
            {
                propensity_score: float (0.0-1.0),
                segment: str (very_high, high, medium, low, very_low),
                breakdown: {
                    recency_score: float,
                    frequency_score: float,
                    monetary_score: float,
                    engagement_score: float,
                    lead_quality_score: float
                },
                factors: {
                    days_since_last_event: int,
                    event_count_30d: int,
                    event_count_90d: int,
                    total_events: int,
                    total_spent: float,
                    email_engagement_rate: float,
                    sms_engagement_rate: float,
                    lead_status: str,
                    lead_source: str
                },
                model_version: str,
                calculated_at: datetime
            }
        """
        from crm_models import Customer, Journey, JourneyEnrollment
        
        # Get customer
        customer = self.db.query(Customer).filter(
            Customer.id == customer_id
        ).first()
        
        if not customer:
            return {
                'propensity_score': 0.0,
                'segment': PropensitySegment.VERY_LOW.value,
                'error': 'Customer not found'
            }
        
        # Calculate component scores
        recency_score, days_since_last = self._calculate_recency_score(customer_id)
        frequency_score, event_count = self._calculate_frequency_score(customer_id)
        monetary_score, total_spent = self._calculate_monetary_score(customer_id)
        engagement_score = self._calculate_engagement_score(customer)
        lead_quality_score = self._calculate_lead_quality_score(customer)
        
        # Weighted combination
        propensity_score = (
            recency_score * 0.40 +      # Recency: 40%
            frequency_score * 0.30 +    # Frequency: 30%
            monetary_score * 0.20 +     # Monetary: 20%
            engagement_score * 0.05 +   # Engagement: 5%
            lead_quality_score * 0.05   # Lead quality: 5%
        )
        
        # Normalize to 0-1
        propensity_score = min(1.0, max(0.0, propensity_score))
        
        # Determine segment
        segment = self._get_segment(propensity_score)
        
        return {
            'propensity_score': round(propensity_score, 4),
            'segment': segment,
            'breakdown': {
                'recency_score': round(recency_score, 4),
                'frequency_score': round(frequency_score, 4),
                'monetary_score': round(monetary_score, 4),
                'engagement_score': round(engagement_score, 4),
                'lead_quality_score': round(lead_quality_score, 4)
            },
            'factors': {
                'days_since_last_event': days_since_last,
                'event_count_30d': self._get_event_count(customer_id, days=30),
                'event_count_90d': self._get_event_count(customer_id, days=90),
                'total_events': self._get_total_event_count(customer_id),
                'total_spent': round(customer.total_spent or 0.0, 2),
                'email_subscribed': customer.email_subscribed,
                'sms_subscribed': customer.sms_subscribed,
                'lead_status': customer.lead_status,
                'lead_source': customer.lead_source,
                'orders_count': customer.orders_count or 0,
                'last_order_date': customer.last_order_date
            },
            'model_version': '1.0',
            'calculated_at': datetime.utcnow()
        }
    
    def _calculate_recency_score(self, customer_id: str) -> Tuple[float, int]:
        """
        Calculate recency score (0-1)
        
        Logic:
        - 0 days ago: 1.0 (perfect)
        - 30 days ago: 0.5 (medium)
        - 90+ days ago: 0.0 (very stale)
        - Never interacted: 0.0
        """
        from crm_models import Customer
        
        customer = self.db.query(Customer).filter(
            Customer.id == customer_id
        ).first()
        
        if not customer or not customer.last_order_date:
            return 0.0, 999  # Very stale
        
        days_since = (datetime.utcnow() - customer.last_order_date).days
        
        if days_since <= 0:
            score = 1.0
        elif days_since <= 30:
            # Linear decay from 1.0 to 0.5
            score = 1.0 - (days_since / 60.0)
        elif days_since <= 90:
            # Decay from 0.5 to 0.1
            score = 0.5 - ((days_since - 30) / 240.0)
        else:
            score = 0.0
        
        return max(0.0, min(1.0, score)), days_since
    
    def _calculate_frequency_score(self, customer_id: str) -> Tuple[float, int]:
        """
        Calculate frequency score (0-1)
        
        Logic:
        - 0 events: 0.0
        - 1-5 events: 0.3
        - 6-20 events: 0.6
        - 21-50 events: 0.8
        - 50+ events: 1.0
        """
        from crm_models import Customer
        
        customer = self.db.query(Customer).filter(
            Customer.id == customer_id
        ).first()
        
        if not customer:
            return 0.0, 0
        
        order_count = customer.orders_count or 0
        
        if order_count == 0:
            score = 0.0
        elif order_count <= 5:
            score = 0.3
        elif order_count <= 20:
            score = 0.6
        elif order_count <= 50:
            score = 0.8
        else:
            score = 1.0
        
        return score, order_count
    
    def _calculate_monetary_score(self, customer_id: str) -> Tuple[float, float]:
        """
        Calculate monetary score (0-1)
        
        Logic (in INR):
        - 0 spent: 0.0
        - ₹1-1000: 0.2
        - ₹1001-5000: 0.4
        - ₹5001-15000: 0.6
        - ₹15001-50000: 0.8
        - ₹50000+: 1.0
        """
        from crm_models import Customer
        
        customer = self.db.query(Customer).filter(
            Customer.id == customer_id
        ).first()
        
        if not customer:
            return 0.0, 0.0
        
        spent = customer.total_spent or 0.0
        
        if spent == 0:
            score = 0.0
        elif spent <= 1000:
            score = 0.2
        elif spent <= 5000:
            score = 0.4
        elif spent <= 15000:
            score = 0.6
        elif spent <= 50000:
            score = 0.8
        else:
            score = 1.0
        
        return score, spent
    
    def _calculate_engagement_score(self, customer) -> float:
        """
        Calculate engagement score (0-1)
        
        Logic:
        - Not subscribed to any: 0.0
        - Email subscribed: 0.5
        - SMS subscribed: 0.5
        - Both subscribed: 1.0
        """
        score = 0.0
        
        if customer.email_subscribed:
            score += 0.5
        
        if customer.sms_subscribed:
            score += 0.5
        
        return score
    
    def _calculate_lead_quality_score(self, customer) -> float:
        """
        Calculate lead quality score (0-1)
        
        Logic:
        - No lead data: 0.0
        - Lead status 'new': 0.2
        - Lead status 'contacted': 0.4
        - Lead status 'qualified': 0.8
        - Lead status 'customer': 1.0
        - Lead status 'lost': 0.0
        """
        if not customer.is_lead:
            return 0.0
        
        status_scores = {
            'new': 0.2,
            'contacted': 0.4,
            'qualified': 0.8,
            'customer': 1.0,
            'lost': 0.0
        }
        
        return status_scores.get(customer.lead_status, 0.0)
    
    def _get_event_count(self, customer_id: str, days: int) -> int:
        """Get event count in last N days"""
        from crm_models import Customer
        
        customer = self.db.query(Customer).filter(
            Customer.id == customer_id
        ).first()
        
        if not customer or not customer.last_order_date:
            return 0
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        if customer.last_order_date < cutoff_date:
            return 0
        
        # Simplified: use orders_count as proxy for events
        return customer.orders_count or 0
    
    def _get_total_event_count(self, customer_id: str) -> int:
        """Get total event count for customer"""
        from crm_models import Customer
        
        customer = self.db.query(Customer).filter(
            Customer.id == customer_id
        ).first()
        
        if not customer:
            return 0
        
        return customer.orders_count or 0
    
    def _get_segment(self, score: float) -> str:
        """Map score to segment"""
        if score >= 0.8:
            return PropensitySegment.VERY_HIGH.value
        elif score >= 0.6:
            return PropensitySegment.HIGH.value
        elif score >= 0.4:
            return PropensitySegment.MEDIUM.value
        elif score >= 0.2:
            return PropensitySegment.LOW.value
        else:
            return PropensitySegment.VERY_LOW.value


class PropensityModelTrainer:
    """
    Training and persistence for propensity model
    Handles batch scoring, caching, and periodic retraining
    """
    
    def __init__(self, db: Session):
        """Initialize trainer"""
        self.db = db
        self.calculator = PropensityCalculator(db)
    
    def batch_calculate_propensity(self, customer_ids: Optional[List[str]] = None) -> Dict:
        """
        Batch calculate propensity scores for multiple customers
        
        Args:
            customer_ids: List of customer IDs (None = all customers)
        
        Returns:
            {
                status: 'success',
                processed: int,
                errors: List[str]
            }
        """
        from crm_models import Customer
        
        if customer_ids is None:
            # Get all active customers
            customers = self.db.query(Customer).filter(
                Customer.deleted_at.is_(None)
            ).all()
        else:
            customers = self.db.query(Customer).filter(
                Customer.id.in_(customer_ids),
                Customer.deleted_at.is_(None)
            ).all()
        
        processed = 0
        errors = []
        
        for customer in customers:
            try:
                score_data = self.calculator.calculate_propensity_score(customer.id)
                
                # Update customer record
                customer.propensity_score = score_data['propensity_score']
                customer.propensity_updated_at = score_data['calculated_at']
                
                # Optionally update lead_status based on segment
                if customer.is_lead:
                    self._update_lead_status_by_segment(customer, score_data['segment'])
                
                processed += 1
            
            except Exception as e:
                errors.append(f"Customer {customer.id}: {str(e)}")
        
        self.db.commit()
        
        return {
            'status': 'success',
            'processed': processed,
            'errors': errors if errors else None
        }
    
    def _update_lead_status_by_segment(self, customer, segment: str):
        """
        Update lead status based on propensity segment
        
        Logic:
        - very_high/high → 'qualified'
        - medium → 'contacted' (if not already)
        - low/very_low → No change (already classified)
        """
        if segment in ['very_high', 'high']:
            if customer.lead_status != 'customer':
                customer.lead_status = 'qualified'
                if not customer.qualified_at:
                    customer.qualified_at = datetime.utcnow()
        
        elif segment == 'medium':
            if customer.lead_status == 'new':
                customer.lead_status = 'contacted'
                if not customer.contacted_at:
                    customer.contacted_at = datetime.utcnow()
    
    def get_segment_distribution(self) -> Dict:
        """
        Get distribution of customers across propensity segments
        
        Returns:
        {
            very_high: { count, percentage },
            high: { count, percentage },
            medium: { count, percentage },
            low: { count, percentage },
            very_low: { count, percentage },
            total: int
        }
        """
        from crm_models import Customer
        
        total = self.db.query(Customer).filter(
            Customer.deleted_at.is_(None)
        ).count()
        
        if total == 0:
            return {'total': 0}
        
        distribution = {}
        for segment in PropensitySegment:
            # Simplified: count based on propensity_score ranges
            if segment == PropensitySegment.VERY_HIGH:
                min_score, max_score = 0.8, 1.0
            elif segment == PropensitySegment.HIGH:
                min_score, max_score = 0.6, 0.8
            elif segment == PropensitySegment.MEDIUM:
                min_score, max_score = 0.4, 0.6
            elif segment == PropensitySegment.LOW:
                min_score, max_score = 0.2, 0.4
            else:  # VERY_LOW
                min_score, max_score = 0.0, 0.2
            
            count = self.db.query(Customer).filter(
                Customer.propensity_score >= min_score,
                Customer.propensity_score < max_score,
                Customer.deleted_at.is_(None)
            ).count()
            
            distribution[segment.value] = {
                'count': count,
                'percentage': round(count / total * 100, 2) if total > 0 else 0
            }
        
        distribution['total'] = total
        return distribution
    
    def get_high_propensity_leads(self, limit: int = 100) -> List[Dict]:
        """
        Get high propensity leads for outreach
        
        Returns:
        List of {
            customer_id,
            email,
            phone,
            propensity_score,
            segment,
            lead_status,
            recommendation: str (e.g., "Contact now")
        }
        """
        from crm_models import Customer
        
        customers = self.db.query(Customer).filter(
            Customer.is_lead == True,
            Customer.propensity_score >= 0.6,
            Customer.deleted_at.is_(None)
        ).order_by(
            Customer.propensity_score.desc()
        ).limit(limit).all()
        
        results = []
        calc = PropensityCalculator(self.db)
        
        for customer in customers:
            segment = calc._get_segment(customer.propensity_score)
            
            # Generate recommendation
            if segment == PropensitySegment.VERY_HIGH.value:
                recommendation = "Contact immediately - High likelihood to convert"
            elif segment == PropensitySegment.HIGH.value:
                recommendation = "Schedule follow-up - Good prospect"
            else:
                recommendation = "Nurture campaign recommended"
            
            results.append({
                'customer_id': customer.id,
                'email': customer.email,
                'phone': customer.phone,
                'name': customer.first_name or customer.last_name or 'N/A',
                'propensity_score': round(customer.propensity_score, 4),
                'segment': segment,
                'lead_status': customer.lead_status,
                'lead_source': customer.lead_source,
                'recommendation': recommendation
            })
        
        return results


# Example usage and testing
if __name__ == '__main__':
    # This would be run with actual database session
    print("Propensity scoring module loaded")
    
    # Example calculation (pseudocode):
    # calculator = PropensityCalculator(db_session)
    # score = calculator.calculate_propensity_score("customer_123")
    # print(f"Propensity Score: {score['propensity_score']}")
    # print(f"Segment: {score['segment']}")
    # print(f"Breakdown: {score['breakdown']}")
