"""
FraudShield real-time orchestration pipeline (v3.0.0).

Integrates:
- Kafka/Redpanda streaming via broker abstraction
- Neo4j graph builder with fraud ring detection
- Hybrid risk engine with optional ring score blending
- Prometheus metrics for transactions, latency, and drift
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Dict, Optional

from fraudshield.config.settings import RuntimeSettings, get_settings
from fraudshield.core.risk_engine.engine import HybridRiskEngine, count_rule_breaches, extract_account_id
from fraudshield.graph.graph_builder.builder import FraudGraphBuilder
from fraudshield.ml.inference.service import FraudInferenceService
from fraudshield.runtime.logging import configure_logging

logger = logging.getLogger(__name__)

# Optional v3.0.0 imports with graceful degradation
try:
    from fraudshield.monitoring.metrics import get_metrics
except ImportError:  # pragma: no cover

    def get_metrics():  # type: ignore[misc]
        return None


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
        logger.info("Initializing FraudShield v3.0.0 Real-Time Pipeline...")

        # --- Graph builder (may hold ring_detector if Neo4j is available) ---
        self.graph_builder = graph_builder or FraudGraphBuilder(self.settings)

        # --- Risk engine with ring detector integration ---
        ring_detector = getattr(self.graph_builder, "ring_detector", None)
        if risk_engine is not None:
            self.risk_engine = risk_engine
        else:
            self.risk_engine = HybridRiskEngine(
                ml_weight=0.6,
                graph_weight=0.3,
                rule_weight=0.1,
                ring_detector=ring_detector,
            )

        # --- Inference service ---
        self.inference_service = inference_service or FraudInferenceService(self.settings)

        # --- Streaming producer/consumer ---
        if producer is None or consumer is None:
            from fraudshield.streaming.kafka_consumer import TransactionConsumer
            from fraudshield.streaming.transaction_producer import TransactionProducer

            self.producer = producer or TransactionProducer(settings=self.settings)
            self.consumer = consumer or TransactionConsumer(settings=self.settings)
        else:
            self.producer = producer
            self.consumer = consumer

        # --- Start Prometheus metrics server if enabled ---
        self._start_metrics_server()

    def _start_metrics_server(self) -> None:
        """Start the Prometheus metrics HTTP server if monitoring is enabled."""
        if not self.settings.monitoring.enabled:
            return
        collector = get_metrics()
        if collector is not None:
            if collector.start_server(port=self.settings.monitoring.port):
                logger.info(
                    "Prometheus metrics server started on port %d",
                    self.settings.monitoring.port,
                )

    @staticmethod
    def _extract_account_id(payload: Dict[str, Any]) -> str:
        """Backward-compatible facade for the shared account-ID extractor."""
        return extract_account_id(payload)

    def process_transaction(self, payload: Dict[str, Any]):
        tx_id = payload.get("transaction_id", "UNKNOWN")
        amount = payload.get("amount") or payload.get("transaction_amount") or 0.0
        logger.info("PROCESSING --> tx_id: %s | amount: $%s", tx_id, amount)

        prediction = self.inference_service.predict(payload)
        graph_score = self.graph_builder.graph_risk(payload)
        self.graph_builder.add_transaction(payload)

        account_id = extract_account_id(payload)
        assessment = self.risk_engine.evaluate_transaction(
            ml_score=prediction.fraud_probability,
            graph_score=graph_score,
            rules_breached=count_rule_breaches(payload),
            account_id=account_id,
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
            logger.info(
                "RISK %s [%s]: %s",
                assessment["assigned_risk_level"],
                assessment["composite_fraud_score"],
                assessment["action"],
            )

        # Record transaction outcome in Prometheus metrics
        self._record_transaction_metric(assessment)
        return assessment

    def _record_transaction_metric(self, assessment: Dict[str, Any]) -> None:
        """Record processed/failed transaction metric."""
        collector = get_metrics()
        if collector is None:
            return
        status = "processed"
        try:
            collector.record_transaction(source="streaming", status=status)
        except Exception:  # pragma: no cover
            logger.debug("Failed to record transaction metric.", exc_info=True)

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
