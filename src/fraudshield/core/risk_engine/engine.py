"""
Hybrid Risk Scoring Engine blending Graph, ML, and Rule signals.
Author: Mudit Bhargava
"""

import logging
import math
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def extract_account_id(payload: Dict[str, Any]) -> str:
    """Return the account key consistently across API and stream processors."""
    return str(payload.get("account_id") or payload.get("user_id") or payload.get("transaction_id", ""))


def count_rule_breaches(payload: Dict[str, Any]) -> int:
    """Apply the same deterministic transaction rules in every entry point."""
    try:
        amount = float(payload.get("amount") or payload.get("transaction_amount") or 0.0)
    except (TypeError, ValueError):
        amount = 0.0

    def as_bool(value: Any, default: bool = False) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "on"}
        if value is None:
            return default
        return bool(value)

    return sum(
        (
            amount >= 4000,
            as_bool(payload.get("is_international")),
            not as_bool(payload.get("is_online"), default=True),
        )
    )


class HybridRiskEngine:
    """
    Consolidates isolated Machine Learning predictions, Graph traversal anomalies, and
    static Rule bounds into a single cohesive fraud probability vector.
    """

    def __init__(
        self,
        ml_weight: float = 0.6,
        graph_weight: float = 0.3,
        rule_weight: float = 0.1,
        ring_detector: Optional[Any] = None,
    ):
        """
        Initializes the scaling vectors dynamically.
        """
        weights = (float(ml_weight), float(graph_weight), float(rule_weight))
        if any(not math.isfinite(weight) or weight < 0 for weight in weights):
            raise ValueError("Risk engine weights must be finite, non-negative values.")
        # fsum, not sum: CPython 3.12 switched sum() to Neumaier summation, so
        # sum((0.6, 0.3, 0.1)) is 1.0 there but 0.9999999999999999 on 3.10/3.11,
        # which shifted every normalized weight by one ulp depending on the runtime.
        total = math.fsum(weights)
        if total <= 0:
            raise ValueError("At least one risk engine weight must be greater than zero.")
        self.ml_weight, self.graph_weight, self.rule_weight = (weight / total for weight in weights)
        self.ring_detector = ring_detector

        # Normalize a valid custom vector so every composite score remains bounded.
        if abs(total - 1.0) > 1e-4:
            logger.warning("Risk engine weights summed to %.4f and were normalized.", total)

    def evaluate_transaction(
        self,
        ml_score: float,
        graph_score: float,
        rules_breached: int,
        max_rules: int = 3,
        account_id: str = "",
    ) -> Dict[str, Any]:
        """
        Calculates the unified compound hybrid risk evaluating streaming components natively.

        Args:
            ml_score (float): XGBoost Probability (0.0 to 1.0)
            graph_score (float): Neo4j PageRank / Connectedness anomaly factor (0.0 to 1.0)
            rules_breached (int): Hard rules violated sequentially inside streaming loop.
            max_rules (int): Maximum possible rules for scaling (three built-in rules).
            account_id (str): Account identifier for optional ring detection.

        Returns:
            Dict: The structured final compound fraud score mapping.
        """
        ml_score = self._bounded_score(ml_score, "ml_score")
        graph_score = self._bounded_score(graph_score, "graph_score")
        if max_rules <= 0:
            raise ValueError("max_rules must be greater than zero.")
        rules_breached = max(0, int(rules_breached))

        # Blend ring score into graph_score when ring detector is available
        if self.ring_detector is not None and account_id:
            try:
                ring_score = self.ring_detector.assess_account(account_id)
                graph_score = max(graph_score, self._bounded_score(ring_score, "ring_score"))
            except Exception as exc:
                logger.warning("Ring detection failed for account %s: %s", account_id, exc)

        # Linear scaling for rule breaches explicitly
        rule_score = min(float(rules_breached) / float(max_rules), 1.0)

        # Generate composite vector
        compound_score = (ml_score * self.ml_weight) + (graph_score * self.graph_weight) + (rule_score * self.rule_weight)

        # Override critical thresholds: all rules broke or graph indicates a distinct ring.
        if rules_breached >= max_rules or graph_score >= 0.95:
            compound_score = max(compound_score, 0.95)

        risk_level = "HIGH" if compound_score >= 0.75 else ("MEDIUM" if compound_score >= 0.40 else "LOW")

        return {
            "composite_fraud_score": round(compound_score, 4),
            "ml_contribution": round(ml_score, 4),
            "graph_contribution": round(graph_score, 4),
            "rule_contribution": round(rule_score, 4),
            "assigned_risk_level": risk_level,
            "action": "BLOCK" if risk_level == "HIGH" else "ALLOW",
        }

    @staticmethod
    def _bounded_score(value: float, name: str) -> float:
        try:
            score = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be numeric.") from exc
        if not math.isfinite(score):
            raise ValueError(f"{name} must be finite.")
        return min(max(score, 0.0), 1.0)
