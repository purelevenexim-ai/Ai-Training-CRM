"""
Review Incentive Optimizer — PureLeven

Determines the minimum effective review incentive per customer segment:
  - Loyal customers (3+ purchases): ₹50-100 (they love us already)
  - High-engagement new customers: ₹100 (warm, just need a nudge)
  - Low-engagement customers: ₹150-200 (bigger push needed)

Integrates with:
  - email_templates.py day15 (review request email)
  - whatsapp_templates.py review incentive template

Guardrails:
  - Max coupon hardcoded at ₹200 (configurable per customer)
  - Only allows amounts from: 50, 100, 150, 200
  - Falls back to ₹100 if AI unavailable
"""

from __future__ import annotations

import logging
from typing import Any

from app.services.ai_enhancement_service import AIEnhancementService

logger = logging.getLogger(__name__)

# ── Hardcoded coupon upper limit ──────────────────────────────────────────────
MAX_COUPON_INR = 200


class ReviewIncentiveOptimizer:
    """
    Determines optimal review incentive for each customer.

    Always returns a safe result — never raises.
    """

    @staticmethod
    def get_incentive(
        customer_id: str,
        customer_segment: str = "new",
        engagement_score: float = 0.0,
        purchase_count: int = 1,
        review_status: str = "not_submitted",
        max_coupon_inr: int = MAX_COUPON_INR,
    ) -> dict[str, Any]:
        """
        Get AI-optimised review incentive for this customer.

        Returns:
          {
            coupon_inr: int,
            urgency: str,       # low | medium | high
            tone: str,          # nurturing | friendly | urgent | premium
            message_hook: str,  # Sentence to append to review request
            coupon_code: str,   # e.g. "REVIEW100"
            source: str,        # ai | cache | fallback
          }
        """
        result = AIEnhancementService.optimize_review_incentive(
            customer_id=customer_id,
            customer_segment=customer_segment,
            engagement_score=engagement_score,
            purchase_count=purchase_count,
            review_status=review_status,
            max_coupon_inr=max_coupon_inr,
        )

        # Generate coupon code from amount
        coupon_inr = result.get("coupon_inr", 100)
        result["coupon_code"] = f"REVIEW{coupon_inr}"

        return result

    @staticmethod
    def format_for_email(
        incentive: dict[str, Any],
        brand_color: str = "#2E7D32",
    ) -> str:
        """
        Render review incentive as HTML block for email templates.
        """
        coupon_code = incentive.get("coupon_code", "REVIEW100")
        coupon_inr = incentive.get("coupon_inr", 100)
        message_hook = incentive.get("message_hook", "")
        urgency = incentive.get("urgency", "medium")

        urgency_styles = {
            "high":   ("background:#FFF3E0;border-left:4px solid #F57C00;", "#E65100"),
            "medium": (f"background:#E8F5E9;border-left:4px solid {brand_color};", brand_color),
            "low":    ("background:#F3F4F6;border-left:4px solid #9CA3AF;", "#374151"),
        }
        block_style, text_color = urgency_styles.get(urgency, urgency_styles["medium"])

        hook_html = f'<p style="margin:8px 0 0;font-size:14px;font-style:italic;color:#6B7280;">{message_hook}</p>' if message_hook else ""

        return f"""
<div style="{block_style}padding:16px;border-radius:0 8px 8px 0;margin:16px 0;">
  <p style="margin:0 0 6px;font-weight:bold;font-size:16px;color:{text_color};">
    🎁 Earn ₹{coupon_inr} off your next order!
  </p>
  <p style="margin:0;font-size:14px;color:#374151;">
    Share your honest review and get coupon code
    <strong style="background:#fff;padding:2px 8px;border-radius:4px;border:1px solid #E5E7EB;font-family:monospace;">{coupon_code}</strong>
    for ₹{coupon_inr} off.
  </p>
  {hook_html}
</div>"""
