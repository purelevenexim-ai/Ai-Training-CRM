"""
AI Routes — PureLeven

API endpoints for all AI features:
  POST /api/ai/generate-subject-variants  — Test email subject generation
  POST /api/ai/get-recommendations        — Test product recommendations
  POST /api/ai/get-psychology             — Customer psychology profile
  POST /api/ai/abandoned-context          — Abandoned lead personalization
  POST /api/ai/review-incentive           — Review incentive optimization
  GET  /api/ai/performance-dashboard      — AI vs. template performance metrics
  GET  /api/ai/cost-summary               — OpenRouter API usage & cost
  GET  /api/ai/cache-stats                — In-memory cache statistics
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import settings
from app.storage import get_db_connection
from app.services.ai_enhancement_service import AIEnhancementService
from app.services.product_recommendation_engine import ProductRecommendationEngine
from app.services.review_incentive_optimizer import ReviewIncentiveOptimizer
from app.services.customer_intelligence_service import list_ai_decisions

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Auth dependency ────────────────────────────────────────────────────────────

def _require_admin(admin_secret: str = Query(..., alias="admin_secret")) -> None:
    if admin_secret != settings.admin_secret:
        raise HTTPException(status_code=403, detail="Invalid admin_secret")


# ── Request models ─────────────────────────────────────────────────────────────

class SubjectVariantRequest(BaseModel):
    customer_id: str = "test-customer"
    stage: str = "day30"
    customer_segment: str = "new"
    product_name: str = "Organic Turmeric"
    psychology_type: str = "explorer"


class ProductRecommendationRequest(BaseModel):
    customer_id: str = "test-customer"
    purchased_product: str = "Organic Turmeric"
    customer_segment: str = "new"
    purchase_count: int = 1
    utm_campaign: str = "email_rec"


class PsychologyRequest(BaseModel):
    customer_id: str
    engagement_score: float = 0.0
    purchase_count: int = 1
    days_since_last_action: int = 30
    review_submitted: bool = False
    total_spent_paise: int = 0
    opened_emails: int = 0
    clicked_emails: int = 0


class AbandonedContextRequest(BaseModel):
    lead_id: str
    interest_product: str = "Organic Turmeric"
    interest_category: str = "turmeric"
    days_abandoned: int = 0
    engagement_score: float = 0.0
    campaign_number: int = 1


class ReviewIncentiveRequest(BaseModel):
    customer_id: str
    customer_segment: str = "new"
    engagement_score: float = 0.0
    purchase_count: int = 1
    review_status: str = "not_submitted"
    max_coupon_inr: int = 200


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/ai/generate-subject-variants")
async def generate_subject_variants(
    req: SubjectVariantRequest,
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Generate 3 AI email subject line variants for testing."""
    result = AIEnhancementService.generate_email_subjects(
        customer_id=req.customer_id,
        stage=req.stage,
        customer_segment=req.customer_segment,
        product_name=req.product_name,
        psychology_type=req.psychology_type,
    )
    return JSONResponse({
        "ok": True,
        "variants": result.get("variants", []),
        "best": result.get("best", ""),
        "best_index": result.get("best_index", 0),
        "reason": result.get("reason", ""),
        "decision_id": result.get("decision_id", ""),
        "source": result.get("source", ""),
    })


@router.post("/ai/get-recommendations")
async def get_product_recommendations(
    req: ProductRecommendationRequest,
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Get top 3 AI product recommendations with verified URLs."""
    recs = ProductRecommendationEngine.get_recommendations(
        customer_id=req.customer_id,
        purchased_product=req.purchased_product,
        customer_segment=req.customer_segment,
        purchase_count=req.purchase_count,
        utm_campaign=req.utm_campaign,
        count=3,
    )
    return JSONResponse({
        "ok": True,
        "customer_id": req.customer_id,
        "purchased_product": req.purchased_product,
        "recommendations": recs,
        "count": len(recs),
    })


@router.post("/ai/get-psychology")
async def get_psychology_profile(
    req: PsychologyRequest,
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Get AI psychology profile for a customer."""
    # Try to look up real customer data if customer_id is in DB
    extra = {}
    try:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT * FROM journey_customers WHERE id = ?",
                (req.customer_id,)
            ).fetchone()
            if row:
                r = dict(row)
                extra = {
                    "customer_name": r.get("customer_name"),
                    "customer_segment": r.get("customer_segment"),
                    "existing_psychograph": r.get("psychograph_ai_json"),
                }
    except Exception:
        pass

    result = AIEnhancementService.get_psychology_profile(
        customer_id=req.customer_id,
        engagement_score=req.engagement_score,
        purchase_count=req.purchase_count,
        days_since_last_action=req.days_since_last_action,
        review_submitted=req.review_submitted,
        total_spent_paise=req.total_spent_paise,
        opened_emails=req.opened_emails,
        clicked_emails=req.clicked_emails,
    )
    return JSONResponse({
        "ok": True,
        "customer_id": req.customer_id,
        "profile": result,
        **extra,
    })


@router.post("/ai/abandoned-context")
async def generate_abandoned_context(
    req: AbandonedContextRequest,
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Generate AI personalization context for an abandoned lead email."""
    context = AIEnhancementService.generate_abandoned_context(
        lead_id=req.lead_id,
        interest_product=req.interest_product,
        interest_category=req.interest_category,
        days_abandoned=req.days_abandoned,
        engagement_score=req.engagement_score,
        campaign_number=req.campaign_number,
    )
    return JSONResponse({
        "ok": True,
        "lead_id": req.lead_id,
        "ai_context": context,
        "has_context": bool(context),
    })


@router.post("/ai/review-incentive")
async def optimize_review_incentive(
    req: ReviewIncentiveRequest,
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Get AI-optimized review incentive for a customer."""
    incentive = ReviewIncentiveOptimizer.get_incentive(
        customer_id=req.customer_id,
        customer_segment=req.customer_segment,
        engagement_score=req.engagement_score,
        purchase_count=req.purchase_count,
        review_status=req.review_status,
        max_coupon_inr=req.max_coupon_inr,
    )
    incentive_html = ReviewIncentiveOptimizer.format_for_email(incentive)
    return JSONResponse({
        "ok": True,
        "customer_id": req.customer_id,
        "incentive": incentive,
        "html_preview": incentive_html[:500],
    })


@router.get("/ai/performance-dashboard")
async def ai_performance_dashboard(
    _: None = Depends(_require_admin),
    days: int = Query(default=7, ge=1, le=90),
) -> JSONResponse:
    """
    AI vs. template performance metrics.
    Returns comparison of AI-generated vs. static content performance.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    stats: dict[str, Any] = {
        "period_days": days,
        "since": since,
        "ai_decisions": {},
        "email_performance": {},
        "abandoned_performance": {},
        "cache_stats": AIEnhancementService.cache_stats(),
    }

    try:
        with get_db_connection() as conn:
            # AI decisions breakdown
            decisions = conn.execute(
                """
                SELECT decision_type, source, COUNT(*) as count
                FROM ai_decisions
                WHERE created_at >= ?
                GROUP BY decision_type, source
                ORDER BY decision_type, source
                """,
                (since,),
            ).fetchall()

            for row in decisions:
                dt = row["decision_type"]
                src = row["source"]
                if dt not in stats["ai_decisions"]:
                    stats["ai_decisions"][dt] = {}
                stats["ai_decisions"][dt][src] = row["count"]

            # Email performance by variant type
            try:
                email_stats = conn.execute(
                    """
                    SELECT
                        subject_line_variant,
                        COUNT(*) as total_sent,
                        SUM(CASE WHEN email_status = 'delivered' THEN 1 ELSE 0 END) as delivered
                    FROM journey_messages
                    WHERE created_at >= ? AND email_status IS NOT NULL
                    GROUP BY subject_line_variant
                    """,
                    (since,),
                ).fetchall()
                for row in email_stats:
                    variant = row["subject_line_variant"] or "template"
                    stats["email_performance"][variant] = {
                        "total_sent": row["total_sent"],
                        "delivered": row["delivered"],
                    }
            except Exception:
                pass

            # Abandoned campaign performance
            try:
                abandoned_stats = conn.execute(
                    """
                    SELECT
                        CASE WHEN ai_context_used IS NOT NULL AND ai_context_used != ''
                             THEN 'ai_personalized' ELSE 'template' END as variant,
                        COUNT(*) as total_sent,
                        SUM(CASE WHEN opened_at IS NOT NULL THEN 1 ELSE 0 END) as opened,
                        SUM(CASE WHEN clicked_at IS NOT NULL THEN 1 ELSE 0 END) as clicked
                    FROM abandoned_campaigns
                    WHERE created_at >= ?
                    GROUP BY variant
                    """,
                    (since,),
                ).fetchall()
                for row in abandoned_stats:
                    variant = row["variant"]
                    total = row["total_sent"] or 1
                    stats["abandoned_performance"][variant] = {
                        "total_sent": row["total_sent"],
                        "opened": row["opened"],
                        "clicked": row["clicked"],
                        "open_rate_pct": round((row["opened"] / total) * 100, 1),
                        "click_rate_pct": round((row["clicked"] / total) * 100, 1),
                    }
            except Exception:
                pass

    except Exception as exc:
        logger.error("AI performance dashboard error: %s", exc)
        stats["error"] = str(exc)

    return JSONResponse({"ok": True, **stats})


@router.get("/ai/cost-summary")
async def ai_cost_summary(
    _: None = Depends(_require_admin),
    days: int = Query(default=30, ge=1, le=90),
) -> JSONResponse:
    """
    OpenRouter API usage and estimated cost summary.
    Estimates based on DeepSeek token pricing.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

    cost_per_1k_tokens = 0.00014  # DeepSeek v3 pricing in USD (~₹0.012)
    avg_tokens_per_call = {
        "subject": 250,
        "product_rec": 400,
        "psychology": 200,
        "incentive": 180,
        "abandoned_context": 100,
    }

    summary: dict[str, Any] = {
        "period_days": days,
        "since": since,
        "by_type": {},
        "totals": {
            "ai_calls": 0,
            "fallback_calls": 0,
            "cached_calls": 0,
            "estimated_tokens": 0,
            "estimated_cost_usd": 0.0,
            "estimated_cost_inr": 0.0,
        },
    }

    try:
        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT decision_type, source, COUNT(*) as count
                FROM ai_decisions
                WHERE created_at >= ?
                GROUP BY decision_type, source
                """,
                (since,),
            ).fetchall()

            for row in rows:
                dt = row["decision_type"]
                src = row["source"]
                cnt = row["count"]

                if dt not in summary["by_type"]:
                    summary["by_type"][dt] = {"ai": 0, "fallback": 0, "cache": 0, "estimated_cost_inr": 0.0}

                summary["by_type"][dt][src if src in ("ai", "fallback", "cache") else "ai"] += cnt

                if src == "ai":
                    tokens = avg_tokens_per_call.get(dt, 200) * cnt
                    cost_usd = (tokens / 1000) * cost_per_1k_tokens
                    cost_inr = cost_usd * 83  # USD → INR
                    summary["by_type"][dt]["estimated_cost_inr"] += round(cost_inr, 2)
                    summary["totals"]["estimated_tokens"] += tokens
                    summary["totals"]["estimated_cost_usd"] += cost_usd
                    summary["totals"]["estimated_cost_inr"] += cost_inr
                    summary["totals"]["ai_calls"] += cnt
                elif src == "fallback":
                    summary["totals"]["fallback_calls"] += cnt
                elif src == "cache":
                    summary["totals"]["cached_calls"] += cnt

    except Exception as exc:
        logger.error("AI cost summary error: %s", exc)
        summary["error"] = str(exc)

    summary["totals"]["estimated_cost_usd"] = round(summary["totals"]["estimated_cost_usd"], 4)
    summary["totals"]["estimated_cost_inr"] = round(summary["totals"]["estimated_cost_inr"], 2)
    summary["totals"]["cache_savings_pct"] = (
        round(
            summary["totals"]["cached_calls"]
            / max(1, summary["totals"]["ai_calls"] + summary["totals"]["cached_calls"])
            * 100,
            1,
        )
    )

    return JSONResponse({"ok": True, **summary})


@router.get('/ai/decisions')
async def ai_decision_log(
    _: None = Depends(_require_admin),
    limit: int = Query(default=100, ge=1, le=500),
    customer_email: str | None = Query(default=None),
) -> JSONResponse:
    items = list_ai_decisions(limit=limit, customer_email=customer_email)
    return JSONResponse({'ok': True, 'items': items, 'count': len(items)})


@router.get("/ai/cache-stats")
async def ai_cache_stats(
    _: None = Depends(_require_admin),
) -> JSONResponse:
    """Return current in-memory AI cache statistics."""
    stats = AIEnhancementService.cache_stats()
    return JSONResponse({"ok": True, **stats})
