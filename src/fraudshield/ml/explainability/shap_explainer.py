"""
SHAP-based Explainability Module for FraudShield.
Author: Mudit Bhargava
"""

import logging
from typing import Dict, Any

try:
    import shap
    import pandas as pd
except ImportError:
    pass

logger = logging.getLogger(__name__)

class FraudExplainer:
    """
    Generates human-readable explanations using TreeSHAP to interpret the XGBoost predictions natively.
    """

    def __init__(self, model):
        """
        Initializes the SHAP TreeExplainer mapped securely to the loaded model weights.
        """
        self.model = model
        try:
            self.explainer = shap.TreeExplainer(self.model)
            logger.info("SHAP TreeExplainer natively attached to XGBoost predictor.")
        except Exception as e:
            logger.error("Failed to initialize SHAP constraints: %s", e)
            self.explainer = None

    def explain_transaction(self, feature_vector: Any) -> Dict[str, float]:
        """
        Computes the SHAP values dynamically for a single transaction vector.
        
        Args:
            feature_vector: A Pandas DataFrame representing exactly 1 row of transformed features.
            
        Returns:
            Dict[str, float]: A dictionary mapping each feature name to its structural SHAP contribution.
        """
        if not self.explainer or feature_vector is None or feature_vector.empty:
            return {"Error": "SHAP Explainer uninitialized or empty vector"}
            
        try:
            shap_values = self.explainer.shap_values(feature_vector)
            
            # For XGBoost binary classification, shap_values might be a nested array. 
            # We enforce flattening and mapping directly to the isolated columnar constraints.
            if isinstance(shap_values, list):
                payload_vals = shap_values[1][0]
            else:
                payload_vals = shap_values[0]
                
            explanation = dict(zip(feature_vector.columns, payload_vals))
            
            # Sort by absolute magnitude to expose the top driving factors out-of-the-box
            sorted_explanation = {
                k: round(float(v), 4) 
                for k, v in sorted(explanation.items(), key=lambda item: abs(item[1]), reverse=True)
            }
            return sorted_explanation
            
        except Exception as e:
            logger.error("SHAP matrix calculation dropped: %s", e)
            return {"Error": "Failed generating SHAP outputs"}
