"""
Basil Commerce OS — Phase 5
psychology_engine.py

Customer Psychology Classification & Scoring Engine.

Classifies customers into emotional profiles based on behavior, then adapts
messaging tone, urgency, and positioning accordingly.

Types:
  - explorer      : Browsing, researching, low urgency
  - skeptic       : Distrusts, needs proof/social proof
  - price_sensitive : Focused on value for money
  - quality_focused : Doesn't care about price, wants best
  - urgent_buyer  : Ready now, wants immediate checkout

Each gets different message variants for same content.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class PsychologyProfile:
    """Customer emotional/behavioral profile."""
    
    def __init__(
        self,
        psychology_type: str,  # explorer | skeptic | price_sensitive | quality_focused | urgent
        confidence: float,      # 0-100, how confident we are in this classification
        lead_score: float,      # 0-100, likelihood to convert
        trust_score: float,     # 0-100, brand trust level
        engagement_score: float,  # 0-100, how responsive they are
        days_since_action: int,  # Days since last interaction
        total_events: int,      # Total interactions (website, email, messages)
    ):
        self.psychology_type = psychology_type
        self.confidence = confidence
        self.lead_score = lead_score
        self.trust_score = trust_score
        self.engagement_score = engagement_score
        self.days_since_action = days_since_action
        self.total_events = total_events
        self.created_at = datetime.now(timezone.utc).isoformat()

def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.psychology_type,
            "confidence": self.confidence,
            "lead_score": self.lead_score,
            "trust_score": self.trust_score,
            "engagement_score": self.engagement_score,
            "days_since_action": self.days_since_action,
            "total_events": self.total_events,
        }


def profile_with_ai(customer: dict[str, Any]) -> PsychologyProfile | None:
    """
    Use AI to profile customer psychology (OpenRouter DeepSeek model).
    
    Returns PsychologyProfile if successful, None if AI unavailable.
    Uses rule-based classification as fallback.
    """
    try:
        from app.services.ai_enhancement_service import AIEnhancementService
        
        customer_id = str(customer.get("id") or customer.get("customer_id") or "anon")
        engagement_score = float(customer.get("engagement_score") or 0)
        purchase_count = int(customer.get("purchase_count") or 0)
        
        last_action = customer.get("last_action_at")
        days_since_action = _days_since(last_action) if last_action else 30
        
        review_submitted = bool(customer.get("review_submitted") or customer.get("google_review_submitted"))
        total_spent = int(customer.get("total_spent_paise") or 0)
        
        opened_emails = int(customer.get("message_count_opened") or 0)
        clicked_emails = int(customer.get("message_count_clicked") or 0)
        
        # Call AI service
        ai_result = AIEnhancementService.get_psychology_profile(
            customer_id=customer_id,
            engagement_score=engagement_score,
            purchase_count=purchase_count,
            days_since_last_action=days_since_action,
            review_submitted=review_submitted,
            total_spent_paise=total_spent,
            opened_emails=opened_emails,
            clicked_emails=clicked_emails,
        )
        
        if not ai_result:
            return None
        
        # Convert AI result to PsychologyProfile
        psychology_type = ai_result.get("psychograph", "explorer")
        confidence = ai_result.get("confidence", 50)
        
        # Derive scores from engagement and purchase behavior
        lead_score = min(100, (engagement_score + (purchase_count * 10)))
        trust_score = min(100, (engagement_score + (50 if review_submitted else 0)))
        
        profile = PsychologyProfile(
            psychology_type=psychology_type,
            confidence=confidence,
            lead_score=lead_score,
            trust_score=trust_score,
            engagement_score=engagement_score,
            days_since_action=days_since_action,
            total_events=opened_emails + clicked_emails + purchase_count,
        )
        
        return profile
        
    except ImportError:
        logger.debug("AIEnhancementService not available, will use rule-based profiling")
        return None
    except Exception as e:
        logger.warning("AI profiling error: %s", e)
        return None


def classify_customer_psychology(customer: dict[str, Any]) -> PsychologyProfile:
    """
    Analyze customer behavior and classify into psychology type.
    
    Tries AI-powered profiling first (for accuracy), falls back to rule-based
    classification if AI is unavailable.
    
    Input: journey_customers row (dict)
    Output: PsychologyProfile with type + confidence
    """
    
    # ─── Attempt AI profiling first ───────────────────────────────────────────
    customer_id = str(customer.get("id") or customer.get("customer_id") or "")
    if customer_id:
        try:
            ai_profile = profile_with_ai(customer)
            if ai_profile:
                return ai_profile
        except Exception as e:
            logger.debug("AI psychology profiling failed, falling back to rule-based: %s", e)
    
    # ─── Fall back to rule-based classification ──────────────────────────────
    engagement_score = float(customer.get("engagement_score", 0))
    lead_score = float(customer.get("lead_score", 0))
    trust_score = float(customer.get("trust_score", 0))
    
    purchase_count = int(customer.get("purchase_count", 0))
    total_spent = int(customer.get("total_spent_paise", 0))
    
    # Website behavior
    pages_viewed = customer.get("pages_viewed", 0)
    if isinstance(pages_viewed, str):
        try:
            pages_viewed = len(pages_viewed.split(","))
        except:
            pages_viewed = 0
    
    time_on_site = customer.get("time_on_site_seconds", 0) or 0
    
    # Recency
    last_action = customer.get("last_action_at")
    days_since_action = _days_since(last_action) if last_action else 999
    
    # Journey stage
    segment = customer.get("customer_segment", "dormant")
    
    # Count total interactions
    total_events = int(customer.get("message_count_sent", 0)) + pages_viewed
    
    # ─── Classification Logic ─────────────────────────────────────────────────
    
    # Rule 1: URGENT_BUYER — Ready to purchase RIGHT NOW
    if lead_score >= 80 and engagement_score >= 70 and trust_score >= 60:
        confidence = min(100, trust_score + engagement_score) / 2
        return PsychologyProfile(
            psychology_type="urgent_buyer",
            confidence=confidence,
            lead_score=lead_score,
            trust_score=trust_score,
            engagement_score=engagement_score,
            days_since_action=days_since_action,
            total_events=total_events,
        )
    
    # Rule 2: QUALITY_FOCUSED — High trust, willing to pay premium
    if trust_score >= 70 and lead_score >= 60 and total_spent >= 500000:  # ₹5000+
        confidence = (trust_score + lead_score) / 2
        return PsychologyProfile(
            psychology_type="quality_focused",
            confidence=confidence,
            lead_score=lead_score,
            trust_score=trust_score,
            engagement_score=engagement_score,
            days_since_action=days_since_action,
            total_events=total_events,
        )
    
    # Rule 3: SKEPTIC — Low trust despite some interest
    if lead_score >= 40 and trust_score < 40:
        confidence = (40 - trust_score) / 40 * 100  # Inverted confidence in skepticism
        return PsychologyProfile(
            psychology_type="skeptic",
            confidence=min(100, confidence),
            lead_score=lead_score,
            trust_score=trust_score,
            engagement_score=engagement_score,
            days_since_action=days_since_action,
            total_events=total_events,
        )
    
    # Rule 4: PRICE_SENSITIVE — Looking at multiple options, comparing value
    if lead_score >= 50 and engagement_score >= 40 and pages_viewed >= 5:
        # High browsing activity + multiple product views
        confidence = (lead_score + engagement_score) / 2
        return PsychologyProfile(
            psychology_type="price_sensitive",
            confidence=confidence,
            lead_score=lead_score,
            trust_score=trust_score,
            engagement_score=engagement_score,
            days_since_action=days_since_action,
            total_events=total_events,
        )
    
    # Rule 5: EXPLORER — Browsing, early stage, low urgency
    if lead_score < 50 and engagement_score < 60 and trust_score < 50:
        confidence = (100 - lead_score) / 100 * 50  # Lower confidence for explorers
        return PsychologyProfile(
            psychology_type="explorer",
            confidence=confidence,
            lead_score=lead_score,
            trust_score=trust_score,
            engagement_score=engagement_score,
            days_since_action=days_since_action,
            total_events=total_events,
        )
    
    # Default: Explorer
    confidence = 40
    return PsychologyProfile(
        psychology_type="explorer",
        confidence=confidence,
        lead_score=lead_score,
        trust_score=trust_score,
        engagement_score=engagement_score,
        days_since_action=days_since_action,
        total_events=total_events,
    )


def get_psychology_message_variant(base_message: str, psychology: str) -> str:
    """
    Take a message template and adjust tone based on psychology type.
    
    Different customers see subtly different messaging for same core content.
    """
    
    variants = {
        "explorer": _variant_explorer,
        "skeptic": _variant_skeptic,
        "price_sensitive": _variant_price_sensitive,
        "quality_focused": _variant_quality_focused,
        "urgent_buyer": _variant_urgent,
    }
    
    variant_func = variants.get(psychology, _variant_explorer)
    return variant_func(base_message)


def _variant_explorer(msg: str) -> str:
    """Explorers need: education, information, low-pressure"""
    replacements = {
        "limited time": "available this season",
        "urgently": "whenever you're ready",
        "buy now": "learn more",
        "special offer": "special offer for curious minds",
    }
    result = msg
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result


def _variant_skeptic(msg: str) -> str:
    """Skeptics need: proof, reviews, guarantees, credentials"""
    additions = {
        "here's why": "here's why (backed by data):",
        "our customers": "98% of our customers",
        "trust us": "we're certified & verified",
    }
    result = msg
    for old, new in additions.items():
        result = result.replace(old, new)
    # Add proof signal if not present
    if "guarantee" not in result.lower() and "certified" not in result.lower():
        result += "\n\n✅ 30-day money-back guarantee | Lab verified | Certified organic"
    return result


def _variant_price_sensitive(msg: str) -> str:
    """Price-sensitive need: value calculation, bulk discounts, cost-per-use"""
    replacements = {
        "premium quality": "premium quality at fair price",
        "invest in": "invest smartly in",
        "buy": "get the best deal on",
    }
    result = msg
    for old, new in replacements.items():
        result = result.replace(old, new)
    # Emphasize value
    if "cost" not in result.lower() and "price" not in result.lower():
        result += "\n\n💰 Cost per use: just ₹20 per serving"
    return result


def _variant_quality_focused(msg: str) -> str:
    """Quality-focused need: premium attributes, sourcing, craftsmanship, heritage"""
    replacements = {
        "good quality": "premium quality",
        "spices": "artisanal spices",
        "fresh": "freshly sourced & hand-selected",
        "best": "the absolute finest",
    }
    result = msg
    for old, new in replacements.items():
        result = result.replace(old, new)
    # Add craftsmanship signal
    if "sourced" not in result.lower() and "heritage" not in result.lower():
        result += "\n\n👨‍🌾 Hand-selected from heritage farms | Small-batch crafted"
    return result


def _variant_urgent(msg: str) -> str:
    """Urgent buyers need: friction removal, quick checkout, immediate delivery"""
    replacements = {
        "click here": "checkout instantly",
        "learn more": "buy now",
        "available": "in stock, ships today",
        "get": "order now & receive",
    }
    result = msg
    for old, new in replacements.items():
        result = result.replace(old, new)
    # Add urgency signal
    if "ships" not in result.lower() and "express" not in result.lower():
        result += "\n\n⚡ Express checkout | Ships same-day"
    return result


def calculate_conversion_probability(profile: PsychologyProfile) -> float:
    """
    Given psychology profile, predict likelihood of conversion in next 24h.
    Returns 0-100 score.
    """
    base_score = profile.lead_score
    
    # Boost for high engagement
    if profile.engagement_score >= 70:
        base_score += 15
    
    # Reduce for long dormancy
    if profile.days_since_action > 30:
        base_score -= 20
    elif profile.days_since_action > 7:
        base_score -= 5
    
    # Psychology modifiers
    modifiers = {
        "urgent_buyer": 25,      # Very high likelihood
        "quality_focused": 15,   # Good likelihood if interested
        "price_sensitive": 10,   # Medium likelihood (will compare)
        "explorer": 0,           # Baseline
        "skeptic": -10,          # Lower (needs conversion)
    }
    
    base_score += modifiers.get(profile.psychology_type, 0)
    
    return max(0, min(100, base_score))


def get_message_intensity(conversion_prob: float) -> str:
    """
    Based on conversion probability, suggest message intensity.
    
    gentle       → low urgency, education-focused
    moderate     → balanced, some urgency
    aggressive   → strong CTA, time-limited offer
    final_offer  → last chance, maximum urgency
    """
    if conversion_prob >= 80:
        return "final_offer"
    elif conversion_prob >= 60:
        return "aggressive"
    elif conversion_prob >= 40:
        return "moderate"
    else:
        return "gentle"


def _days_since(iso_timestamp: str | None) -> int:
    """Calculate days since timestamp."""
    if not iso_timestamp:
        return 999
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        return max(0, int(delta.total_seconds() / 86400))
    except (ValueError, AttributeError):
        return 999
