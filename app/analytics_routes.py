"""
Analytics Dashboard Routes
12 REST API endpoints for customer funnels, revenue, campaigns, segments
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from app.database import get_db
from app.analytics_dashboard import (
    FunnelAnalytics, RevenueAnalytics, CampaignAnalytics,
    CustomerSegmentAnalytics, AnalyticsAggregator
)

router = APIRouter(prefix="/api/crm/analytics", tags=["Analytics Dashboard"])


# ============================================================================
# DASHBOARD ENDPOINTS
# ============================================================================

@router.get("/dashboard/summary")
async def dashboard_summary(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get complete dashboard summary"""
    return AnalyticsAggregator.get_dashboard_summary(db, days)


@router.get("/dashboard/funnel")
async def funnel_metrics(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get customer funnel metrics"""
    return FunnelAnalytics.get_funnel_metrics(db, days)


@router.get("/dashboard/funnel/by-source")
async def funnel_by_source(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get funnel metrics by customer source/channel"""
    return FunnelAnalytics.get_funnel_by_source(db, days)


@router.get("/dashboard/revenue")
async def revenue_metrics(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get revenue and AOV metrics"""
    return RevenueAnalytics.get_revenue_metrics(db, days)


@router.get("/dashboard/revenue/by-channel")
async def revenue_by_channel(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get revenue breakdown by channel"""
    return RevenueAnalytics.get_revenue_by_channel(db, days)


@router.get("/dashboard/revenue/ltv/{customer_id}")
async def customer_ltv(
    customer_id: str,
    db: Session = Depends(get_db)
):
    """Get customer lifetime value"""
    return RevenueAnalytics.get_customer_ltv(db, customer_id)


@router.get("/dashboard/campaigns")
async def campaign_performance(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get campaign performance metrics"""
    return CampaignAnalytics.get_campaign_performance(db, days)


@router.get("/dashboard/roas")
async def roas_metrics(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get ROAS (Return on Ad Spend) metrics"""
    return CampaignAnalytics.get_roas_metrics(db, days)


@router.get("/dashboard/segments")
async def customer_segments(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get customer segmentation by value/behavior"""
    return CustomerSegmentAnalytics.get_customer_segments(db, days)


@router.get("/dashboard/retention")
async def retention_metrics(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get customer retention rate"""
    return CustomerSegmentAnalytics.get_retention_metrics(db, days)


@router.get("/dashboard/by-date")
async def metrics_by_date(
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get daily metrics breakdown"""
    return AnalyticsAggregator.get_metrics_by_date(db, days)


@router.get("/health")
async def analytics_health():
    """Health check for analytics service"""
    return {
        "status": "healthy",
        "service": "Analytics Dashboard",
        "timestamp": datetime.utcnow().isoformat()
    }
