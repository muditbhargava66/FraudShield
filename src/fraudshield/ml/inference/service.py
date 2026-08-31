"""
Inference service that keeps preprocessing, model loading, and streaming features aligned.
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

import pandas as pd

from fraudshield.config.settings import RuntimeSettings, get_settings
from fraudshield.feature_engineering.stateful_aggregates import StatefulFeatureStore
from fraudshield.ml.explainability.shap_explainer import FraudExplainer
from fraudshield.runtime.resources import InferenceArtifacts, load_inference_artifacts

try:
    from fraudshield.monitoring.metrics import get_metrics
except ImportError:  # pragma: no cover - optional monitoring

    def get_metrics():  # type: ignore[misc]
        return None

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
        start = time.perf_counter()
        normalized = self._normalize_payload(payload)
        raw_features = self._build_feature_frame(normalized)
        if not self.artifacts:
            probability = self._heuristic_probability(normalized)
            result = PredictionResult(
                transaction_id=normalized["transaction_id"],
                fraud_probability=probability,
                model_name=self.model_name,
                model_loaded=False,
                source="rules_fallback",
                features=raw_features,
            )
            latency = time.perf_counter() - start
            _record_metrics(result, latency)
            return result

        transformed = self.artifacts.preprocessor.transform(raw_features)
        if hasattr(self.artifacts.model, "predict_proba"):
            probability = float(self.artifacts.model.predict_proba(transformed)[0][1])
        else:
            probability = float(self.artifacts.model.predict(transformed)[0])
        result = PredictionResult(
            transaction_id=normalized["transaction_id"],
            fraud_probability=probability,
            model_name=self.model_name,
            model_loaded=True,
            source="trained_model",
            features=self._transformed_feature_frame(transformed),
        )
        latency = time.perf_counter() - start
        _record_metrics(result, latency)
        return result

    def explain(self, prediction: PredictionResult) -> Dict[str, Any]:
        if not self.explainer or prediction.features.empty:
            return {"Error": "SHAP Explainer uninitialized or empty vector"}
        return self.explainer.explain_transaction(prediction.features)

    def _transformed_feature_frame(self, transformed: Any) -> pd.DataFrame:
        """Return the exact feature matrix used by the fitted estimator for SHAP."""
        if hasattr(transformed, "toarray"):
            transformed = transformed.toarray()
        columns = self.artifacts.transformed_feature_names if self.artifacts else []
        if not columns:
            columns = [f"feature_{index}" for index in range(transformed.shape[1])]
        return pd.DataFrame(transformed, columns=columns)

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
            # None (not pd.NA) so sklearn's imputer receives NaN-compatible values.
            prepared[column] = record.get(column, None)
        return pd.DataFrame([prepared], columns=self.artifacts.input_feature_columns)

    def normalize_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize an inbound transaction payload for feature building."""
        return self._normalize_payload(payload)

    @staticmethod
    def _normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        normalized = dict(payload)
        normalized["transaction_id"] = normalized.get("transaction_id") or f"TX_{uuid.uuid4().hex[:12]}"
        normalized["user_id"] = normalized.get("user_id") or normalized.get("account_id")
        amount = normalized.get("amount")
        if amount is None:
            amount = normalized.get("transaction_amount")
        normalized["amount"] = float(amount if amount is not None else 0.0)
        normalized["transaction_date"] = (
            normalized.get("transaction_date") or normalized.get("transaction_time") or pd.Timestamp.now(tz="UTC")
        )
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


def _record_metrics(result: PredictionResult, latency: float) -> None:
    """Record prediction metrics if monitoring is available."""
    collector = get_metrics()
    if collector is not None:
        try:
            collector.record_prediction(result, latency)
        except Exception:  # pragma: no cover - defensive
            pass
