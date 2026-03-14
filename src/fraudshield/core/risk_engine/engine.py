"""
Hybrid Risk Scoring Engine blending Graph, ML, and Rule signals.
Author: Mudit Bhargava
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

class HybridRiskEngine:
    """
    Consolidates isolated Machine Learning predictions, Graph traversal anomalies, and
    static Rule bounds into a single cohesive fraud probability vector.
    """
    
    def __init__(self, 
                 ml_weight: float = 0.6, 
                 graph_weight: float = 0.3, 
                 rule_weight: float = 0.1):
        """
        Initializes the scaling vectors dynamically.
        """
        self.ml_weight = ml_weight
        self.graph_weight = graph_weight
        self.rule_weight = rule_weight
        
        # Ensure scaling architecture resolves cleanly to 1.0 structurally
        total = ml_weight + graph_weight + rule_weight
        if abs(total - 1.0) > 1e-4:
            logger.warning("Risk Engine weights do not perfectly sum to 1.0 (Sum: %.2f)", total)

    def evaluate_transaction(self, 
                             ml_score: float, 
                             graph_score: float, 
                             rules_breached: int,
                             max_rules: int = 5) -> Dict[str, Any]:
        """
        Calculates the unified compound hybrid risk evaluating streaming components natively.
        
        Args:
            ml_score (float): XGBoost Probability (0.0 to 1.0)
            graph_score (float): Neo4j PageRank / Connectedness anomaly factor (0.0 to 1.0)
            rules_breached (int): Hard rules violated sequentially inside streaming loop.
            max_rules (int): Maximum possible rules for scaling.
            
        Returns:
            Dict: The structured final compound fraud score mapping.
        """
        # Linear scaling for rule breaches explicitly
        rule_score = min(float(rules_breached) / float(max_rules), 1.0)
        
        # Generate composite vector
        compound_score = (
            (ml_score * self.ml_weight) + 
            (graph_score * self.graph_weight) + 
            (rule_score * self.rule_weight)
        )
        
        # Override critical thresholds: If 4+ rules break OR graph indicates distinct ring
        if rules_breached >= 4 or graph_score >= 0.95:
            compound_score = max(compound_score, 0.95)
            
        risk_level = "HIGH" if compound_score >= 0.75 else ("MEDIUM" if compound_score >= 0.40 else "LOW")
        
        return {
            "composite_fraud_score": round(compound_score, 4),
            "ml_contribution": round(ml_score, 4),
            "graph_contribution": round(graph_score, 4),
            "rule_contribution": round(rule_score, 4),
            "assigned_risk_level": risk_level,
            "action": "BLOCK" if risk_level == "HIGH" else "ALLOW"
        }
