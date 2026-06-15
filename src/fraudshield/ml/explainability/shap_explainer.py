"""
SHAP-based Explainability Module for FraudShield.
Author: Mudit Bhargava
"""

import logging
from typing import Any, Dict

try:
    import shap
except ImportError:
    shap = None

logger = logging.getLogger(__name__)


class FraudExplainer:
    """
    Generates human-readable explanations using TreeSHAP to interpret the XGBoost predictions natively.
    """

    def __init__(self, model):
        """
        Initializes the explainer using XGBoost's native pred_contribs if available,
        or falls back to SHAP TreeExplainer for other models like Random Forest.
        """
        self.model = model
        self.is_xgboost = hasattr(model, "get_booster")
        self.explainer = None

        if not self.is_xgboost:
            if shap is None or model is None:
                return
            try:
                self.explainer = shap.TreeExplainer(self.model)
                logger.info("SHAP TreeExplainer natively attached to model.")
            except Exception as e:
                logger.error("Failed to initialize SHAP constraints: %s", e)
                self.explainer = None
        else:
            logger.info("XGBoost model detected, using native pred_contribs for explanations.")

    def explain_transaction(self, feature_vector: Any) -> Dict[str, Any]:
        """
        Computes the SHAP values dynamically for a single transaction vector.

        Args:
            feature_vector: A Pandas DataFrame representing exactly 1 row of transformed features.

        Returns:
            Dict[str, Any]: A dictionary mapping each feature name to its SHAP contribution, or error message.
        """
        if feature_vector is None or feature_vector.empty:
            return {"Error": "Empty feature vector"}

        try:
            if self.is_xgboost:
                import xgboost as xgb
                dmatrix = xgb.DMatrix(feature_vector)
                booster = self.model.get_booster()
                contribs = booster.predict(dmatrix, pred_contribs=True)
                payload_vals = contribs[0][:-1]
            else:
                if not self.explainer:
                    return {"Error": "SHAP Explainer uninitialized"}
                shap_values = self.explainer.shap_values(feature_vector)
                if isinstance(shap_values, list):
                    payload_vals = shap_values[1][0]
                else:
                    payload_vals = shap_values[0] if getattr(shap_values, "ndim", 1) > 1 else shap_values

            explanation = dict(zip(feature_vector.columns, payload_vals))
            sorted_explanation = {k: round(float(v), 4) for k, v in sorted(explanation.items(), key=lambda item: abs(item[1]), reverse=True)}
            return sorted_explanation

        except Exception as e:
            logger.error("SHAP matrix calculation dropped: %s", e)
            return {"Error": str(e)}
