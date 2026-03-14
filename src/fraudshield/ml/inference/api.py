"""
Real-time Inference API for FraudShield models.
Author: Mudit Bhargava
"""

import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import pandas as pd

try:
    from fraudshield.model_training.model_persistence import load_model
except ImportError:
    # Handle local vs global package routing gracefully
    pass

logger = logging.getLogger(__name__)

app = FastAPI(
    title="FraudShield Inference API",
    description="High-frequency real-time fraud prediction and scoring API.",
    version="3.0.0"
)

# Global variables to retain loaded models and prevent reloading latency
_MODEL_CACHE: Dict[str, Any] = {}

class TransactionRequest(BaseModel):
    account_id: str
    transaction_amount: float
    device_id: str
    ip_address: str
    is_international: bool
    is_online: bool
    transaction_time: str
    # Other pre-processed features can go here to simulate pipeline outputs

class FraudScoreResponse(BaseModel):
    transaction_id: str
    fraud_probability: float
    risk_level: str
    action: str

@app.on_event("startup")
def load_assets():
    """
    Pre-loads static machine learning assets into local memory caches.
    Ensures minimum prediction latency natively.
    """
    logger.info("Initializing FraudShield Inference Service - Loading Weights...")
    try:
        # We attempt to load our XGBoost model from the data/models/ repository path natively
        best_model = load_model("data/models", "xgboost")
        if best_model is not None:
            _MODEL_CACHE['predictor'] = best_model
            logger.info("XGBoost weights successfully bound to inference cache.")
        else:
            logger.warning("Failed to locate pre-trained XGBoost weights. Inference will run dry.")
    except Exception as e:
        logger.error("Error during model initialization lookup: %s", e)

@app.post("/predict", response_model=FraudScoreResponse)
def predict_fraud(transaction: TransactionRequest):
    """
    Evaluates a single transaction dictionary mapping against trained XGBoost trees.
    """
    # 1. Transform raw payload
    # In a full deployment, this calls `feature_engineering` to synthesize `amount_rolling_sum`, `graph_score`, etc.
    feature_vector = pd.DataFrame([{
        "transaction_amount": transaction.transaction_amount,
        "is_international": int(transaction.is_international),
        "is_online": int(transaction.is_online),
        # dummy values mapped for baseline structural tests
        "num_transactions_1h": 1,
        "amount_rolling_sum_1h": transaction.transaction_amount,
        "rolling_amount_std": 0.0,
        "target": 0 # to satisfy column alignment if necessary
    }])
    
    predictor = _MODEL_CACHE.get('predictor')
    
    if predictor is None:
        # Mock prediction logic evaluating high-level rules if ML weights aren't cached natively
        prob = 0.85 if transaction.transaction_amount > 4000 else 0.05
    else:
        try:
            # Drop target and run inference
            features = feature_vector.drop("target", axis=1, errors="ignore")
            # Forxgboost this expects aligned column mappings
            prob_batch = predictor.predict_proba(features)
            prob = float(prob_batch[0][1])
        except Exception as e:
            logger.error("Prediction matrix failed: %s", e)
            raise HTTPException(status_code=500, detail="Inference failure")
    
    # 2. Derive Rule constraints
    risk_level = "HIGH" if prob >= 0.75 else ("MEDIUM" if prob >= 0.4 else "LOW")
    action = "BLOCK" if risk_level == "HIGH" else "ALLOW"
    
    return FraudScoreResponse(
        transaction_id="TX_REQ_001",
        fraud_probability=prob,
        risk_level=risk_level,
        action=action
    )

@app.get("/health")
def health_check():
    """Returns endpoint liveness probes securely."""
    return {"status": "healthy", "model_loaded": 'predictor' in _MODEL_CACHE}

if __name__ == "__main__":
    import uvicorn
    # Standalone execution wrapper natively exposing port 8000
    uvicorn.run("fraudshield.ml.inference.api:app", host="0.0.0.0", port=8000, reload=True)
