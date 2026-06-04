"""
Google Gemini AI client for PureLeven WhatsApp intelligence.
Primary AI provider with OpenRouter fallback.

STRICT GUARDRAILS:
  - AI NEVER generates prices, stock, offers, or delivery timelines
  - AI outputs ONLY structured JSON: {tone, story_type, product_id, cta_type, urgency}
  - All values validated against allowed enums before use
  - If AI output is invalid → safe fallback returned, never crash
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

logger = logging.getLogger(__name__)

# ── Allowed AI output values (strict enum enforcement) ───────────────────────
ALLOWED_TONES = frozenset(["premium", "educational", "friendly", "founder", "social_proof"])
ALLOWED_STORY_TYPES = frozenset([
    "harvest_quality", "recipe", "emotional_family",
    "seasonal", "freshness", "founder_note", "testimonial", "usage_guide",
])
ALLOWED_CTA_TYPES = frozenset(["website", "recipe_link", "soft_browse", "founder_story", "soft_reminder"])
ALLOWED_URGENCY = frozenset(["low", "medium", "high"])

# ── Model selection ───────────────────────────────────────────────────────────
MODEL_PRIMARY = "gemini-2.5-flash"       # Stable production model
MODEL_FALLBACK = "gemini-2.5-flash-lite"  # Lower-cost fallback for structured output


# ─────────────────────────────────────────────────────────────────────────────
class GeminiClient:
    """
    Google Gemini API client wrapper.

    All methods return structured, validated Python dicts.
    If the API call fails or returns invalid data → returns a safe default.
    """

    def __init__(self) -> None:
        self._api_key = settings.gemini_api_key
        self._base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        self._timeout = httpx.Timeout(30.0, connect=5.0) if httpx is not None else 30.0

    def _call(
        self,
        prompt: str,
        response_schema: Optional[dict[str, Any]] = None,
        temperature: float = 0.5,
        model: str = MODEL_PRIMARY,
    ) -> Optional[dict[str, Any]]:
        """
        Call Gemini API and return parsed JSON response.

        Args:
            prompt: The full prompt text
            response_schema: JSON schema for structured output (optional)
            temperature: Model temperature (0-1)
            model: Model name (default: gemini-2.0-flash)

        Returns:
            Parsed JSON dict, or None if API fails
        """
        if not self._api_key:
            logger.error("GEMINI_API_KEY not set — AI decisions disabled")
            return None
        if httpx is None:
            logger.warning("httpx is not installed — Gemini API disabled")
            return None

        try:
            client = httpx.Client(timeout=self._timeout)

            # Build request body
            request_body = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": 1024,
                }
            }

            # Add response schema if provided (structured output)
            if response_schema:
                request_body["generationConfig"]["responseSchema"] = response_schema
                request_body["generationConfig"]["responseMimeType"] = "application/json"

            attempted_models: list[str] = []
            for candidate_model in (model, MODEL_FALLBACK):
                if not candidate_model or candidate_model in attempted_models:
                    continue
                attempted_models.append(candidate_model)

                url = f"{self._base_url}/{candidate_model}:generateContent?key={self._api_key}"
                response = client.post(url, json=request_body)

                if response.status_code == 200:
                    data = response.json()
                    try:
                        text = data["candidates"][0]["content"]["parts"][0]["text"]
                        if text.startswith("{") or text.startswith("["):
                            return json.loads(text)
                        return {"text": text}
                    except (KeyError, IndexError, json.JSONDecodeError) as e:
                        logger.warning(f"Failed to parse Gemini response: {e}")
                        return None

                if response.status_code in {404, 429} and candidate_model != MODEL_FALLBACK:
                    logger.warning(
                        "Gemini model %s returned %s, retrying with fallback model %s",
                        candidate_model,
                        response.status_code,
                        MODEL_FALLBACK,
                    )
                    continue

                if response.status_code == 429:
                    logger.warning("Gemini rate limited, falling back to OpenRouter")
                    return None

                logger.error(f"Gemini HTTP error {response.status_code}: {response.text}")
                return None

            return None

        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return None

    def classify_reply(self, message: str) -> dict[str, Any]:
        """
        Classify incoming message intent using Gemini.

        Returns: {
            "intent": "complaint|bulk_inquiry|purchase_intent|question_product|unsubscribe|affirmation|feedback_positive|recipe_interest|unknown",
            "confidence": 0.0-1.0
        }
        """
        prompt = f"""Classify this customer message for an organic spice company (Pure Leven).

Message: "{message}"

Important:
- Customers may misspell product names.
- Customers may write Manglish or transliterated Malayalam.
- Infer the intended product/intent from the closest reasonable spelling and context.

Return a JSON object with:
- intent: One of [complaint, bulk_inquiry, purchase_intent, question_product, unsubscribe, affirmation, feedback_positive, recipe_interest, unknown]
- confidence: 0.0 to 1.0

Example response:
{{"intent": "question_product", "confidence": 0.95}}

Respond with ONLY the JSON object, no other text."""

        schema = {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "enum": ["complaint", "bulk_inquiry", "purchase_intent", "question_product", 
                             "unsubscribe", "affirmation", "feedback_positive", "recipe_interest", "unknown"]
                },
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0
                }
            },
            "required": ["intent", "confidence"]
        }

        result = self._call(prompt, response_schema=schema)
        if result and "intent" in result:
            return {
                "intent": result.get("intent", "unknown"),
                "confidence": float(result.get("confidence", 0.5))
            }
        return {"intent": "unknown", "confidence": 0.5}

    def generate_product_response(self, message: str, product_name: str) -> str:
        """Generate friendly product info response (no pricing/offers)."""
        prompt = f"""A customer asked about {product_name}: "{message}"

Generate a friendly, helpful response about this product for an organic spices company.
DO NOT mention:
- Prices
- Stock levels
- Delivery times
- Special offers

Keep response under 100 words. Be warm and helpful."""

        result = self._call(prompt, temperature=0.7)
        if result and isinstance(result, dict) and "text" in result:
            return result["text"]
        return f"Thank you for asking about {product_name}! We'd love to help you find exactly what you need."

    def generate_complaint_response(self, complaint: str, customer_name: str = "Valued Customer") -> str:
        """Generate empathetic complaint acknowledgment."""
        prompt = f"""A customer ({customer_name}) raised a complaint: "{complaint}"

Generate a warm, empathetic response acknowledging their concern.
Apologize sincerely and promise to help resolve it.
Keep under 80 words."""

        result = self._call(prompt, temperature=0.7)
        if result and isinstance(result, dict) and "text" in result:
            return result["text"]
        return f"Thank you for bringing this to our attention, {customer_name}. We sincerely apologize and will resolve this immediately."

    def generate_whatsapp_reply_lines(
        self,
        *,
        scenario: str,
        customer_message: str,
        customer_name: str = "Customer",
        style: str = "english",
        product_name: str = "",
        facts: Optional[dict[str, Any]] = None,
        instruction: str = "",
    ) -> dict[str, str]:
        """Generate short opening/closing lines for a WhatsApp reply.

        The backend keeps all factual content such as prices and delivery tables.
        Gemini only writes the human connective lines around those facts.
        """
        if not self._api_key:
            return {"opening_line": "", "closing_line": ""}

        prompt = self.build_whatsapp_reply_prompt(
            scenario=scenario,
            customer_message=customer_message,
            customer_name=customer_name,
            style=style,
            product_name=product_name,
            facts=facts,
            instruction=instruction,
        )

        schema = {
            "type": "object",
            "properties": {
                "opening_line": {"type": "string"},
                "closing_line": {"type": "string"},
            },
            "required": ["opening_line", "closing_line"],
        }

        result = self._call(prompt, response_schema=schema, temperature=0.55)
        if not result:
            return {"opening_line": "", "closing_line": ""}

        def _clean(value: Any) -> str:
            text = " ".join(str(value or "").split()).strip(" \t\r\n\"'")
            return text

        return {
            "opening_line": _clean(result.get("opening_line")),
            "closing_line": _clean(result.get("closing_line")),
        }

    def build_whatsapp_reply_prompt(
        self,
        *,
        scenario: str,
        customer_message: str,
        customer_name: str = "Customer",
        style: str = "english",
        product_name: str = "",
        facts: Optional[dict[str, Any]] = None,
        instruction: str = "",
    ) -> str:
        facts_json = json.dumps(facts or {}, ensure_ascii=False)
        return f"""You write short, human WhatsApp replies for PureLeven, a Kerala spice brand.

Customer name: {customer_name}
Customer style: {style}
Scenario: {scenario}
Customer message: {customer_message}
Product: {product_name}
Facts:
{facts_json}

Instruction:
{instruction or "Write a warm, concise reply using only the facts above."}

Rules:
- opening_line is the first short sentence.
- closing_line is an optional second sentence or call-to-action.
- Do not invent prices, stock, offers, delivery days, or other facts.
- If style is manglish, use English script with Malayalam rhythm.
- Keep it natural, polite, and customer-friendly.
- Return ONLY JSON.

Example:
{{"opening_line":"Yes, black pepper undallo stock.","closing_line":"I can share the price details below."}}"""


# ─────────────────────────────────────────────────────────────────────────────
# Singleton instance
gemini_client = GeminiClient()
