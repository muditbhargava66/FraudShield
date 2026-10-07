"""
Prometheus metrics collector for FraudShield streaming and inference pipelines.

Provides counters, histograms, and gauges for:
- Transaction throughput (processed / failed)
- Inference latency per prediction
- Fraud probability distribution
- Risk level breakdown (HIGH / MEDIUM / LOW)
- Active fraud ring count
- Data drift ratio
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional, cast

if TYPE_CHECKING:
    from fraudshield.ml.inference.service import PredictionResult

logger = logging.getLogger(__name__)

try:
    from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, make_asgi_app, start_http_server

    _HAS_PROMETHEUS = True
except ImportError:  # pragma: no cover - optional dependency
    CollectorRegistry = None  # type: ignore[assignment,misc]
    Counter = None  # type: ignore[assignment,misc]
    Gauge = None  # type: ignore[assignment,misc]
    Histogram = None  # type: ignore[assignment,misc]
    make_asgi_app = None  # type: ignore[assignment,misc]
    start_http_server = None  # type: ignore[assignment]
    _HAS_PROMETHEUS = False

# Histogram bucket boundaries
_LATENCY_BUCKETS = (0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
_PROBABILITY_BUCKETS = (0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95)


class MetricsCollector:
    """
    Central Prometheus metrics registry for FraudShield.

    All metric objects are created lazily. If ``prometheus_client`` is not
    installed the collector operates as a silent no-op so that callers do not
    need conditional imports.
    """

    def __init__(self) -> None:
        self._enabled = _HAS_PROMETHEUS
        self._server_started = False
        self._registry = None

        if not _HAS_PROMETHEUS:
            self.transactions_total = None
            self.risk_level_total = None
            self.inference_latency_seconds = None
            self.fraud_probability = None
            self.active_fraud_rings = None
            self.drift_ratio = None
            self.drifted_features = None
            return

        # Use a dedicated registry per instance to avoid duplicate-registration errors
        self._registry = CollectorRegistry()  # type: ignore[misc]

        # --- Counters ---
        self.transactions_total = Counter(  # type: ignore[assignment]
            "fraudshield_transactions_total",
            "Total transactions processed",
            ["source", "status"],
            registry=self._registry,
        )

        self.risk_level_total = Counter(  # type: ignore[assignment]
            "fraudshield_risk_level_total",
            "Predictions grouped by assigned risk level",
            ["level"],
            registry=self._registry,
        )

        # --- Histograms ---
        self.inference_latency_seconds = Histogram(  # type: ignore[assignment]
            "fraudshield_inference_latency_seconds",
            "Inference latency per prediction",
            ["model_name", "source"],
            buckets=_LATENCY_BUCKETS,
            registry=self._registry,
        )

        self.fraud_probability = Histogram(  # type: ignore[assignment]
            "fraudshield_fraud_probability",
            "Distribution of fraud probability scores",
            buckets=_PROBABILITY_BUCKETS,
            registry=self._registry,
        )

        # --- Gauges ---
        self.active_fraud_rings = Gauge(  # type: ignore[assignment]
            "fraudshield_active_fraud_rings",
            "Current number of detected fraud rings",
            registry=self._registry,
        )

        self.drift_ratio = Gauge(  # type: ignore[assignment]
            "fraudshield_drift_ratio",
            "Latest data drift ratio from KS-test validation",
            registry=self._registry,
        )

        self.drifted_features = Gauge(  # type: ignore[assignment]
            "fraudshield_drifted_features",
            "Number of features that drifted beyond threshold",
            registry=self._registry,
        )

    # ------------------------------------------------------------------
    # Convenience recorders
    # ------------------------------------------------------------------

    def record_transaction(self, source: str = "streaming", status: str = "processed") -> None:
        """Increment the transaction counter."""
        if self.transactions_total is not None:
            self.transactions_total.labels(source=source, status=status).inc()

    def record_prediction(self, result: "PredictionResult", latency: float) -> None:
        """Record all metrics associated with a single prediction."""
        if self.inference_latency_seconds is not None:
            self.inference_latency_seconds.labels(
                model_name=result.model_name,
                source=result.source,
            ).observe(latency)

        if self.fraud_probability is not None:
            self.fraud_probability.observe(result.fraud_probability)

        # Derive risk level from probability using the same thresholds as HybridRiskEngine
        risk_level = "HIGH" if result.fraud_probability >= 0.75 else (
            "MEDIUM" if result.fraud_probability >= 0.40 else "LOW"
        )
        if self.risk_level_total is not None:
            self.risk_level_total.labels(level=risk_level).inc()

        self.record_transaction(source=result.source, status="processed")

    def record_drift_check(
        self,
        drift_ratio_value: float,
        drifted_feature_count: int,
        total_features: int = 0,
    ) -> None:
        """Record drift check results."""
        if self.drift_ratio is not None:
            self.drift_ratio.set(drift_ratio_value)
        if self.drifted_features is not None:
            self.drifted_features.set(drifted_feature_count)
        logger.info(
            "Drift metrics recorded: ratio=%.4f, drifted=%d/%d",
            drift_ratio_value,
            drifted_feature_count,
            total_features,
        )

    def set_active_rings(self, count: int) -> None:
        """Update the active fraud rings gauge."""
        if self.active_fraud_rings is not None:
            self.active_fraud_rings.set(count)

    # ------------------------------------------------------------------
    # HTTP server
    # ------------------------------------------------------------------

    def start_server(self, port: int = 9090) -> bool:
        """Start the Prometheus metrics HTTP server and report whether it is available."""
        if not self._enabled:
            logger.warning("prometheus_client not installed; metrics server not started.")
            return False
        if self._server_started:
            return True
        try:
            start_http_server(port, registry=cast(Any, self._registry))  # type: ignore[misc]
            self._server_started = True
            logger.info("Prometheus metrics server started on port %d", port)
            return True
        except Exception as exc:
            logger.warning("Failed to start Prometheus metrics server: %s", exc)
            return False

    def asgi_app(self):
        """Return an ASGI metrics endpoint backed by this collector's registry."""
        if not self._enabled or self._registry is None:
            return None
        return make_asgi_app(registry=cast(Any, self._registry))  # type: ignore[misc, arg-type]


_collector_instance: Optional[MetricsCollector] = None


def get_metrics() -> MetricsCollector:
    """Return (or create) the process-wide MetricsCollector singleton."""
    global _collector_instance
    if _collector_instance is None:
        _collector_instance = MetricsCollector()
    return _collector_instance
