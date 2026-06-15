"""
Inference service that keeps preprocessing, model loading, and streaming features aligned.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

import pandas as pd

from fraudshield.config.settings import RuntimeSettings, get_settings
from fraudshield.feature_engineering.stateful_aggregates import StatefulFeatureStore
from fraudshield.ml.explainability.shap_explainer import FraudExplainer
from fraudshield.runtime.resources import InferenceArtifacts, load_inference_artifacts

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    transaction_id: str
    fraud_probability: float
    model_name: str
    model_loaded: bool
    source: str
    features: pd.DataFrame


class FraudInferenceService:
    def __init__(
        self,
        settings: Optional[RuntimeSettings] = None,
        model_name: Optional[str] = None,
        artifacts: Optional[InferenceArtifacts] = None,
        feature_store: Optional[StatefulFeatureStore] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.model_name = model_name or self.settings.models.default_model_name
        self.artifacts: Optional[InferenceArtifacts] = artifacts
        self.feature_store = feature_store
        self.explainer: Optional[FraudExplainer] = None
        if self.artifacts is None:
            self._load_artifacts()
        if self.feature_store is None:
            windows = self.artifacts.metadata.get("feature_windows", []) if self.artifacts else []
            self.feature_store = StatefulFeatureStore(windows=windows)
        if self.artifacts:
            self.explainer = FraudExplainer(self.artifacts.model)

    @property
    def model_loaded(self) -> bool:
        return self.artifacts is not None

    def _load_artifacts(self) -> None:
        try:
            self.artifacts = load_inference_artifacts(self.settings.models, self.model_name)
            logger.info("Loaded inference artifacts for model %s", self.model_name)
        except Exception as exc:
            logger.warning("Failed to load inference artifacts for %s: %s", self.model_name, exc)
            self.artifacts = None

    def predict(self, payload: Dict[str, Any]) -> PredictionResult:
        normalized = self._normalize_payload(payload)
        features = self._build_feature_frame(normalized)
        if not self.artifacts:
            probability = self._heuristic_probability(normalized)
            return PredictionResult(
                transaction_id=normalized["transaction_id"],
                fraud_probability=probability,
                model_name=self.model_name,
                model_loaded=False,
                source="rules_fallback",
                features=features,
            )

        transformed = self.artifacts.preprocessor.transform(features)
        if hasattr(self.artifacts.model, "predict_proba"):
            probability = float(self.artifacts.model.predict_proba(transformed)[0][1])
        else:
            probability = float(self.artifacts.model.predict(transformed)[0])
        return PredictionResult(
            transaction_id=normalized["transaction_id"],
            fraud_probability=probability,
            model_name=self.model_name,
            model_loaded=True,
            source="trained_model",
            features=features,
        )

    def explain(self, prediction: PredictionResult) -> Dict[str, Any]:
        if not self.explainer or prediction.features.empty:
            return {"Error": "SHAP Explainer uninitialized or empty vector"}
        return self.explainer.explain_transaction(prediction.features)

    def _build_feature_frame(self, payload: Dict[str, Any]) -> pd.DataFrame:
        if self.feature_store is None:
            derived_features: Dict[str, Any] = {}
        else:
            derived_features = self.feature_store.build_features(payload)
        record = {**payload, **derived_features}
        if not self.artifacts:
            return pd.DataFrame([record])

        prepared = {}
        for column in self.artifacts.input_feature_columns:
            prepared[column] = record.get(column, pd.NA)
        return pd.DataFrame([prepared], columns=self.artifacts.input_feature_columns)

    @staticmethod
    def _normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(payload)
        normalized["transaction_id"] = normalized.get("transaction_id") or f"TX_{uuid.uuid4().hex[:12]}"
        normalized["user_id"] = normalized.get("user_id") or normalized.get("account_id")
        normalized["amount"] = float(normalized.get("amount") or normalized.get("transaction_amount") or 0.0)
        normalized["transaction_date"] = normalized.get("transaction_date") or normalized.get("transaction_time") or pd.Timestamp.utcnow()
        normalized["currency"] = normalized.get("currency", "USD")
        normalized["status"] = normalized.get("status", "posted")
        normalized["is_international"] = bool(normalized.get("is_international", False))
        normalized["is_online"] = bool(normalized.get("is_online", True))
        return normalized

    @staticmethod
    def _heuristic_probability(payload: Dict[str, Any]) -> float:
        probability = 0.05
        if payload["amount"] >= 4000:
            probability += 0.55
        if payload.get("is_international"):
            probability += 0.2
        if payload.get("is_online"):
            probability += 0.05
        return min(probability, 0.99)
