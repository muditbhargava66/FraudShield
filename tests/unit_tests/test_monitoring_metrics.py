"""
Unit tests for Prometheus monitoring metrics and drift hooks.
"""

from unittest.mock import MagicMock

from fraudshield.monitoring.drift_hooks import streaming_drift_monitor
from fraudshield.monitoring.metrics import MetricsCollector, get_metrics


class TestMetricsCollector:
    def setup_method(self):
        """Reset the singleton between tests."""
        import fraudshield.monitoring.metrics as metrics_module
        metrics_module._collector_instance = None

    def test_collector_initializes_with_prometheus(self):
        collector = MetricsCollector()
        assert collector._enabled is True
        assert collector.transactions_total is not None
        assert collector.inference_latency_seconds is not None
        assert collector.fraud_probability is not None
        assert collector.risk_level_total is not None
        assert collector.active_fraud_rings is not None
        assert collector.drift_ratio is not None

    def test_record_prediction(self):
        collector = MetricsCollector()
        mock_result = MagicMock()
        mock_result.model_name = "xgboost"
        mock_result.source = "trained_model"
        mock_result.fraud_probability = 0.85

        # Should not raise
        collector.record_prediction(mock_result, latency=0.042)

    def test_record_transaction(self):
        collector = MetricsCollector()
        collector.record_transaction(source="batch", status="processed")
        collector.record_transaction(source="streaming", status="failed")

    def test_record_drift_check(self):
        collector = MetricsCollector()
        collector.record_drift_check(
            drift_ratio_value=0.15,
            drifted_feature_count=3,
            total_features=20,
        )

    def test_set_active_rings(self):
        collector = MetricsCollector()
        collector.set_active_rings(5)

    def test_get_metrics_singleton(self):
        import fraudshield.monitoring.metrics as metrics_module
        metrics_module._collector_instance = None

        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2

    def test_start_server_idempotent(self):
        collector = MetricsCollector()
        # Start once (may fail due to port conflict, but shouldn't raise)
        collector.start_server(port=19090)
        # Second call should be a no-op
        collector.start_server(port=19090)


class TestStreamingDriftMonitor:
    def test_no_drift_stable_features(self):
        feature_values = {
            "amount": [100.0, 102.0, 98.0, 101.0, 99.0],
            "frequency": [5.0, 4.8, 5.1, 5.2, 4.9],
        }
        baseline_stats = {
            "amount": {"mean": 100.0, "std": 10.0},
            "frequency": {"mean": 5.0, "std": 1.0},
        }

        results = streaming_drift_monitor(feature_values, baseline_stats, z_threshold=3.0)

        assert results["amount"] is False
        assert results["frequency"] is False

    def test_drift_detected_in_feature(self):
        feature_values = {
            "amount": [500.0, 510.0, 495.0, 505.0, 500.0],
            "frequency": [5.0, 4.8, 5.1, 5.2, 4.9],
        }
        baseline_stats = {
            "amount": {"mean": 100.0, "std": 10.0},
            "frequency": {"mean": 5.0, "std": 1.0},
        }

        results = streaming_drift_monitor(feature_values, baseline_stats, z_threshold=3.0)

        assert results["amount"] is True  # z_score = 40.0, well above 3.0
        assert results["frequency"] is False

    def test_missing_baseline_feature(self):
        feature_values = {"unknown_feature": [1.0, 2.0, 3.0]}
        baseline_stats = {}

        results = streaming_drift_monitor(feature_values, baseline_stats)

        assert results["unknown_feature"] is False

    def test_empty_feature_values(self):
        feature_values = {"amount": []}
        baseline_stats = {"amount": {"mean": 100.0, "std": 10.0}}

        results = streaming_drift_monitor(feature_values, baseline_stats)

        assert results["amount"] is False

    def test_constant_baseline_feature(self):
        """Test handling of near-zero std to avoid division by zero."""
        feature_values = {"constant": [5.0, 5.0, 5.0]}
        baseline_stats = {"constant": {"mean": 5.0, "std": 0.0}}

        results = streaming_drift_monitor(feature_values, baseline_stats)

        assert results["constant"] == False  # noqa: E712 - mean matches baseline exactly

    def test_constant_baseline_with_drift(self):
        feature_values = {"constant": [10.0, 10.0, 10.0]}
        baseline_stats = {"constant": {"mean": 5.0, "std": 0.0}}

        results = streaming_drift_monitor(feature_values, baseline_stats)

        assert results["constant"] == True  # noqa: E712 - mean differs from baseline
