"""
AI Enhancement Service — PureLeven

Central wrapper for all AI-powered features:
  1. Email subject line generation (A/B variants)
  2. Smart product recommendations
  3. Customer psychology profiling
  4. Review incentive optimization
  5. Abandoned lead context generation

Features:
  - In-memory caching (24h subjects, 7d products)
  - All AI decisions logged to ai_decisions DB table
  - Fallback to rule-based defaults on any AI failure
  - No PII sent to OpenRouter (customer_id only)
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from app.ai.openrouter_client import ai_client
from app.storage import get_db_connection

logger = logging.getLogger(__name__)

# ── In-memory cache ───────────────────────────────────────────────────────────
# {cache_key: (value, expires_at_timestamp)}
_cache: dict[str, tuple[Any, float]] = {}

CACHE_TTL_SUBJECTS    = 86400        # 24 hours — subject lines
CACHE_TTL_PRODUCTS    = 604800       # 7 days   — product recommendations
CACHE_TTL_PSYCHOLOGY  = 172800       # 48 hours — psychology profile
CACHE_TTL_INCENTIVE   = 86400        # 24 hours — review incentives


def _cache_get(key: str) -> Any | None:
    entry = _cache.get(key)
    if entry and time.time() < entry[1]:
        return entry[0]
    _cache.pop(key, None)
    return None


def _cache_set(key: str, value: Any, ttl: int) -> None:
    _cache[key] = (value, time.time() + ttl)


def _log_decision(
    decision_type: str,
    customer_id: str,
    output: dict[str, Any],
    source: str = "ai",
) -> str:
    """Log AI decision to database for tracking + learning. Returns decision_id."""
    decision_id = f"ai-{decision_type[:4]}-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()
    try:
        with get_db_connection() as conn:
            conn.execute(
                """
                INSERT INTO ai_decisions
                  (id, decision_type, customer_id, ai_output_json, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    decision_type,
                    str(customer_id),
                    json.dumps(output, ensure_ascii=False),
                    source,
                    now,
                ),
            )
    except Exception as exc:
        logger.warning("Failed to log AI decision: %s", exc)
    return decision_id


# ── Public API ────────────────────────────────────────────────────────────────

class AIEnhancementService:
    """
    High-level AI service used by email templates, campaign services,
    and orchestrators.

    All methods:
      - Return a result dict (never raise)
      - Check cache first
      - Log to ai_decisions table
      - Include 'source': 'ai' | 'cache' | 'fallback'
    """

    # ── 1. Email Subject Line Generation ─────────────────────────────────────

    @staticmethod
    def generate_email_subjects(
        customer_id: str,
        stage: str,
        customer_segment: str,
        product_name: str,
        psychology_type: str = "explorer",
    ) -> dict[str, Any]:
        """
        Generate 3 AI subject line variants for an email stage.

        Returns:
          {variants: [...], best: str, best_index: int, reason: str, decision_id: str, source: str}
        """
        cache_key = f"subj:{customer_id}:{stage}"
        cached = _cache_get(cache_key)
        if cached:
            cached["source"] = "cache"
            return cached

        result = ai_client.generate_email_subjects(
            stage=stage,
            customer_segment=customer_segment,
            product_name=product_name,
            psychology_type=psychology_type,
        )

        decision_id = _log_decision("subject", customer_id, result, result.get("source", "ai"))
        result["decision_id"] = decision_id

        if result.get("source") != "fallback":
            _cache_set(cache_key, result, CACHE_TTL_SUBJECTS)

        return result

    # ── 2. Product Recommendations ────────────────────────────────────────────

    @staticmethod
    def get_product_recommendations(
        customer_id: str,
        purchased_product: str,
        customer_segment: str,
        purchase_count: int,
    ) -> dict[str, Any]:
        """
        Get top 3 product recommendations with AI reasoning.

        Returns:
          {recommendations: [{category, product_name, reason}, ...], decision_id: str, source: str}
        """
        cache_key = f"rec:{customer_id}:{purchased_product[:20]}"
        cached = _cache_get(cache_key)
        if cached:
            cached["source"] = "cache"
            return cached

        result = ai_client.recommend_products(
            purchased_product=purchased_product,
            customer_segment=customer_segment,
            purchase_count=purchase_count,
        )

        decision_id = _log_decision("product_rec", customer_id, result, result.get("source", "ai"))
        result["decision_id"] = decision_id

        if result.get("source") != "fallback":
            _cache_set(cache_key, result, CACHE_TTL_PRODUCTS)

        return result

    # ── 3. Customer Psychology Profiling ──────────────────────────────────────

    @staticmethod
    def get_psychology_profile(
        customer_id: str,
        engagement_score: float = 0,
        purchase_count: int = 0,
        days_since_last_action: int = 30,
        review_submitted: bool = False,
        total_spent_paise: int = 0,
        opened_emails: int = 0,
        clicked_emails: int = 0,
    ) -> dict[str, Any]:
        """
        Get AI psychology profile for a customer.

        Returns:
          {psychograph, tone, content_preference, urgency, confidence, reason, decision_id, source}
        """
        cache_key = f"psych:{customer_id}"
        cached = _cache_get(cache_key)
        if cached:
            cached["source"] = "cache"
            return cached

        result = ai_client.profile_psychology(
            engagement_score=engagement_score,
            purchase_count=purchase_count,
            days_since_last_action=days_since_last_action,
            review_submitted=review_submitted,
            total_spent_paise=total_spent_paise,
            opened_emails=opened_emails,
            clicked_emails=clicked_emails,
        )

        decision_id = _log_decision("psychology", customer_id, result, result.get("source", "ai"))
        result["decision_id"] = decision_id

        if result.get("source") != "fallback":
            _cache_set(cache_key, result, CACHE_TTL_PSYCHOLOGY)

        # Persist psychograph to journey_customers if available
        try:
            with get_db_connection() as conn:
                conn.execute(
                    """
                    UPDATE journey_customers
                    SET psychograph_ai_json = ?, psychograph_updated_at = ?
                    WHERE id = ?
                    """,
                    (json.dumps(result), datetime.now(timezone.utc).isoformat(), customer_id),
                )
        except Exception:
            pass  # Column may not exist yet — silently skip

        return result

    # ── 4. Review Incentive Optimization ─────────────────────────────────────

    @staticmethod
    def optimize_review_incentive(
        customer_id: str,
        customer_segment: str,
        engagement_score: float,
        purchase_count: int,
        review_status: str = "not_submitted",
        max_coupon_inr: int = 200,
    ) -> dict[str, Any]:
        """
        Decide optimal review incentive for this customer.

        Returns:
          {coupon_inr, urgency, tone, message_hook, decision_id, source}
        """
        cache_key = f"incentive:{customer_id}"
        cached = _cache_get(cache_key)
        if cached:
            cached["source"] = "cache"
            return cached

        result = ai_client.optimize_review_incentive(
            customer_segment=customer_segment,
            engagement_score=engagement_score,
            purchase_count=purchase_count,
            review_status=review_status,
            max_coupon_inr=max_coupon_inr,
        )

        decision_id = _log_decision("incentive", customer_id, result, result.get("source", "ai"))
        result["decision_id"] = decision_id

        if result.get("source") != "fallback":
            _cache_set(cache_key, result, CACHE_TTL_INCENTIVE)

        return result

    # ── 5. Abandoned Lead Context ─────────────────────────────────────────────

    @staticmethod
    def generate_abandoned_context(
        lead_id: str,
        interest_product: str,
        interest_category: str,
        days_abandoned: int,
        engagement_score: float,
        campaign_number: int,
    ) -> str:
        """
        Generate a 1-sentence personalization context for abandoned email.

        Returns: Plain string (empty string if AI fails — templates handle gracefully).
        """
        cache_key = f"abctx:{lead_id}:{campaign_number}"
        cached = _cache_get(cache_key)
        if isinstance(cached, str):
            return cached

        context = ai_client.generate_abandoned_context(
            interest_product=interest_product,
            interest_category=interest_category,
            days_abandoned=days_abandoned,
            engagement_score=engagement_score,
            campaign_number=campaign_number,
        )

        if context:
            _log_decision("abandoned_context", lead_id, {"context": context}, "ai")
            _cache_set(cache_key, context, CACHE_TTL_SUBJECTS)
        else:
            _log_decision("abandoned_context", lead_id, {"context": ""}, "fallback")

        return context

    # ── Utility: Invalidate cache for a customer ──────────────────────────────

    @staticmethod
    def invalidate_cache(customer_id: str) -> None:
        """Remove all cached AI decisions for a customer (call on profile update)."""
        prefix = str(customer_id)
        keys_to_remove = [k for k in _cache if prefix in k]
        for k in keys_to_remove:
            _cache.pop(k, None)
        logger.debug("Invalidated %d AI cache entries for %s", len(keys_to_remove), customer_id)

    # ── Utility: Cache stats ──────────────────────────────────────────────────

    @staticmethod
    def cache_stats() -> dict[str, Any]:
        """Return current cache statistics."""
        now = time.time()
        active = sum(1 for _, (_, exp) in _cache.items() if now < exp)
        expired = len(_cache) - active
        return {"total": len(_cache), "active": active, "expired": expired}
