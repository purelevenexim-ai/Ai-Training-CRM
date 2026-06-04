"""
claude_analyzer.py — Phase 9: AI-powered ad performance analysis
Calls Claude via OpenRouter API with yesterday's campaign metrics.

Required env:
  OPENROUTER_API_KEY = sk-or-v1-xxxxx

Optional env:
  OPENROUTER_MODEL   = anthropic/claude-3.5-haiku  (default)
                       anthropic/claude-3.5-sonnet   (better quality)
                       openai/gpt-4o-mini             (cheaper)

Usage:
  from claude_analyzer import analyze_ad_performance
  result = analyze_ad_performance(metrics_dict)
  # result = {"summary": "...", "winners": [...], "losers": [...], "adjustments": [...]}
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error
from typing import Any

logger = logging.getLogger("pureleven.claude")

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL     = "anthropic/claude-3.5-haiku"   # fast + cheap for daily review

_SYSTEM_PROMPT = """You are a senior performance marketing analyst for Pureleven.com,
an organic spice e-commerce brand in India (budget ₹40,000/month).

You review daily ad performance data and produce actionable recommendations.
Always output valid JSON only — no prose outside the JSON object.

Output format:
{
  "summary": "<2-3 sentence overall assessment>",
  "overall_roas": <float>,
  "health": "healthy | caution | alert",
  "winners": ["<campaign_name>", ...],
  "losers":  ["<campaign_name>", ...],
  "adjustments": [
    {
      "campaign":  "<name>",
      "platform":  "google | meta",
      "action":    "increase_budget | decrease_budget | pause | increase_cpa_target | decrease_cpa_target",
      "percent":   <int, 0 if action=pause>,
      "rationale": "<brief reason>"
    },
    ...
  ],
  "creative_suggestions": ["<suggestion>", ...],
  "audience_recommendations": ["<suggestion>", ...],
  "budget_reallocation": "<optional 1-sentence advice or null>"
}

Rules:
- Only recommend increases if ROAS > 6x for 3+ days or CPA trending down
- Recommend pause if ROAS < 1.5x or CPA > 2x target for 2+ days
- Budget adjustments capped at ±25% per day
- Total daily spend must not exceed ₹950 (₹350 Google, ₹400 Meta, ₹200 recovery)
- Respond ONLY with the JSON object, no markdown fences."""


def analyze_ad_performance(metrics: dict[str, Any]) -> dict[str, Any]:
    """
    Send campaign metrics to Claude and return structured recommendations.

    metrics dict shape (all values optional — include what's available):
    {
      "date": "2026-05-18",
      "google": {
        "HighIntent_Search": {"spend": 142, "conversions": 3, "revenue": 1497, "clicks": 40, "impressions": 2100},
        "Category_Search":   {...},
        "Brand_PureLeven":   {...},
      },
      "meta": {
        "TOF_Video_Cold":        {"spend": 125, "impressions": 8200, "clicks": 82, "purchases": 0, "reach": 6100},
        "ProductViewers_Retarget": {...},
        "CartAbandon_Recovery":   {...},
        "CheckoutRecovery":       {...},
      },
      "crm": {
        "orders_today": 7,
        "recovery_messages_sent": 12,
        "recovery_conversions": 2,
      }
    }
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set — returning mock analysis")
        return _mock_analysis(metrics)

    model = os.getenv("OPENROUTER_MODEL", DEFAULT_MODEL)

    user_message = (
        "Analyze yesterday's Pureleven ad performance and provide recommendations.\n\n"
        f"Campaign metrics:\n{json.dumps(metrics, indent=2, ensure_ascii=False)}"
    )

    # OpenRouter uses OpenAI-compatible chat completions format
    payload = {
        "model":    model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        "max_tokens": 1200,
    }

    body = json.dumps(payload).encode()

    try:
        req = urllib.request.Request(
            OPENROUTER_API_URL,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type":  "application/json",
                "HTTP-Referer":  "https://pureleven.com",
                "X-Title":       "Pureleven AI Ad Review",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="ignore")
        logger.error("OpenRouter API HTTP %d: %s", exc.code, err)
        return {"error": f"OpenRouter API error {exc.code}", "detail": err}
    except Exception as exc:
        logger.error("OpenRouter API call failed: %s", exc)
        return {"error": str(exc)}

    # Extract text from OpenAI-compatible response
    try:
        content = data["choices"][0]["message"]["content"]
        # Strip markdown fences if model wrapped the JSON
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        result = json.loads(content)
        logger.info("OpenRouter analysis complete: model=%s health=%s roas=%s",
                    model, result.get("health"), result.get("overall_roas"))
        return result
    except (KeyError, json.JSONDecodeError) as exc:
        logger.error("OpenRouter response parse error: %s | raw: %s", exc, data)
        return {"error": "parse_error", "raw": str(data)}


def _mock_analysis(metrics: dict) -> dict:
    """Fallback when Claude API key not set — returns sensible defaults."""
    return {
        "summary": "OPENROUTER_API_KEY not configured. Using mock analysis. All campaigns nominal.",
        "overall_roas": 0.0,
        "health": "caution",
        "winners": [],
        "losers":  [],
        "adjustments": [],
        "creative_suggestions": ["Configure CLAUDE_API_KEY to enable AI analysis."],
        "audience_recommendations": [],
        "budget_reallocation": None,
    }
