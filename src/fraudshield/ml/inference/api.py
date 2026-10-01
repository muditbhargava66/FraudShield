"""
Real-time Inference API for FraudShield models.
Author: Mudit Bhargava
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, ConfigDict

from fraudshield.config.settings import RuntimeSettings, get_settings
from fraudshield.core.risk_engine.engine import HybridRiskEngine, count_rule_breaches, extract_account_id
from fraudshield.graph.graph_builder.builder import FraudGraphBuilder
from fraudshield.ml.inference.service import FraudInferenceService
from fraudshield.monitoring.metrics import get_metrics
from fraudshield.runtime.logging import configure_logging

logger = logging.getLogger(__name__)


class TransactionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: Optional[str] = None
    user_id: Optional[str] = None
    account_id: Optional[str] = None
    merchant_id: Optional[str] = None
    amount: Optional[float] = None
    transaction_amount: Optional[float] = None
    device_id: Optional[str] = None
    ip_address: Optional[str] = None
    is_international: bool = False
    is_online: bool = True
    transaction_date: Optional[str] = None
    transaction_time: Optional[str] = None
    currency: str = "USD"
    status: str = "posted"

    def to_event(self) -> Dict[str, Any]:
        dump = self.model_dump() if hasattr(self, "model_dump") else self.dict()
        return dump


class FraudScoreResponse(BaseModel):
    transaction_id: str
    fraud_probability: float
    risk_level: str
    action: str
    model_loaded: bool
    source: str
    explanation: Optional[Dict[str, float]] = None


def _top_explanation_factors(raw: Dict[str, Any], limit: int = 5) -> Optional[Dict[str, float]]:
    """Trim the abs-sorted SHAP mapping to the strongest factors; None when unavailable."""
    if not raw or "Error" in raw:
        return None
    return {name: float(value) for name, value in list(raw.items())[:limit]}


def create_app(settings: Optional[RuntimeSettings] = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings, component="api")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = resolved_settings
        app.state.inference_service = FraudInferenceService(resolved_settings)
        app.state.graph_builder = FraudGraphBuilder(resolved_settings)
        app.state.risk_engine = HybridRiskEngine(
            ml_weight=0.6,
            graph_weight=0.3,
            rule_weight=0.1,
            ring_detector=app.state.graph_builder.ring_detector,
        )
        try:
            yield
        finally:
            app.state.graph_builder.close()

    app = FastAPI(
        title="FraudShield Inference API",
        description="High-frequency real-time fraud prediction and scoring API.",
        version="3.0.0",
        lifespan=lifespan,
    )
    if resolved_settings.monitoring.enabled:
        metrics = get_metrics()
        metrics_app = metrics.asgi_app()
        if metrics_app is not None:
            app.mount(resolved_settings.monitoring.metrics_path, metrics_app)

    @app.post("/predict", response_model=FraudScoreResponse)
    def predict_fraud(transaction: TransactionRequest, request: Request):
        service: FraudInferenceService = request.app.state.inference_service
        try:
            payload = service.normalize_payload(transaction.to_event())
            prediction = service.predict(payload)
            graph_builder: FraudGraphBuilder = request.app.state.graph_builder
            risk_engine: HybridRiskEngine = request.app.state.risk_engine
            graph_score = graph_builder.graph_risk(payload)
            graph_builder.add_transaction(payload)
            assessment = risk_engine.evaluate_transaction(
                ml_score=prediction.fraud_probability,
                graph_score=graph_score,
                rules_breached=count_rule_breaches(payload),
                account_id=extract_account_id(payload),
            )
        except Exception as exc:
            logger.error("Prediction matrix failed: %s", exc)
            raise HTTPException(status_code=500, detail="Inference failure") from exc

        return FraudScoreResponse(
            transaction_id=prediction.transaction_id,
            fraud_probability=prediction.fraud_probability,
            risk_level=assessment["assigned_risk_level"],
            action=assessment["action"],
            model_loaded=prediction.model_loaded,
            source=prediction.source,
            explanation=_top_explanation_factors(service.explain(prediction)),
        )

    @app.get("/health")
    def health_check(request: Request):
        service: FraudInferenceService = request.app.state.inference_service
        return {
            "status": "healthy",
            "model_loaded": service.model_loaded,
            "model_name": service.model_name,
        }

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("fraudshield.ml.inference.api:app", host="0.0.0.0", port=8000, reload=True)
