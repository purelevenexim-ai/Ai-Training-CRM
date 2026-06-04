"""
AI client with Gemini primary + OpenRouter fallback for PureLeven WhatsApp intelligence.

STRICT GUARDRAILS:
  - AI NEVER generates prices, stock, offers, or delivery timelines
  - AI outputs ONLY structured JSON: {tone, story_type, product_id, cta_type, urgency}
  - All values validated against allowed enums before use
  - If AI output is invalid → safe fallback returned, never crash

Priority:
  1. Gemini API (free models: gemini-2.0-flash, gemini-1.5-flash)
  2. OpenRouter fallback (Deepseek models)
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

try:
    import httpx
except Exception:  # pragma: no cover - optional dependency for local reply tests
    httpx = None

from app.config import settings
from app.services.owner_dashboard_service import get_ai_control_settings

logger = logging.getLogger(__name__)

# ── Allowed AI output values (strict enum enforcement) ───────────────────────
ALLOWED_TONES = frozenset(["premium", "educational", "friendly", "founder", "social_proof"])
ALLOWED_STORY_TYPES = frozenset([
    "harvest_quality", "recipe", "emotional_family",
    "seasonal", "freshness", "founder_note", "testimonial", "usage_guide",
])
ALLOWED_CTA_TYPES = frozenset(["website", "recipe_link", "soft_browse", "founder_story", "soft_reminder"])
ALLOWED_URGENCY = frozenset(["low", "medium", "high"])

# ── Email AI enums ────────────────────────────────────────────────────────────
ALLOWED_EMAIL_TONES = frozenset(["premium", "friendly", "educational", "urgent", "nurturing"])
ALLOWED_PSYCHOGRAPHS = frozenset([
    "price_sensitive", "quality_seeker", "social_proof_responder",
    "sustainability_focused", "convenience_priority",
])
ALLOWED_CONTENT_PREFS = frozenset(["story", "benefit", "social_proof", "testimonial", "urgency"])
ALLOWED_PRODUCT_CATEGORIES = frozenset(["turmeric", "ghee", "spices", "supplements", "bundles", "general"])
ALLOWED_INCENTIVE_AMOUNTS = frozenset([50, 100, 150, 200])

# ── Model selection ───────────────────────────────────────────────────────────
MODEL_DECISION = "openai/gpt-4o-mini"   # Fallback model on OpenRouter
MODEL_REASONING = "openai/gpt-4o"        # Reasoning fallback
MODEL_FALLBACK = "openrouter/auto"       # If rate limit hit

RUNTIME_MODEL_MAP = {
    "gemini_flash": {"provider": "gemini", "model": "gemini-2.5-flash"},
    "openai_mini": {"provider": "openrouter", "model": "openai/gpt-4o-mini"},
    "claude_haiku": {"provider": "openrouter", "model": "anthropic/claude-3.5-haiku"},
    "openrouter_auto": {"provider": "openrouter", "model": "openrouter/auto"},
}


# ─────────────────────────────────────────────────────────────────────────────
class OpenRouterClient:
    """
    Thin wrapper around OpenRouter API.

    All methods return structured, validated Python dicts.
    If the API call fails or returns invalid data → returns a safe default.
    """

    def __init__(self) -> None:
        self._gemini_api_key = getattr(settings, "gemini_api_key", "")
        self._openrouter_api_key = getattr(settings, "openrouter_api_key", "")
        self._openrouter_base_url = getattr(settings, "openrouter_base_url", "https://openrouter.ai/api/v1")
        self._timeout = 20.0
        self._gemini_base_url = "https://generativelanguage.googleapis.com/v1beta/models"

    # ── Core request ─────────────────────────────────────────────────────────

    def _call_gemini(
        self,
        prompt: str,
        max_tokens: int = 100,
        temperature: float = 0.3,
        model_name: str = "gemini-2.5-flash",
    ) -> Optional[str]:
        """Try Gemini API first. Returns None on failure or if key not set."""
        if not self._gemini_api_key:
            return None

        try:
            import urllib.request as _urlreq
            import urllib.error as _urlerr

            request_body = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                    "thinkingConfig": {"thinkingBudget": 0},
                }
            }).encode()

            url = f"{self._gemini_base_url}/{model_name}:generateContent?key={self._gemini_api_key}"
            req = _urlreq.Request(
                url, data=request_body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with _urlreq.urlopen(req, timeout=int(self._timeout)) as resp:
                data = json.loads(resp.read())
                # Safely extract text from nested structure
                try:
                    candidates = data.get("candidates", [])
                    if candidates:
                        content = candidates[0].get("content", {})
                        parts = content.get("parts", [])
                        if parts and "text" in parts[0]:
                            text = parts[0]["text"].strip()
                            if text:
                                logger.info("Gemini API success")
                                return text
                except (KeyError, IndexError, AttributeError):
                    pass
                # If we get here, response was malformed
                logger.warning(f"Gemini returned empty/malformed response: {data}")
                return None

        except Exception as e:
            logger.warning(f"Gemini call failed: {e}")
            return None

    def _call(
        self,
        prompt: str,
        model: str = MODEL_DECISION,
        max_tokens: int = 100,
        temperature: float = 0.3,
    ) -> str | None:
        """
        Try Gemini first, fallback to OpenRouter.
        Send a prompt and return the raw text response, or None on failure.
        """
        runtime_control = get_ai_control_settings()
        selected_runtime = RUNTIME_MODEL_MAP.get(
            str(runtime_control.get("selected_model") or "gemini_flash"),
            RUNTIME_MODEL_MAP["gemini_flash"],
        )
        effective_temperature = runtime_control.get("temperature", temperature)
        if not isinstance(effective_temperature, (int, float)):
            effective_temperature = temperature

        if selected_runtime["provider"] == "gemini":
            result = self._call_gemini(
                prompt,
                max_tokens=max_tokens,
                temperature=float(effective_temperature),
                model_name=str(selected_runtime["model"]),
            )
            if result is not None:
                return result
        elif selected_runtime["provider"] == "openrouter":
            model = str(selected_runtime["model"])

        # Fallback to OpenRouter
        if not self._openrouter_api_key:
            logger.warning("Neither GEMINI_API_KEY nor OPENROUTER_API_KEY set — AI disabled")
            return None

        if httpx is None:
            logger.warning("httpx is not installed — OpenRouter fallback disabled")
            return None

        headers = {
            "Authorization": f"Bearer {self._openrouter_api_key}",
            "HTTP-Referer": "https://pureleven.com",
            "X-Title": "PureLeven WhatsApp AI",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": float(effective_temperature),
        }

        try:
            with httpx.Client(timeout=self._timeout) as client:
                resp = client.post(
                    f"{self._openrouter_base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                logger.debug("OpenRouter API success (fallback from Gemini)")
                return data["choices"][0]["message"]["content"].strip()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("OpenRouter rate limit hit — using fallback decision")
            else:
                logger.error("OpenRouter HTTP error %s: %s", e.response.status_code, e.response.text[:200])
        except Exception as exc:
            logger.error("OpenRouter call failed: %s", exc)

        return None

    # ── Decision engine ───────────────────────────────────────────────────────

    def decide_next_message(
        self,
        customer: dict[str, Any],
        conversation_history: list[dict[str, Any]],
        available_products: list[dict[str, Any]],
        session_turn: int,
    ) -> dict[str, Any]:
        """
        Given customer context + conversation history, decide the next message parameters.

        AI outputs ONLY: tone, story_type, product_id, cta_type, urgency
        Backend uses these to render a SAFE message using real Shopify data.

        Returns validated dict, never raises.
        """
        if not available_products:
            return _safe_fallback_decision(session_turn)

        product_list = "\n".join(
            f"  - {p['id']}: {p['title']} (₹{p['price']}, "
            f"stock: {p.get('inventory_status', 'unknown')}, tags: {p.get('tags', '')})"
            for p in available_products[:10]
        )

        history_summary = ""
        if conversation_history:
            recent = conversation_history[-4:]
            history_summary = "\n".join(
                f"  [{m['actor']}] type={m.get('message_type','?')} content={m.get('customer_text') or m.get('message_type','sent')}"
                for m in recent
            )

        prompt = f"""You are helping PureLeven, a Kerala organic spice brand, decide the next WhatsApp message.

Customer profile:
  Name: {customer.get('name', 'Customer')}
  Segment: {customer.get('customer_segment', 'new')}
  Engagement score: {customer.get('engagement_score', 0)}
  Last purchase: {customer.get('last_purchase_at', 'unknown')}
  Do not message: {customer.get('do_not_message', 0)}

Conversation so far (turn {session_turn}):
{history_summary or '  (first message)'}

Available products (ONLY choose product_id from this list):
{product_list}

Task: Decide the best next message parameters.

Rules:
  - If turn >= 4, prefer soft_reminder (do not push hard)
  - If segment is dormant or engagement < 0, use educational tone
  - If customer complained before (seen in history), return urgency=low
  - Never pick a product not in the list above
  - Respect Kerala spice brand premium positioning

Respond with ONLY valid JSON (no markdown, no explanation):
{{
  "tone": "<one of: premium|educational|friendly|founder|social_proof>",
  "story_type": "<one of: harvest_quality|recipe|emotional_family|seasonal|freshness|founder_note|testimonial|usage_guide>",
  "product_id": "<exact id from list above>",
  "cta_type": "<one of: website|recipe_link|soft_browse|founder_story|soft_reminder>",
  "urgency": "<one of: low|medium|high>",
  "reason": "<one sentence why>"
}}"""

        raw = self._call(prompt, model=MODEL_DECISION, max_tokens=150, temperature=0.3)

        if raw:
            decision = _parse_and_validate_decision(raw, available_products)
            if decision:
                return decision

        logger.warning("AI decision invalid or unavailable — using rule-based fallback")
        return _safe_fallback_decision(session_turn, available_products)

    # ── Email subject line generation ─────────────────────────────────────────

    def generate_email_subjects(
        self,
        stage: str,
        customer_segment: str,
        product_name: str,
        psychology_type: str = "explorer",
    ) -> dict[str, Any]:
        """
        Generate 3 AI-optimised email subject line variants for A/B testing.

        Returns: {variants: [str, str, str], best_index: int, reason: str, source: str}
        Never raises — returns safe static subjects on failure.
        """
        prompt = f"""You are a high-converting email copywriter for PureLeven, a premium organic spice brand from Kerala.

Generate 3 subject line variants for a lifecycle email.

Journey stage: {stage}
Customer segment: {customer_segment}
Featured product: {product_name}
Customer psychology: {psychology_type}

Rules:
- Max 60 characters each
- No misleading claims ("You won", "Urgent" spam triggers)
- No prices or discounts unless stage is upsell/winback
- Tone must match psychology: price_sensitive=value, quality_seeker=premium, social_proof_responder=reviews/numbers, sustainability_focused=organic/earth, convenience_priority=fast/easy
- Use emojis sparingly (max 1 per subject)
- Must feel personal, not mass-email

Respond ONLY with valid JSON, no markdown:
{{
  "variants": ["subject 1", "subject 2", "subject 3"],
  "best_index": 0,
  "reason": "one sentence explaining the best variant"
}}"""

        raw = self._call(prompt, model=MODEL_DECISION, max_tokens=200, temperature=0.7)
        if raw:
            result = _parse_subject_variants(raw)
            if result:
                result["source"] = "ai"
                return result

        logger.warning("AI subject generation failed — returning static fallback")
        return _fallback_subjects(stage, product_name)

    # ── Product recommendations ───────────────────────────────────────────────

    def recommend_products(
        self,
        purchased_product: str,
        customer_segment: str,
        purchase_count: int,
        available_categories: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Recommend the top 3 next products with reasoning.

        Returns: {recommendations: [{category, product_name, reason}, ...], source: str}
        Only recommends from verified categories. Never invents products.
        """
        categories = available_categories or list(ALLOWED_PRODUCT_CATEGORIES - {"general"})
        cat_list = ", ".join(categories)

        prompt = f"""You are a product recommendation engine for PureLeven organic spices.

Customer just purchased: {purchased_product}
Customer segment: {customer_segment}
Previous purchases: {purchase_count}

Available product categories you CAN recommend (ONLY from this list): {cat_list}

Recommend top 3 complementary products.

Rules:
- Only use categories from the list above — no others
- Explain why it complements the purchase
- Consider cooking synergy (e.g., turmeric + ghee for golden milk)
- Consider progression (starter → premium → combo)
- No invented brand names, no prices, no specific SKUs

Respond ONLY with valid JSON, no markdown:
{{
  "recommendations": [
    {{"category": "category_name", "product_name": "display name", "reason": "why they'd want this"}},
    {{"category": "category_name", "product_name": "display name", "reason": "why they'd want this"}},
    {{"category": "category_name", "product_name": "display name", "reason": "why they'd want this"}}
  ]
}}"""

        raw = self._call(prompt, model=MODEL_DECISION, max_tokens=300, temperature=0.4)
        if raw:
            result = _parse_product_recommendations(raw, categories)
            if result:
                result["source"] = "ai"
                return result

        logger.warning("AI product recommendation failed — returning category-based fallback")
        return _fallback_recommendations(purchased_product)

    # ── Customer psychology profiling ─────────────────────────────────────────

    def profile_psychology(
        self,
        engagement_score: float,
        purchase_count: int,
        days_since_last_action: int,
        review_submitted: bool,
        total_spent_paise: int,
        opened_emails: int = 0,
        clicked_emails: int = 0,
    ) -> dict[str, Any]:
        """
        AI-powered psychology profiling for deeper personalization.

        Returns: {psychograph, tone, content_preference, urgency, confidence, reason, source}
        Falls back to rule-based classification on failure.
        """
        prompt = f"""Classify a PureLeven organic food customer's buying psychology.

Customer signals:
- Engagement score: {engagement_score}/100
- Purchase count: {purchase_count}
- Days since last activity: {days_since_last_action}
- Submitted a review: {review_submitted}
- Total spent (paise): {total_spent_paise} (₹{total_spent_paise // 100})
- Emails opened: {opened_emails}
- Emails clicked: {clicked_emails}

Choose ONE psychograph:
- price_sensitive: Clicks only on discount offers, low spend, hesitates
- quality_seeker: High spend, engages with premium content, ignores discounts
- social_proof_responder: Submits reviews, clicks testimonial emails, shares
- sustainability_focused: Engages with organic/ethical content, long sessions
- convenience_priority: Quick decisions, clicks CTAs fast, values speed

Rules:
- Pick the most dominant trait only
- Be decisive, not neutral
- Confidence 60-95 based on signal strength

Respond ONLY with valid JSON, no markdown:
{{
  "psychograph": "one_of_the_five",
  "tone": "one of: premium|friendly|educational|urgent|nurturing",
  "content_preference": "one of: story|benefit|social_proof|testimonial|urgency",
  "urgency_level": "one of: low|medium|high",
  "confidence": 75,
  "reason": "one sentence"
}}"""

        raw = self._call(prompt, model=MODEL_DECISION, max_tokens=150, temperature=0.2)
        if raw:
            result = _parse_psychology_profile(raw)
            if result:
                result["source"] = "ai"
                return result

        logger.warning("AI psychology profiling failed — using rule-based fallback")
        return _fallback_psychology(engagement_score, purchase_count, total_spent_paise)

    # ── Review incentive optimization ─────────────────────────────────────────

    def optimize_review_incentive(
        self,
        customer_segment: str,
        engagement_score: float,
        purchase_count: int,
        review_status: str,
        max_coupon_inr: int = 200,
    ) -> dict[str, Any]:
        """
        Decide optimal review incentive: coupon amount + urgency tone.

        Returns: {coupon_inr: int, urgency: str, tone: str, message_hook: str, source: str}
        """
        prompt = f"""Decide the minimum effective review incentive for a PureLeven customer.

Customer:
- Segment: {customer_segment}
- Engagement score: {engagement_score}/100
- Purchase count: {purchase_count}
- Review status: {review_status}
- Maximum allowed coupon: ₹{max_coupon_inr}

Goal: Get a Google review. Use the smallest effective coupon to preserve margin.

Allowed coupon amounts: 50, 100, 150, 200 (in INR)
Urgency options: low, medium, high
Tone options: nurturing, friendly, urgent, premium

Rules:
- Loyal customers (purchase_count >= 3) get 50-100 because they love us
- High-engagement new customers get 100 (they're warm)
- Low-engagement customers get 150-200 (need bigger push)
- Max is {max_coupon_inr} INR — never exceed it
- Only output amounts from: 50, 100, 150, 200

Respond ONLY with valid JSON, no markdown:
{{
  "coupon_inr": 100,
  "urgency": "medium",
  "tone": "friendly",
  "message_hook": "one sentence to add to review request email"
}}"""

        raw = self._call(prompt, model=MODEL_DECISION, max_tokens=120, temperature=0.3)
        if raw:
            result = _parse_incentive(raw, max_coupon_inr)
            if result:
                result["source"] = "ai"
                return result

        logger.warning("AI incentive optimization failed — using default incentive")
        return _fallback_incentive(engagement_score, purchase_count, max_coupon_inr)

    # ── Abandoned lead context generation ────────────────────────────────────

    def generate_abandoned_context(
        self,
        interest_product: str,
        interest_category: str,
        days_abandoned: int,
        engagement_score: float,
        campaign_number: int,
    ) -> str:
        """
        Generate a personalization context string for abandoned lead emails.

        Returns: A plain string describing the customer's interest angle.
        Falls back to empty string (templates handle missing context gracefully).
        """
        prompt = f"""Generate a one-sentence personalization insight for an abandoned cart email.

Abandoned product: {interest_product}
Category: {interest_category}
Days since abandonment: {days_abandoned}
Engagement score: {engagement_score}/100
Campaign number: {campaign_number} of 6

Task: Write ONE sentence that explains WHY this customer might love this product.
This will be injected into the email body for personalization.

Rules:
- Max 20 words
- Focus on the product benefit, not the discount
- Do NOT mention prices or specific discounts
- Do NOT use phrases like "our records show" or "we noticed"
- Sound warm and genuine, not salesy

Output ONLY the sentence, no JSON, no punctuation at end except period."""

        raw = self._call(prompt, model=MODEL_DECISION, max_tokens=60, temperature=0.6)
        if raw:
            # Sanitize — only single sentence, no quotes, no hallucinated claims
            line = raw.strip().strip('"\'').split('\n')[0]
            if 10 <= len(line) <= 150:
                return line

        return ""

    # ── Reply classification ──────────────────────────────────────────────────

    def classify_reply(self, reply_text: str) -> dict[str, Any]:
        """
        Classify a customer WhatsApp reply into an intent category.

        Returns: {intent, confidence, action}
        Never hallucinate — returns 'unknown' on failure.
        """
        prompt = f"""Classify this WhatsApp reply to a Kerala spice brand.

Reply: "{reply_text}"

Important:
- Customers may misspell product names or use Manglish / transliterated Malayalam.
- Infer the intended intent from the closest reasonable spelling and context.
- Treat typoed product names as the same product when the meaning is clear.

Categories:
  purchase_intent    - wants to buy, asks about ordering
  bulk_inquiry       - asks about bulk / wholesale / corporate
  question_product   - asks about a specific product
  question_shipping  - asks about delivery or tracking
  complaint          - dissatisfied, issue, problem
  feedback_positive  - happy, thank you, liked the product
  unsubscribe        - wants to stop messages
  recipe_interest    - interested in recipes / cooking
  affirmation        - ok / yes / sure / will check (positive but passive)
  ignore             - one word irrelevant reply, no action needed

Output ONLY the category name, lowercase, no spaces, no punctuation."""

        raw = self._call(prompt, model=MODEL_DECISION, max_tokens=32, temperature=0.1)

        intent = "unknown"
        if raw:
            cleaned = raw.strip().lower().replace(" ", "_")
            valid_intents = {
                "purchase_intent", "bulk_inquiry", "question_product",
                "question_shipping", "complaint", "feedback_positive",
                "unsubscribe", "recipe_interest", "affirmation", "ignore",
            }
            if cleaned in valid_intents:
                intent = cleaned

        high_confidence = {"purchase_intent", "bulk_inquiry", "complaint", "unsubscribe"}
        return {
            "intent": intent,
            "confidence": 0.9 if intent in high_confidence else 0.7,
            "action": _intent_to_action(intent),
        }


# ── Private helpers ───────────────────────────────────────────────────────────

def _parse_and_validate_decision(
    raw: str,
    available_products: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """Parse AI JSON response and validate all fields. Returns None if invalid."""
    try:
        # Strip markdown code fences if present
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        text = text.strip()

        data = json.loads(text)
    except (json.JSONDecodeError, IndexError):
        logger.debug("AI returned non-JSON: %s", raw[:200])
        return None

    # Validate all fields against strict enums
    tone = str(data.get("tone", "")).lower()
    story_type = str(data.get("story_type", "")).lower()
    product_id = str(data.get("product_id", ""))
    cta_type = str(data.get("cta_type", "")).lower()
    urgency = str(data.get("urgency", "low")).lower()

    if tone not in ALLOWED_TONES:
        logger.debug("AI returned invalid tone: %s", tone)
        return None

    if story_type not in ALLOWED_STORY_TYPES:
        logger.debug("AI returned invalid story_type: %s", story_type)
        return None

    if cta_type not in ALLOWED_CTA_TYPES:
        logger.debug("AI returned invalid cta_type: %s", cta_type)
        return None

    if urgency not in ALLOWED_URGENCY:
        urgency = "low"

    # CRITICAL: product_id must exist in real catalog
    valid_product_ids = {p["id"] for p in available_products}
    if product_id not in valid_product_ids:
        logger.warning("AI hallucinated product_id '%s' — not in catalog", product_id)
        # Use first available product instead (safe fallback)
        if available_products:
            product_id = available_products[0]["id"]
        else:
            return None

    return {
        "tone": tone,
        "story_type": story_type,
        "product_id": product_id,
        "cta_type": cta_type,
        "urgency": urgency,
        "reason": str(data.get("reason", ""))[:200],
        "source": "ai",
    }


def _safe_fallback_decision(
    turn: int,
    available_products: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a deterministic, safe fallback decision without any AI call."""
    product_id = available_products[0]["id"] if available_products else ""

    if turn == 0:
        return {"tone": "premium", "story_type": "harvest_quality", "product_id": product_id,
                "cta_type": "soft_browse", "urgency": "low", "reason": "fallback_turn_0", "source": "fallback"}
    if turn == 1:
        return {"tone": "educational", "story_type": "recipe", "product_id": product_id,
                "cta_type": "recipe_link", "urgency": "low", "reason": "fallback_turn_1", "source": "fallback"}
    if turn == 2:
        return {"tone": "social_proof", "story_type": "testimonial", "product_id": product_id,
                "cta_type": "website", "urgency": "medium", "reason": "fallback_turn_2", "source": "fallback"}
    if turn == 3:
        return {"tone": "friendly", "story_type": "freshness", "product_id": product_id,
                "cta_type": "soft_browse", "urgency": "medium", "reason": "fallback_turn_3", "source": "fallback"}
    return {"tone": "friendly", "story_type": "founder_note", "product_id": product_id,
            "cta_type": "soft_reminder", "urgency": "low", "reason": "fallback_final", "source": "fallback"}


def _intent_to_action(intent: str) -> str:
    mapping = {
        "purchase_intent": "add_hot_lead_tag",
        "bulk_inquiry": "alert_owner_urgent",
        "question_product": "schedule_product_info_reply",
        "question_shipping": "schedule_shipping_reply",
        "complaint": "pause_campaigns_alert_owner",
        "feedback_positive": "add_happy_customer_tag",
        "unsubscribe": "unsubscribe_customer",
        "recipe_interest": "add_recipe_interest_tag",
        "affirmation": "log_engagement",
        "ignore": "no_action",
        "unknown": "no_action",
    }
    return mapping.get(intent, "no_action")


def _strip_json(raw: str) -> str:
    """Strip markdown code fences from AI response."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return text.strip()


def _parse_subject_variants(raw: str) -> dict[str, Any] | None:
    """Parse and validate AI-generated email subject variants."""
    try:
        data = json.loads(_strip_json(raw))
    except (json.JSONDecodeError, IndexError):
        return None

    variants = data.get("variants", [])
    if not isinstance(variants, list) or len(variants) < 1:
        return None

    # Sanitize: max 60 chars, strip quotes, ensure strings
    clean_variants = []
    for v in variants[:3]:
        v = str(v).strip().strip('"\'')[:60]
        if v:
            clean_variants.append(v)

    if not clean_variants:
        return None

    best_index = int(data.get("best_index", 0))
    if best_index >= len(clean_variants):
        best_index = 0

    return {
        "variants": clean_variants,
        "best_index": best_index,
        "best": clean_variants[best_index],
        "reason": str(data.get("reason", ""))[:200],
    }


def _fallback_subjects(stage: str, product_name: str) -> dict[str, Any]:
    """Static fallback subject lines when AI is unavailable."""
    static: dict[str, list[str]] = {
        "day2":  ["Your PureLeven order is confirmed! 🌿", "Order received — thank you!", "We've got your order ready"],
        "day5":  ["Your order is on its way! 🚚", "Good news — your spices are coming", "Your delivery is moving 📦"],
        "day15": ["How are you enjoying PureLeven? ⭐", "A quick favor — share your experience", "Your review means the world to us"],
        "day30": ["Complete your organic pantry 💚", "What pairs perfectly with your last order?", "You might love this next"],
        "day60": ["Organic gifting for your team 🏢", "Corporate gifting made wholesome", "Gift wellness this season"],
        "day75": ["You've earned VIP status 💚", "A special reward for our loyalists", "This one's just for you"],
        "day95": ["We miss you — 15% off inside 👋", "Come back? Here's a little something", "Your organic journey isn't over"],
    }
    variants = static.get(stage, [f"A message from PureLeven", f"Your {product_name} is waiting", "Stay organic with PureLeven"])
    return {"variants": variants, "best_index": 0, "best": variants[0], "reason": "static_fallback", "source": "fallback"}


def _parse_product_recommendations(raw: str, allowed_categories: list[str]) -> dict[str, Any] | None:
    """Parse and validate AI product recommendations — only allow verified categories."""
    try:
        data = json.loads(_strip_json(raw))
    except (json.JSONDecodeError, IndexError):
        return None

    recs_raw = data.get("recommendations", [])
    if not isinstance(recs_raw, list):
        return None

    valid_recs = []
    for rec in recs_raw[:3]:
        category = str(rec.get("category", "")).lower().strip()
        if category not in allowed_categories:
            logger.warning("AI hallucinated product category '%s' — skipping", category)
            continue
        valid_recs.append({
            "category": category,
            "product_name": str(rec.get("product_name", ""))[:80],
            "reason": str(rec.get("reason", ""))[:150],
        })

    if not valid_recs:
        return None

    return {"recommendations": valid_recs}


def _fallback_recommendations(purchased_product: str) -> dict[str, Any]:
    """Static cross-sell fallback based on purchased product name."""
    lower = purchased_product.lower()
    if "turmeric" in lower:
        recs = [
            {"category": "ghee", "product_name": "Organic A2 Ghee", "reason": "Golden milk needs both turmeric and ghee"},
            {"category": "spices", "product_name": "Black Pepper Powder", "reason": "Piperine in pepper boosts turmeric absorption"},
            {"category": "bundles", "product_name": "Wellness Spice Combo", "reason": "Complete your anti-inflammatory kitchen"},
        ]
    elif "ghee" in lower:
        recs = [
            {"category": "turmeric", "product_name": "Organic Turmeric Powder", "reason": "Golden milk essential pairing"},
            {"category": "spices", "product_name": "Cardamom Pods", "reason": "Elevate ghee-based recipes"},
            {"category": "bundles", "product_name": "Kitchen Starter Pack", "reason": "Everything you need for organic cooking"},
        ]
    else:
        recs = [
            {"category": "bundles", "product_name": "Spice Combo Pack", "reason": "Complete your organic pantry"},
            {"category": "turmeric", "product_name": "Organic Turmeric", "reason": "Our bestselling anti-inflammatory"},
            {"category": "ghee", "product_name": "Organic A2 Ghee", "reason": "Pure and traditionally made"},
        ]
    return {"recommendations": recs, "source": "fallback"}


def _parse_psychology_profile(raw: str) -> dict[str, Any] | None:
    """Parse and validate AI psychology profile."""
    try:
        data = json.loads(_strip_json(raw))
    except (json.JSONDecodeError, IndexError):
        return None

    psychograph = str(data.get("psychograph", "")).lower()
    if psychograph not in ALLOWED_PSYCHOGRAPHS:
        return None

    tone = str(data.get("tone", "friendly")).lower()
    if tone not in ALLOWED_EMAIL_TONES:
        tone = "friendly"

    content_pref = str(data.get("content_preference", "benefit")).lower()
    if content_pref not in ALLOWED_CONTENT_PREFS:
        content_pref = "benefit"

    urgency = str(data.get("urgency_level", "medium")).lower()
    if urgency not in ALLOWED_URGENCY:
        urgency = "medium"

    confidence = max(0.0, min(100.0, float(data.get("confidence", 65))))

    return {
        "psychograph": psychograph,
        "tone": tone,
        "content_preference": content_pref,
        "urgency": urgency,
        "confidence": confidence,
        "reason": str(data.get("reason", ""))[:200],
    }


def _fallback_psychology(
    engagement_score: float,
    purchase_count: int,
    total_spent_paise: int,
) -> dict[str, Any]:
    """Rule-based psychology fallback when AI is unavailable."""
    if purchase_count >= 3 and total_spent_paise >= 100000:
        psychograph = "quality_seeker"
        tone = "premium"
    elif engagement_score >= 60:
        psychograph = "social_proof_responder"
        tone = "friendly"
    elif total_spent_paise < 30000:
        psychograph = "price_sensitive"
        tone = "educational"
    else:
        psychograph = "sustainability_focused"
        tone = "nurturing"

    return {
        "psychograph": psychograph,
        "tone": tone,
        "content_preference": "benefit",
        "urgency": "medium" if engagement_score >= 40 else "low",
        "confidence": 60.0,
        "reason": "rule_based_fallback",
        "source": "fallback",
    }


def _parse_incentive(raw: str, max_coupon_inr: int) -> dict[str, Any] | None:
    """Parse and validate AI review incentive decision."""
    try:
        data = json.loads(_strip_json(raw))
    except (json.JSONDecodeError, IndexError):
        return None

    coupon_inr = int(data.get("coupon_inr", 100))
    # Snap to nearest allowed value, never exceed max
    allowed = [v for v in ALLOWED_INCENTIVE_AMOUNTS if v <= max_coupon_inr]
    if not allowed:
        allowed = [50]
    coupon_inr = min(allowed, key=lambda x: abs(x - coupon_inr))

    urgency = str(data.get("urgency", "medium")).lower()
    if urgency not in ALLOWED_URGENCY:
        urgency = "medium"

    tone = str(data.get("tone", "friendly")).lower()
    if tone not in ALLOWED_EMAIL_TONES:
        tone = "friendly"

    message_hook = str(data.get("message_hook", ""))[:200]

    return {
        "coupon_inr": coupon_inr,
        "urgency": urgency,
        "tone": tone,
        "message_hook": message_hook,
    }


def _fallback_incentive(
    engagement_score: float,
    purchase_count: int,
    max_coupon_inr: int,
) -> dict[str, Any]:
    """Rule-based incentive fallback."""
    if purchase_count >= 3:
        coupon = min(100, max_coupon_inr)
        tone = "friendly"
        urgency = "low"
    elif engagement_score >= 40:
        coupon = min(100, max_coupon_inr)
        tone = "friendly"
        urgency = "medium"
    else:
        coupon = min(150, max_coupon_inr)
        tone = "nurturing"
        urgency = "medium"

    return {
        "coupon_inr": coupon,
        "urgency": urgency,
        "tone": tone,
        "message_hook": f"We appreciate every PureLeven customer — your ₹{coupon} coupon is waiting!",
        "source": "fallback",
    }


# ── Module-level singleton ────────────────────────────────────────────────────
ai_client = OpenRouterClient()
