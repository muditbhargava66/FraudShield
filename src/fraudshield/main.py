"""
FraudShield real-time orchestration pipeline.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional

from fraudshield.config.settings import RuntimeSettings, get_settings
from fraudshield.core.risk_engine.engine import HybridRiskEngine
from fraudshield.graph.graph_builder.builder import FraudGraphBuilder
from fraudshield.ml.inference.service import FraudInferenceService
from fraudshield.runtime.logging import configure_logging

logger = logging.getLogger(__name__)


class RealTimeOrchestrator:
    def __init__(
        self,
        settings: Optional[RuntimeSettings] = None,
        *,
        producer=None,
        consumer=None,
        graph_builder=None,
        inference_service=None,
        risk_engine=None,
    ):
        self.settings = settings or get_settings()
        configure_logging(self.settings, component="realtime")
        logger.info("Initializing FraudShield Real-Time Pipeline...")
        self.risk_engine = risk_engine or HybridRiskEngine(ml_weight=0.6, graph_weight=0.25, rule_weight=0.15)
        self.inference_service = inference_service or FraudInferenceService(self.settings)
        self.graph_builder = graph_builder or FraudGraphBuilder(self.settings)
        if producer is None or consumer is None:
            from fraudshield.streaming.kafka_consumer import TransactionConsumer
            from fraudshield.streaming.transaction_producer import TransactionProducer

            self.producer = producer or TransactionProducer(settings=self.settings)
            self.consumer = consumer or TransactionConsumer(settings=self.settings)
        else:
            self.producer = producer
            self.consumer = consumer

    def _rule_breaches(self, payload: Dict[str, Any]) -> int:
        amount = float(payload.get("amount", 0.0) or 0.0)
        breaches = 0
        breaches += int(amount >= 4000)
        breaches += int(bool(payload.get("is_international")))
        breaches += int(not bool(payload.get("is_online", True)))
        breaches += int(bool(payload.get("known_fraud")))
        return breaches

    def process_transaction(self, payload: Dict[str, Any]):
        tx_id = payload.get("transaction_id", "UNKNOWN")
        amount = payload.get("amount") or payload.get("transaction_amount") or 0.0
        logger.info("PROCESSING --> tx_id: %s | amount: $%s", tx_id, amount)

        prediction = self.inference_service.predict(payload)
        graph_score = self.graph_builder.graph_risk(payload)
        self.graph_builder.add_transaction(payload)
        assessment = self.risk_engine.evaluate_transaction(
            ml_score=prediction.fraud_probability,
            graph_score=graph_score,
            rules_breached=self._rule_breaches(payload),
        )

        if assessment["assigned_risk_level"] == "HIGH" and self.inference_service.model_loaded:
            explanation = self.inference_service.explain(prediction)
            logger.warning(
                "HIGH RISK DETECTED [%s]: %s | SHAP: %s",
                assessment["composite_fraud_score"],
                assessment["action"],
                explanation,
            )
        else:
            logger.info("RISK %s [%s]: %s", assessment["assigned_risk_level"], assessment["composite_fraud_score"], assessment["action"])
        return assessment

    def run_pipeline(self, transactions_per_second: int = 2):
        producer_thread = threading.Thread(
            target=self.producer.start_streaming,
            kwargs={"transactions_per_second": transactions_per_second},
            daemon=True,
        )
        producer_thread.start()

        logger.info("Pipeline Orchestrator engaged. Awaiting real-time influx...")
        try:
            self.consumer.start_consuming(self.process_transaction)
        except KeyboardInterrupt:
            logger.info("Pipeline shutdown gracefully.")
        finally:
            self.close()

    def close(self) -> None:
        try:
            self.graph_builder.close()
        finally:
            if hasattr(self.consumer, "close"):
                self.consumer.close()
            if hasattr(self.producer, "close"):
                self.producer.close()


if __name__ == "__main__":
    app = RealTimeOrchestrator()
    app.run_pipeline()
