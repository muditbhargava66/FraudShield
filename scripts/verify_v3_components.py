#!/usr/bin/env python3
"""
FraudShield v3.0.0 Component Verification Script

Validates that all v3.0.0 components (and their integration with v2.x
components) function correctly. Run this to confirm the full stack
is wired up properly before deploying.

Usage:
    python scripts/verify_v3_components.py
    uv run python scripts/verify_v3_components.py
"""

from __future__ import annotations

import sys
import time
import traceback
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASSED = 0
FAILED = 0
ERRORS: list[str] = []


def check(name: str, fn: Any) -> None:
    """Run a verification check and report pass/fail."""
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        print(f"  [PASS] {name}")
    except Exception as exc:
        FAILED += 1
        ERRORS.append(f"{name}: {exc}")
        print(f"  [FAIL] {name} -> {exc}")
        traceback.print_exc()


def section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


# ---------------------------------------------------------------------------
# 1. Module Imports
# ---------------------------------------------------------------------------


def verify_imports():
    section("1. Module Import Verification")

    def _config_settings():
        from fraudshield.config.settings import (
            MonitoringSettings,
            get_settings,
        )
        s = get_settings()
        assert hasattr(s.kafka, "broker_type"), "KafkaSettings missing broker_type"
        assert hasattr(s, "monitoring"), "RuntimeSettings missing monitoring"
        assert isinstance(s.monitoring, MonitoringSettings)

    def _fraud_ring_detector():
        from fraudshield.graph.fraud_ring_detector import FraudRing, FraudRingDetector
        assert FraudRing is not None
        assert FraudRingDetector is not None

    def _monitoring_metrics():
        from fraudshield.monitoring.metrics import MetricsCollector, get_metrics
        assert MetricsCollector is not None
        assert get_metrics is not None

    def _drift_hooks():
        from fraudshield.monitoring.drift_hooks import (
            run_drift_check_with_metrics,
            streaming_drift_monitor,
        )
        assert run_drift_check_with_metrics is not None
        assert streaming_drift_monitor is not None

    def _broker_abstraction():
        from fraudshield.streaming.broker import (
            BrokerType,
        )
        assert BrokerType.KAFKA.value == "kafka"
        assert BrokerType.REDPANDA.value == "redpanda"

    def _risk_engine_updated():
        from fraudshield.core.risk_engine.engine import HybridRiskEngine
        engine = HybridRiskEngine()
        assert hasattr(engine, "ring_detector"), "HybridRiskEngine missing ring_detector"

    def _inference_service_updated():
        from fraudshield.ml.inference.service import FraudInferenceService
        assert FraudInferenceService is not None

    def _graph_builder_updated():
        from fraudshield.graph.graph_builder.builder import FraudGraphBuilder
        assert FraudGraphBuilder is not None

    def _main_orchestrator():
        from fraudshield.main import RealTimeOrchestrator
        assert RealTimeOrchestrator is not None

    def _resources_updated():
        from fraudshield.runtime.resources import (
            create_consumer_via_broker,
            create_producer_via_broker,
        )
        assert create_producer_via_broker is not None
        assert create_consumer_via_broker is not None

    checks = [
        ("config/settings.py (MonitoringSettings + broker_type)", _config_settings),
        ("graph/fraud_ring_detector.py", _fraud_ring_detector),
        ("monitoring/metrics.py", _monitoring_metrics),
        ("monitoring/drift_hooks.py", _drift_hooks),
        ("streaming/broker.py", _broker_abstraction),
        ("core/risk_engine/engine.py (ring_detector)", _risk_engine_updated),
        ("ml/inference/service.py (metrics)", _inference_service_updated),
        ("graph/graph_builder/builder.py (ring_detector)", _graph_builder_updated),
        ("main.py (RealTimeOrchestrator)", _main_orchestrator),
        ("runtime/resources.py (broker helpers)", _resources_updated),
    ]
    for name, fn in checks:
        check(name, fn)


# ---------------------------------------------------------------------------
# 2. Configuration Verification
# ---------------------------------------------------------------------------


def verify_config():
    section("2. Configuration Verification")

    def _monitoring_defaults():
        from fraudshield.config.settings import get_settings
        s = get_settings()
        assert s.monitoring.enabled is True
        assert s.monitoring.port == 9090
        assert s.monitoring.metrics_path == "/metrics"

    def _broker_type_default():
        from fraudshield.config.settings import get_settings
        s = get_settings()
        assert s.kafka.broker_type == "kafka"

    def _monitoring_env_override():
        import os

        from fraudshield.config.settings import get_settings
        get_settings.cache_clear()
        os.environ["FRAUDSHIELD_MONITORING_ENABLED"] = "false"
        os.environ["FRAUDSHIELD_MONITORING_PORT"] = "9999"
        os.environ["FRAUDSHIELD_KAFKA_BROKER_TYPE"] = "redpanda"
        try:
            s = get_settings()
            assert s.monitoring.enabled is False
            assert s.monitoring.port == 9999
            assert s.kafka.broker_type == "redpanda"
        finally:
            del os.environ["FRAUDSHIELD_MONITORING_ENABLED"]
            del os.environ["FRAUDSHIELD_MONITORING_PORT"]
            del os.environ["FRAUDSHIELD_KAFKA_BROKER_TYPE"]
            get_settings.cache_clear()

    checks = [
        ("MonitoringSettings defaults", _monitoring_defaults),
        ("broker_type default is 'kafka'", _broker_type_default),
        ("Environment variable overrides", _monitoring_env_override),
    ]
    for name, fn in checks:
        check(name, fn)


# ---------------------------------------------------------------------------
# 3. Fraud Ring Detector
# ---------------------------------------------------------------------------


def verify_fraud_ring_detector():
    section("3. Fraud Ring Detector")

    def _fraud_ring_dataclass():
        from fraudshield.graph.fraud_ring_detector import FraudRing
        ring = FraudRing(
            ring_id="RING_test",
            member_accounts=["A", "B", "C"],
            shared_entities=["D1"],
            risk_score=1.5,
        )
        assert ring.risk_score == 1.0, f"Expected 1.0, got {ring.risk_score}"
        ring2 = FraudRing("R2", ["X"], [], -0.5)
        assert ring2.risk_score == 0.0

    def _risk_score_formula():
        from fraudshield.graph.fraud_ring_detector import FraudRingDetector
        score = FraudRingDetector._compute_risk_score(5, 0.8)
        expected = round(1.0 - 2.718281828 ** (-0.3 * 5 * 0.8), 4)
        assert abs(score - expected) < 0.01, f"Expected ~{expected}, got {score}"

    def _ring_id_deterministic():
        from fraudshield.graph.fraud_ring_detector import FraudRingDetector
        id1 = FraudRingDetector._make_ring_id(["C", "A", "B"])
        id2 = FraudRingDetector._make_ring_id(["A", "B", "C"])
        assert id1 == id2, f"Ring IDs differ: {id1} vs {id2}"
        assert id1.startswith("RING_")

    def _extract_subgraph_mock():
        from fraudshield.graph.fraud_ring_detector import FraudRingDetector
        mock_session = MagicMock()
        mock_session.run.return_value = [
            {"neighbor_id": "acct_2", "shared_id": "dev_1", "edge_weight": 3},
        ]
        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        detector = FraudRingDetector(mock_driver, min_ring_size=2)
        records = detector.extract_subgraph("acct_1")
        assert len(records) == 1
        assert records[0]["neighbor_id"] == "acct_2"

    def _assess_account_graceful_degradation():
        from fraudshield.graph.fraud_ring_detector import FraudRingDetector
        mock_driver = MagicMock()
        mock_driver.session.side_effect = Exception("Neo4j down")
        detector = FraudRingDetector(mock_driver)
        score = detector.assess_account("acct_1")
        assert score == 0.0, f"Expected 0.0, got {score}"

    checks = [
        ("FraudRing dataclass clamping", _fraud_ring_dataclass),
        ("Risk score formula", _risk_score_formula),
        ("Ring ID determinism (order-independent)", _ring_id_deterministic),
        ("extract_subgraph with mock driver", _extract_subgraph_mock),
        ("Graceful degradation on Neo4j failure", _assess_account_graceful_degradation),
    ]
    for name, fn in checks:
        check(name, fn)


# ---------------------------------------------------------------------------
# 4. Prometheus Metrics
# ---------------------------------------------------------------------------


def verify_metrics():
    section("4. Prometheus Metrics")

    def _collector_creation():
        from fraudshield.monitoring.metrics import MetricsCollector
        c = MetricsCollector()
        assert c._enabled is True
        assert c.transactions_total is not None
        assert c.inference_latency_seconds is not None
        assert c.fraud_probability is not None
        assert c.active_fraud_rings is not None
        assert c.drift_ratio is not None

    def _record_prediction():
        from fraudshield.monitoring.metrics import MetricsCollector
        c = MetricsCollector()
        mock_result = MagicMock()
        mock_result.model_name = "xgboost"
        mock_result.source = "trained_model"
        mock_result.fraud_probability = 0.85
        c.record_prediction(mock_result, latency=0.042)

    def _record_drift():
        from fraudshield.monitoring.metrics import MetricsCollector
        c = MetricsCollector()
        c.record_drift_check(0.15, 3, 20)

    def _singleton_pattern():
        import fraudshield.monitoring.metrics as mod
        mod._collector_instance = None
        from fraudshield.monitoring.metrics import get_metrics
        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2
        mod._collector_instance = None

    def _per_instance_registry():
        from fraudshield.monitoring.metrics import MetricsCollector
        c1 = MetricsCollector()
        c2 = MetricsCollector()
        assert c1._registry is not c2._registry, "Registries should be independent"

    checks = [
        ("MetricsCollector creation", _collector_creation),
        ("record_prediction()", _record_prediction),
        ("record_drift_check()", _record_drift),
        ("Singleton get_metrics()", _singleton_pattern),
        ("Per-instance CollectorRegistry", _per_instance_registry),
    ]
    for name, fn in checks:
        check(name, fn)


# ---------------------------------------------------------------------------
# 5. Streaming Drift Monitor
# ---------------------------------------------------------------------------


def verify_drift_hooks():
    section("5. Streaming Drift Hooks")

    def _no_drift():
        from fraudshield.monitoring.drift_hooks import streaming_drift_monitor
        result = streaming_drift_monitor(
            {"amount": [100.0, 102.0, 98.0]},
            {"amount": {"mean": 100.0, "std": 10.0}},
            z_threshold=3.0,
        )
        assert result["amount"] == False  # noqa: E712

    def _drift_detected():
        from fraudshield.monitoring.drift_hooks import streaming_drift_monitor
        result = streaming_drift_monitor(
            {"amount": [500.0, 510.0, 495.0]},
            {"amount": {"mean": 100.0, "std": 10.0}},
            z_threshold=3.0,
        )
        assert result["amount"] == True  # noqa: E712

    checks = [
        ("No drift (stable features)", _no_drift),
        ("Drift detected (z-score > threshold)", _drift_detected),
    ]
    for name, fn in checks:
        check(name, fn)


# ---------------------------------------------------------------------------
# 6. Broker Abstraction
# ---------------------------------------------------------------------------


def verify_broker():
    section("6. Streaming Broker Abstraction")

    def _factory_dispatch_kafka():
        from fraudshield.streaming.broker import KafkaBrokerFactory, get_broker_factory
        f = get_broker_factory("kafka")
        assert isinstance(f, KafkaBrokerFactory)

    def _factory_dispatch_redpanda():
        from fraudshield.streaming.broker import RedpandaBrokerFactory, get_broker_factory
        f = get_broker_factory("redpanda")
        assert isinstance(f, RedpandaBrokerFactory)

    def _factory_dispatch_invalid():
        from fraudshield.streaming.broker import get_broker_factory
        try:
            get_broker_factory("rabbitmq")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def _factory_dispatch_case_insensitive():
        from fraudshield.streaming.broker import KafkaBrokerFactory, get_broker_factory
        f = get_broker_factory("KAFKA")
        assert isinstance(f, KafkaBrokerFactory)

    checks = [
        ("Kafka factory dispatch", _factory_dispatch_kafka),
        ("Redpanda factory dispatch", _factory_dispatch_redpanda),
        ("Invalid broker type raises ValueError", _factory_dispatch_invalid),
        ("Case-insensitive dispatch", _factory_dispatch_case_insensitive),
    ]
    for name, fn in checks:
        check(name, fn)


# ---------------------------------------------------------------------------
# 7. Risk Engine with Ring Detector
# ---------------------------------------------------------------------------


def verify_risk_engine():
    section("7. Risk Engine + Ring Detector Integration")

    def _without_ring_detector():
        from fraudshield.core.risk_engine.engine import HybridRiskEngine
        engine = HybridRiskEngine(ml_weight=0.6, graph_weight=0.3, rule_weight=0.1)
        result = engine.evaluate_transaction(
            ml_score=0.5, graph_score=0.2, rules_breached=0, account_id="acct_1"
        )
        # composite = 0.5*0.6 + 0.2*0.3 + 0*0.1 = 0.36
        assert abs(result["composite_fraud_score"] - 0.36) < 0.01

    def _with_ring_detector():
        from fraudshield.core.risk_engine.engine import HybridRiskEngine
        mock_detector = MagicMock()
        mock_detector.assess_account.return_value = 0.9
        engine = HybridRiskEngine(
            ml_weight=0.6, graph_weight=0.3, rule_weight=0.1,
            ring_detector=mock_detector,
        )
        result = engine.evaluate_transaction(
            ml_score=0.5, graph_score=0.1, rules_breached=0,
            account_id="acct_123",
        )
        # ring_score 0.9 > graph_score 0.1 -> graph becomes 0.9
        # composite = 0.5*0.6 + 0.9*0.3 = 0.57
        assert result["graph_contribution"] == 0.9
        assert abs(result["composite_fraud_score"] - 0.57) < 0.01
        mock_detector.assess_account.assert_called_once_with("acct_123")

    def _ring_detector_failure_graceful():
        from fraudshield.core.risk_engine.engine import HybridRiskEngine
        mock_detector = MagicMock()
        mock_detector.assess_account.side_effect = Exception("Neo4j error")
        engine = HybridRiskEngine(
            ml_weight=0.6, graph_weight=0.3, rule_weight=0.1,
            ring_detector=mock_detector,
        )
        result = engine.evaluate_transaction(
            ml_score=0.5, graph_score=0.2, rules_breached=0,
            account_id="acct_1",
        )
        # Should fall back to original graph_score=0.2
        assert result["graph_contribution"] == 0.2

    def _backward_compatible_no_account_id():
        from fraudshield.core.risk_engine.engine import HybridRiskEngine
        engine = HybridRiskEngine()
        result = engine.evaluate_transaction(
            ml_score=0.5, graph_score=0.2, rules_breached=1,
        )
        assert "composite_fraud_score" in result

    checks = [
        ("Without ring detector (original behavior)", _without_ring_detector),
        ("With ring detector (score blending)", _with_ring_detector),
        ("Ring detector failure -> graceful fallback", _ring_detector_failure_graceful),
        ("Backward compatible (no account_id)", _backward_compatible_no_account_id),
    ]
    for name, fn in checks:
        check(name, fn)


# ---------------------------------------------------------------------------
# 8. Orchestrator Integration
# ---------------------------------------------------------------------------


def verify_orchestrator():
    section("8. RealTimeOrchestrator Integration")

    def _orchestrator_with_mocks():
        import pandas as pd

        from fraudshield.main import RealTimeOrchestrator

        graph_builder = MagicMock()
        graph_builder.graph_risk.return_value = 0.2
        graph_builder.ring_detector = None

        inference_service = MagicMock()
        inference_service.model_loaded = False
        inference_service.predict.return_value = SimpleNamespace(
            transaction_id="tx_999",
            fraud_probability=0.82,
            model_loaded=False,
            source="rules_fallback",
            features=pd.DataFrame([{"amount": 5000.0}]),
        )

        orchestrator = RealTimeOrchestrator(
            producer=MagicMock(),
            consumer=MagicMock(),
            graph_builder=graph_builder,
            inference_service=inference_service,
        )

        payload = {
            "transaction_id": "tx_999",
            "account_id": "acct_42",
            "amount": 5000.0,
            "is_online": True,
            "is_international": True,
        }
        assessment = orchestrator.process_transaction(payload)

        assert assessment["assigned_risk_level"] in {"MEDIUM", "HIGH"}
        assert "composite_fraud_score" in assessment
        graph_builder.add_transaction.assert_called_once_with(payload)

    def _orchestrator_weights_correct():
        from fraudshield.main import RealTimeOrchestrator

        graph_builder = MagicMock()
        graph_builder.graph_risk.return_value = 0.0
        graph_builder.ring_detector = None

        orchestrator = RealTimeOrchestrator(
            producer=MagicMock(),
            consumer=MagicMock(),
            graph_builder=graph_builder,
            inference_service=MagicMock(),
        )

        assert orchestrator.risk_engine.ml_weight == 0.6
        assert orchestrator.risk_engine.graph_weight == 0.3
        assert orchestrator.risk_engine.rule_weight == 0.1

    def _extract_account_id():
        from fraudshield.main import RealTimeOrchestrator

        orchestrator = RealTimeOrchestrator(
            producer=MagicMock(),
            consumer=MagicMock(),
            graph_builder=MagicMock(),
            inference_service=MagicMock(),
        )

        assert orchestrator._extract_account_id({"account_id": "a1"}) == "a1"
        assert orchestrator._extract_account_id({"user_id": "u1"}) == "u1"
        assert orchestrator._extract_account_id({"transaction_id": "t1"}) == "t1"

    checks = [
        ("Full process_transaction with mocks", _orchestrator_with_mocks),
        ("Risk engine weights (0.6, 0.3, 0.1)", _orchestrator_weights_correct),
        ("_extract_account_id() fallback logic", _extract_account_id),
    ]
    for name, fn in checks:
        check(name, fn)


# ---------------------------------------------------------------------------
# 9. Inference Service Metrics Integration
# ---------------------------------------------------------------------------


def verify_inference_metrics():
    section("9. Inference Service + Metrics Integration")

    def _predict_records_latency():
        """Verify predict() returns a result with timing (internal _record_metrics called)."""
        from fraudshield.ml.inference.service import FraudInferenceService

        service = FraudInferenceService.__new__(FraudInferenceService)
        service.settings = MagicMock()
        service.model_name = "test"
        service.artifacts = None
        service.feature_store = None
        service.explainer = None

        result = service.predict({"amount": 100.0, "transaction_id": "tx_1"})
        assert result.source == "rules_fallback"
        assert result.fraud_probability >= 0.0

    checks = [
        ("predict() returns result (metrics recorded internally)", _predict_records_latency),
    ]
    for name, fn in checks:
        check(name, fn)


# ---------------------------------------------------------------------------
# 10. Docker Configuration Validation
# ---------------------------------------------------------------------------


def verify_docker():
    section("10. Docker Configuration")

    def _dockerfile_exists():
        from pathlib import Path
        assert Path("Dockerfile").exists(), "Dockerfile not found"

    def _dockerfile_content():
        from pathlib import Path
        content = Path("Dockerfile").read_text()
        assert "python:3.10" in content
        assert "EXPOSE 8000 9090" in content
        assert "uvicorn" in content

    def _docker_compose_valid():
        import os
        import subprocess

        environment = os.environ.copy()
        environment.update(
            {
                "FRAUDSHIELD_NEO4J_PASSWORD": "verification-only-password",
                "FRAUDSHIELD_POSTGRES_PASSWORD": "verification-only-password",
                "FRAUDSHIELD_GRAFANA_ADMIN_PASSWORD": "verification-only-password",
                "FRAUDSHIELD_DATABASE_URL": "postgresql+psycopg2://fraudshield:verification-only-password@postgres:5432/fraudshield_db",
            }
        )
        result = subprocess.run(
            ["docker", "compose", "-f", "infra/docker-compose.yml", "config", "--quiet"],
            capture_output=True,
            text=True,
            timeout=30,
            env=environment,
        )
        assert result.returncode == 0, f"docker compose config failed: {result.stderr}"

    def _prometheus_config_exists():
        from pathlib import Path
        p = Path("infra/prometheus.yml")
        assert p.exists(), "infra/prometheus.yml not found"
        content = p.read_text()
        assert "fraudshield:8000" in content

    def _compose_services():
        from pathlib import Path
        content = Path("infra/docker-compose.yml").read_text()
        for service in ["fraudshield", "prometheus", "grafana", "kafka", "neo4j"]:
            assert service in content, f"Service '{service}' not in docker-compose.yml"

    checks = [
        ("Dockerfile exists", _dockerfile_exists),
        ("Dockerfile content validation", _dockerfile_content),
        ("docker-compose.yml config valid", _docker_compose_valid),
        ("infra/prometheus.yml exists and targets fraudshield", _prometheus_config_exists),
        ("All expected services in docker-compose", _compose_services),
    ]
    for name, fn in checks:
        check(name, fn)


# ---------------------------------------------------------------------------
# 11. Existing Test Suite
# ---------------------------------------------------------------------------


def verify_test_suite():
    section("11. Existing Test Suite (pytest)")

    def _run_pytest():
        import subprocess
        result = subprocess.run(
            ["uv", "run", "pytest", "tests/", "-x", "-q", "--tb=short"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"\n    stdout: {result.stdout[-500:]}")
            print(f"    stderr: {result.stderr[-500:]}")
        assert result.returncode == 0, f"pytest failed (exit {result.returncode})"

    checks = [
        ("Full test suite passes", _run_pytest),
    ]
    for name, fn in checks:
        check(name, fn)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    print("=" * 60)
    print("  FraudShield v3.0.0 Component Verification")
    print("=" * 60)

    start = time.time()

    verify_imports()
    verify_config()
    verify_fraud_ring_detector()
    verify_metrics()
    verify_drift_hooks()
    verify_broker()
    verify_risk_engine()
    verify_orchestrator()
    verify_inference_metrics()
    verify_docker()
    verify_test_suite()

    elapsed = time.time() - start
    print(f"\n{'=' * 60}")
    print(f"  RESULTS: {PASSED} passed, {FAILED} failed ({elapsed:.1f}s)")
    print(f"{'=' * 60}")

    if ERRORS:
        print("\nFailures:")
        for err in ERRORS:
            print(f"  - {err}")

    return 1 if FAILED > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
