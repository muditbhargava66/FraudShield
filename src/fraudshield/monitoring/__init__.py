"""
FraudShield monitoring module — Prometheus metrics and drift detection.
"""

from fraudshield.monitoring.metrics import MetricsCollector, get_metrics, setup_metrics

__all__ = ["MetricsCollector", "get_metrics", "setup_metrics"]
