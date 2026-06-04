"""
app/services/statistical_analysis_service.py

Statistical significance testing for A/B experiments.

Implements:
  - Chi-square test for proportion comparison (conversion rates)
  - Z-test for proportions (large samples)
  - Returns p-value, confidence interval, effect size (Cohen's h), winner

Usage:
    from app.services.statistical_analysis_service import StatisticalAnalysisService
    svc = StatisticalAnalysisService()
    result = svc.test_variants([
        {"name": "control", "assigned": 500, "converted": 45},
        {"name": "variant_a", "assigned": 490, "converted": 62},
    ])
"""

from __future__ import annotations

import math
import logging
from typing import Any

logger = logging.getLogger(__name__)

SIGNIFICANCE_THRESHOLD = 0.05   # 95% confidence
MIN_SAMPLE_SIZE        = 30     # Below this, results are unreliable


class StatisticalAnalysisService:

    def test_variants(self, variants: list[dict[str, Any]]) -> dict[str, Any]:
        """
        Compare all variants and return statistical results.

        Each variant dict must have: name, assigned, converted.
        Returns: {
            variants: [...enriched with rate, uplift, z_score, p_value, ci],
            winner: str | None,
            is_significant: bool,
            confidence: float,
            sample_adequate: bool,
            recommendation: str,
        }
        """
        if len(variants) < 2:
            return self._insufficient("Need at least 2 variants")

        # Enrich each variant
        enriched = []
        for v in variants:
            n = int(v.get("assigned") or 0)
            c = int(v.get("converted") or 0)
            rate = c / n if n > 0 else 0.0
            enriched.append({
                "name":          v.get("name", "unknown"),
                "assigned":      n,
                "converted":     c,
                "conversion_rate": round(rate * 100, 4),
            })

        # Need at least one adequate sample
        min_n = min(v["assigned"] for v in enriched)
        sample_adequate = min_n >= MIN_SAMPLE_SIZE

        # Control = first variant
        control = enriched[0]
        control_rate = control["converted"] / max(control["assigned"], 1)

        winner = None
        best_p = 1.0
        best_variant = None

        for v in enriched[1:]:
            test_rate = v["converted"] / max(v["assigned"], 1)

            z, p, ci = self._two_proportion_z_test(
                n1=control["assigned"], c1=control["converted"],
                n2=v["assigned"],      c2=v["converted"],
            )
            effect = self._cohens_h(control_rate, test_rate)
            uplift = ((test_rate - control_rate) / max(control_rate, 0.0001)) * 100

            v["z_score"]            = round(z, 4)
            v["p_value"]            = round(p, 6)
            v["confidence_interval"] = [round(ci[0] * 100, 4), round(ci[1] * 100, 4)]
            v["effect_size"]        = round(effect, 4)
            v["uplift_pct"]         = round(uplift, 2)
            v["is_significant"]     = p < SIGNIFICANCE_THRESHOLD

            if p < best_p and p < SIGNIFICANCE_THRESHOLD and uplift > 0:
                best_p = p
                best_variant = v

        # Mark control
        control["z_score"]            = 0.0
        control["p_value"]            = 1.0
        control["confidence_interval"] = [0.0, 0.0]
        control["effect_size"]        = 0.0
        control["uplift_pct"]         = 0.0
        control["is_significant"]     = False

        if best_variant:
            winner = best_variant["name"]

        recommendation = self._recommendation(winner, best_variant, sample_adequate)

        return {
            "variants":        enriched,
            "winner":          winner,
            "is_significant":  winner is not None,
            "confidence":      round((1 - min(best_p, 1.0)) * 100, 2),
            "sample_adequate": sample_adequate,
            "min_sample_size": MIN_SAMPLE_SIZE,
            "recommendation":  recommendation,
        }

    def _two_proportion_z_test(
        self,
        n1: int, c1: int,
        n2: int, c2: int,
    ) -> tuple[float, float, tuple[float, float]]:
        """
        Two-proportion z-test.
        Returns (z_score, p_value, 95% CI for difference in rates).
        """
        if n1 == 0 or n2 == 0:
            return 0.0, 1.0, (0.0, 0.0)

        p1 = c1 / n1
        p2 = c2 / n2
        p_pool = (c1 + c2) / (n1 + n2)

        se_pool = math.sqrt(p_pool * (1 - p_pool) * (1 / n1 + 1 / n2))
        if se_pool == 0:
            return 0.0, 1.0, (0.0, 0.0)

        z = (p2 - p1) / se_pool
        p_value = 2 * (1 - self._norm_cdf(abs(z)))  # two-tailed

        # 95% CI for difference p2 - p1
        se_diff = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
        ci_low  = (p2 - p1) - 1.96 * se_diff
        ci_high = (p2 - p1) + 1.96 * se_diff

        return z, p_value, (ci_low, ci_high)

    def _norm_cdf(self, z: float) -> float:
        """Standard normal CDF via erfc approximation."""
        return 0.5 * math.erfc(-z / math.sqrt(2))

    def _cohens_h(self, p1: float, p2: float) -> float:
        """Effect size for two proportions (Cohen's h)."""
        try:
            phi1 = 2 * math.asin(math.sqrt(max(p1, 0)))
            phi2 = 2 * math.asin(math.sqrt(max(p2, 0)))
            return phi2 - phi1
        except (ValueError, ZeroDivisionError):
            return 0.0

    def _recommendation(
        self,
        winner: str | None,
        best: dict[str, Any] | None,
        sample_adequate: bool,
    ) -> str:
        if not sample_adequate:
            return f"Continue test — minimum {MIN_SAMPLE_SIZE} participants per variant needed"
        if not winner:
            return "No significant winner yet. Continue the experiment or redesign variants."
        uplift = best["uplift_pct"] if best else 0
        effect = abs(best["effect_size"]) if best else 0
        if effect < 0.2:
            return f"{winner} wins but effect is small ({uplift:+.1f}%). Consider whether the difference is practically meaningful."
        return f"Deploy {winner}: {uplift:+.1f}% conversion uplift (statistically significant at 95% confidence)."

    def _insufficient(self, reason: str) -> dict[str, Any]:
        return {
            "variants":        [],
            "winner":          None,
            "is_significant":  False,
            "confidence":      0.0,
            "sample_adequate": False,
            "recommendation":  reason,
        }
