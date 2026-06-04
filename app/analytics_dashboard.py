"""
Analytics Dashboard Integration
Customer funnels, revenue attribution, campaign performance
"""

import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy import func, and_, or_
from sqlalchemy.orm import Session
from app.crm_models import (
    Customer, OfflineConversion, CartAbandonment, 
    DelhiveryOrder, GoogleFormSubmission, MetaConversion
)


class FunnelAnalytics:
    """Customer funnel analysis"""
    
    @staticmethod
    def get_funnel_metrics(
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get customer funnel: Leads → Conversions → Repeat Purchases
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Stage 1: Total customers/leads created
        total_leads = db.query(func.count(Customer.id)).filter(
            Customer.created_at >= start_date,
            Customer.deleted_at.is_(None)
        ).scalar() or 0
        
        # Stage 2: Engaged customers (with cart/order)
        engaged = db.query(func.count(func.distinct(CartAbandonment.customer_id))).filter(
            CartAbandonment.created_at >= start_date
        ).scalar() or 0
        
        # Stage 3: Converted (paid)
        converted = db.query(func.count(func.distinct(OfflineConversion.customer_id))).filter(
            OfflineConversion.created_at >= start_date,
            OfflineConversion.event_name == "Purchase"
        ).scalar() or 0
        
        # Stage 4: Repeat customers
        repeat = db.query(func.count(func.distinct(Customer.id))).filter(
            Customer.created_at >= start_date,
            Customer.has_purchased == True,
            Customer.deleted_at.is_(None)
        ).scalar() or 0
        
        return {
            "period_days": days,
            "stages": [
                {"stage": "Leads/Customers", "count": total_leads, "conversion": 1.0},
                {"stage": "Engaged", "count": engaged, "conversion": engaged / total_leads if total_leads > 0 else 0},
                {"stage": "Converted (Paid)", "count": converted, "conversion": converted / total_leads if total_leads > 0 else 0},
                {"stage": "Repeat Customers", "count": repeat, "conversion": repeat / total_leads if total_leads > 0 else 0}
            ],
            "overall_conversion_rate": converted / total_leads if total_leads > 0 else 0
        }
    
    @staticmethod
    def get_funnel_by_source(
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get funnel metrics broken down by customer source"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        sources = db.query(
            Customer.source,
            func.count(Customer.id).label('total'),
            func.count(func.distinct(
                OfflineConversion.id
            )).label('conversions')
        ).outerjoin(
            OfflineConversion,
            and_(
                OfflineConversion.customer_id == Customer.id,
                OfflineConversion.created_at >= start_date
            )
        ).filter(
            Customer.created_at >= start_date,
            Customer.deleted_at.is_(None)
        ).group_by(Customer.source).all()
        
        return {
            "period_days": days,
            "by_source": [
                {
                    "source": s.source or "unknown",
                    "total_customers": s.total,
                    "conversions": s.conversions,
                    "conversion_rate": s.conversions / s.total if s.total > 0 else 0
                }
                for s in sources
            ]
        }


class RevenueAnalytics:
    """Revenue and attribution analytics"""
    
    @staticmethod
    def get_revenue_metrics(
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get total revenue, AOV, repeat purchase value"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Total revenue
        total_revenue = db.query(func.sum(OfflineConversion.value)).filter(
            OfflineConversion.created_at >= start_date,
            OfflineConversion.event_name == "Purchase"
        ).scalar() or 0
        
        # Purchase count
        purchase_count = db.query(func.count(OfflineConversion.id)).filter(
            OfflineConversion.created_at >= start_date,
            OfflineConversion.event_name == "Purchase"
        ).scalar() or 0
        
        # Unique customers who purchased
        unique_customers = db.query(func.count(func.distinct(OfflineConversion.customer_id))).filter(
            OfflineConversion.created_at >= start_date,
            OfflineConversion.event_name == "Purchase"
        ).scalar() or 0
        
        return {
            "period_days": days,
            "total_revenue": float(total_revenue),
            "purchase_count": purchase_count,
            "unique_customers": unique_customers,
            "aov": float(total_revenue / purchase_count) if purchase_count > 0 else 0,
            "revenue_per_customer": float(total_revenue / unique_customers) if unique_customers > 0 else 0
        }
    
    @staticmethod
    def get_revenue_by_channel(
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get revenue breakdown by acquisition channel/source"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        channels = db.query(
            Customer.source,
            func.sum(OfflineConversion.value).label('revenue'),
            func.count(OfflineConversion.id).label('purchases')
        ).join(
            OfflineConversion,
            Customer.id == OfflineConversion.customer_id
        ).filter(
            OfflineConversion.created_at >= start_date,
            OfflineConversion.event_name == "Purchase",
            Customer.deleted_at.is_(None)
        ).group_by(Customer.source).all()
        
        return {
            "period_days": days,
            "by_channel": [
                {
                    "channel": c.source or "unknown",
                    "revenue": float(c.revenue),
                    "purchases": c.purchases,
                    "avg_order_value": float(c.revenue / c.purchases) if c.purchases > 0 else 0
                }
                for c in channels
            ]
        }
    
    @staticmethod
    def get_customer_ltv(
        db: Session,
        customer_id: str
    ) -> Dict[str, Any]:
        """Calculate customer lifetime value"""
        conversions = db.query(OfflineConversion).filter(
            OfflineConversion.customer_id == customer_id
        ).all()
        
        total_value = sum(c.value or 0 for c in conversions)
        purchase_count = len([c for c in conversions if c.event_name == "Purchase"])
        
        return {
            "customer_id": customer_id,
            "lifetime_value": float(total_value),
            "purchase_count": purchase_count,
            "average_order_value": float(total_value / purchase_count) if purchase_count > 0 else 0,
            "last_purchase": max([c.created_at for c in conversions]).isoformat() if conversions else None
        }


class CampaignAnalytics:
    """Campaign performance analytics"""
    
    @staticmethod
    def get_campaign_performance(
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get performance for all active campaigns"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Meta Ads performance
        meta_conversions = db.query(
            MetaConversion.event_name,
            func.count(MetaConversion.id).label('count'),
            func.sum(MetaConversion.value).label('total_value')
        ).filter(
            MetaConversion.created_at >= start_date,
            MetaConversion.synced_to_meta == True
        ).group_by(MetaConversion.event_name).all()
        
        # Form submissions (leads from Google Forms)
        form_leads = db.query(func.count(GoogleFormSubmission.id)).filter(
            GoogleFormSubmission.created_at >= start_date,
            GoogleFormSubmission.status == "lead_created"
        ).scalar() or 0
        
        # Orders from Delhivery
        orders = db.query(func.count(DelhiveryOrder.id)).filter(
            DelhiveryOrder.created_at >= start_date
        ).scalar() or 0
        
        return {
            "period_days": days,
            "meta_conversions": [
                {
                    "event": c.event_name,
                    "count": c.count,
                    "total_value": float(c.total_value) if c.total_value else 0
                }
                for c in meta_conversions
            ],
            "form_leads": form_leads,
            "orders_tracked": orders
        }
    
    @staticmethod
    def get_roas_metrics(
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Calculate ROAS (Return on Ad Spend)
        This requires ad spend data from Meta/Google Ads
        """
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Revenue from Meta conversions
        meta_revenue = db.query(func.sum(MetaConversion.value)).filter(
            MetaConversion.created_at >= start_date,
            MetaConversion.event_name == "Purchase",
            MetaConversion.synced_to_meta == True
        ).scalar() or 0
        
        # This would need actual ad spend data from Meta/Google Ads APIs
        estimated_ad_spend = 10000  # Placeholder
        
        return {
            "period_days": days,
            "estimated_revenue": float(meta_revenue),
            "estimated_ad_spend": float(estimated_ad_spend),
            "estimated_roas": float(meta_revenue / estimated_ad_spend) if estimated_ad_spend > 0 else 0
        }


class CustomerSegmentAnalytics:
    """Customer segmentation and cohort analysis"""
    
    @staticmethod
    def get_customer_segments(
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get customer segments by behavior and value"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # High-value customers
        high_value = db.query(func.count(func.distinct(Customer.id))).filter(
            Customer.created_at >= start_date,
            Customer.propensity_score >= 0.8,
            Customer.deleted_at.is_(None)
        ).scalar() or 0
        
        # Medium-value
        medium_value = db.query(func.count(func.distinct(Customer.id))).filter(
            Customer.created_at >= start_date,
            Customer.propensity_score.between(0.5, 0.79),
            Customer.deleted_at.is_(None)
        ).scalar() or 0
        
        # Low-value / At-risk
        low_value = db.query(func.count(func.distinct(Customer.id))).filter(
            Customer.created_at >= start_date,
            Customer.propensity_score < 0.5,
            Customer.deleted_at.is_(None)
        ).scalar() or 0
        
        # Engaged (recent cart activity)
        engaged = db.query(func.count(func.distinct(CartAbandonment.customer_id))).filter(
            CartAbandonment.created_at >= start_date
        ).scalar() or 0
        
        total = high_value + medium_value + low_value
        
        return {
            "period_days": days,
            "segments": [
                {
                    "segment": "High-Value",
                    "count": high_value,
                    "percentage": (high_value / total * 100) if total > 0 else 0
                },
                {
                    "segment": "Medium-Value",
                    "count": medium_value,
                    "percentage": (medium_value / total * 100) if total > 0 else 0
                },
                {
                    "segment": "Low-Value/At-Risk",
                    "count": low_value,
                    "percentage": (low_value / total * 100) if total > 0 else 0
                },
                {
                    "segment": "Engaged (Recent)",
                    "count": engaged,
                    "percentage": (engaged / total * 100) if total > 0 else 0
                }
            ],
            "total_customers": total
        }
    
    @staticmethod
    def get_retention_metrics(
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Calculate customer retention rate"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        period_start = start_date - timedelta(days=days)
        
        # Customers from previous period
        previous_customers = db.query(func.count(func.distinct(Customer.id))).filter(
            Customer.created_at >= period_start,
            Customer.created_at < start_date,
            Customer.deleted_at.is_(None)
        ).scalar() or 0
        
        # Customers still active in current period
        retained = db.query(func.count(func.distinct(Customer.id))).filter(
            Customer.created_at >= period_start,
            Customer.created_at < start_date,
            Customer.updated_at >= start_date,
            Customer.deleted_at.is_(None)
        ).scalar() or 0
        
        return {
            "period_days": days,
            "previous_period_customers": previous_customers,
            "retained_customers": retained,
            "retention_rate": (retained / previous_customers * 100) if previous_customers > 0 else 0
        }


class AnalyticsAggregator:
    """Aggregates all analytics for dashboard"""
    
    @staticmethod
    def get_dashboard_summary(
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get complete dashboard summary"""
        return {
            "period_days": days,
            "timestamp": datetime.utcnow().isoformat(),
            "funnel": FunnelAnalytics.get_funnel_metrics(db, days),
            "revenue": RevenueAnalytics.get_revenue_metrics(db, days),
            "campaigns": CampaignAnalytics.get_campaign_performance(db, days),
            "segments": CustomerSegmentAnalytics.get_customer_segments(db, days),
            "retention": CustomerSegmentAnalytics.get_retention_metrics(db, days)
        }
    
    @staticmethod
    def get_metrics_by_date(
        db: Session,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get daily metrics breakdown"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        daily_metrics = {}
        
        for i in range(days):
            current_date = start_date + timedelta(days=i)
            day_key = current_date.date().isoformat()
            
            # Leads created
            leads = db.query(func.count(Customer.id)).filter(
                Customer.created_at.cast(__import__('sqlalchemy.types', fromlist=['Date']).Date) == current_date.date()
            ).scalar() or 0
            
            # Conversions
            conversions = db.query(func.count(OfflineConversion.id)).filter(
                OfflineConversion.created_at.cast(__import__('sqlalchemy.types', fromlist=['Date']).Date) == current_date.date(),
                OfflineConversion.event_name == "Purchase"
            ).scalar() or 0
            
            # Revenue
            revenue = db.query(func.sum(OfflineConversion.value)).filter(
                OfflineConversion.created_at.cast(__import__('sqlalchemy.types', fromlist=['Date']).Date) == current_date.date(),
                OfflineConversion.event_name == "Purchase"
            ).scalar() or 0
            
            daily_metrics[day_key] = {
                "leads": leads,
                "conversions": conversions,
                "revenue": float(revenue)
            }
        
        return {
            "period_days": days,
            "daily_metrics": daily_metrics
        }
