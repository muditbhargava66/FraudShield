"""
Real-time Inference API for FraudShield models.
Author: Mudit Bhargava
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from fraudshield.config.settings import RuntimeSettings, get_settings
from fraudshield.ml.inference.service import FraudInferenceService
from fraudshield.runtime.logging import configure_logging

logger = logging.getLogger(__name__)


class TransactionRequest(BaseModel):
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
    known_fraud: Optional[int] = Field(default=None, ge=0, le=1)

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


def _risk_level(probability: float) -> str:
    if probability >= 0.75:
        return "HIGH"
    if probability >= 0.4:
        return "MEDIUM"
    return "LOW"


def create_app(settings: Optional[RuntimeSettings] = None) -> FastAPI:
    resolved_settings = settings or get_settings()
    configure_logging(resolved_settings, component="api")

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.settings = resolved_settings
        app.state.inference_service = FraudInferenceService(resolved_settings)
        yield

    app = FastAPI(
        title="FraudShield Inference API",
        description="High-frequency real-time fraud prediction and scoring API.",
        version="3.0.0",
        lifespan=lifespan,
    )

    @app.post("/predict", response_model=FraudScoreResponse)
    def predict_fraud(transaction: TransactionRequest, request: Request):
        service: FraudInferenceService = request.app.state.inference_service
        try:
            prediction = service.predict(transaction.to_event())
        except Exception as exc:
            logger.error("Prediction matrix failed: %s", exc)
            raise HTTPException(status_code=500, detail="Inference failure") from exc

        risk_level = _risk_level(prediction.fraud_probability)
        return FraudScoreResponse(
            transaction_id=prediction.transaction_id,
            fraud_probability=prediction.fraud_probability,
            risk_level=risk_level,
            action="BLOCK" if risk_level == "HIGH" else "ALLOW",
            model_loaded=prediction.model_loaded,
            source=prediction.source,
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
