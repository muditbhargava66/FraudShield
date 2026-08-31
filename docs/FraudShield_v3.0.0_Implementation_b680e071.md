# FraudShield v3.0.0 Implementation Plan

## Task 1: Add new dependencies to pyproject.toml

Add `prometheus_client` and `networkx` as core dependencies. The `confluent-kafka` library already works with Redpanda (Kafka-compatible protocol), so no new broker dependency is needed.

- File: `pyproject.toml`
- Add `"prometheus_client>=0.21.0"` and `"networkx>=3.2"` to `[project.dependencies]`
- Regenerate `uv.lock` via `uv lock`

## Task 2: Fraud Ring Detector (`graph/fraud_ring_detector.py`)

Detect coordinated fraud rings by finding communities of accounts connected through shared devices/IPs in the Neo4j graph.

**New file: `src/fraudshield/graph/fraud_ring_detector.py`**
- Class `FraudRingDetector` with constructor `__init__(driver, min_ring_size=3)`
- `extract_subgraph(account_id) -> list[dict]`: Cypher query fetching the 2-hop neighborhood (account -> shared device/IP -> connected accounts). Uses `MATCH (a:Account {id: $id})-[:FROM_DEVICE|FROM_IP*1..2]-(connected:Account) RETURN connected, ...` pattern.
- `detect_rings(account_id) -> list[FraudRing]`: Builds a `networkx.Graph` from the subgraph, runs `nx.community.louvain_communities()`, filters by `min_ring_size`, returns `FraudRing` dataclasses.
- `FraudRing` dataclass: `ring_id`, `member_accounts`, `shared_entities`, `risk_score` (based on ring size + density).
- `assess_account(account_id) -> float`: Returns the max ring risk score for the account, or 0.0 if no ring found.
- Graceful degradation: `try/except` around Neo4j and networkx calls, returning empty results on failure.

**Modify: `src/fraudshield/graph/graph_builder/builder.py`**
- Add `detect_fraud_rings(account_id) -> list[FraudRing]` method that delegates to `FraudRingDetector`.
- Add `ring_risk(account_id) -> float` method that returns the max ring risk score.

**New tests: `tests/unit_tests/test_fraud_ring_detector.py`**
- `test_extract_subgraph_with_mock_driver`: Mock Neo4j session, verify Cypher query structure.
- `test_detect_rings_builds_graph`: Mock Neo4j results, verify networkx graph construction and community detection.
- `test_detect_rings_empty_graph`: Verify empty input returns empty rings.
- `test_assess_account_with_ring`: Verify risk score aggregation.
- `test_graceful_degradation_on_neo4j_failure`: Mock driver raises exception, verify empty result.

## Task 3: Monitoring Metrics (`monitoring/metrics.py`)

Prometheus-compatible metrics for the streaming and inference pipeline.

**New file: `src/fraudshield/monitoring/__init__.py`**
- Re-export `MetricsCollector`, `setup_metrics`.

**New file: `src/fraudshield/monitoring/metrics.py`**
- Class `MetricsCollector` (singleton via `get_metrics()`):
  - `transactions_total` (Counter): labels `source` (streaming/batch), `status` (processed/failed)
  - `inference_latency_seconds` (Histogram): labels `model_name`, `source` (trained_model/rules_fallback). Buckets: 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0
  - `fraud_probability` (Histogram): distribution of prediction scores. Buckets: 0.05 to 0.95
  - `risk_level_total` (Counter): labels `level` (HIGH/MEDIUM/LOW)
  - `active_fraud_rings` (Gauge): current count of detected rings
  - `drift_ratio` (Gauge): latest drift ratio from drift check
- `setup_metrics(port=9090)`: Starts Prometheus HTTP server. Graceful fallback if `prometheus_client` is not installed.
- `record_prediction(result: PredictionResult, latency: float)`: Convenience method recording all prediction-related metrics in one call.
- `record_drift_check(drift_ratio: float, drifted_features: int, total_features: int)`: Records drift metrics.

**New file: `src/fraudshield/monitoring/drift_hooks.py`**
- Function `run_drift_check_with_metrics(train_path, test_path, max_drift_ratio=0.3)`: Wraps the existing KS-test logic from `pipeline_tasks.py`, but also emits metrics via `MetricsCollector`.
- Function `streaming_drift_monitor(feature_store, baseline_stats, check_interval=1000)`: Periodically compares streaming feature distributions against baseline. Uses simple mean/std comparison (not full KS test) for low-overhead streaming checks.

**Modify: `src/fraudshield/config/settings.py`**
- Add `MonitoringSettings` dataclass: `enabled` (bool), `port` (int, default 9090), `metrics_path` (str, default "/metrics")
- Add `monitoring: MonitoringSettings` field to `RuntimeSettings`
- Add env var resolution: `FRAUDSHIELD_MONITORING_ENABLED`, `FRAUDSHIELD_MONITORING_PORT`

**Modify: `src/fraudshield/ml/inference/service.py`**
- Wrap `predict()` with latency timing via `time.perf_counter()`, call `MetricsCollector.record_prediction()` after each prediction.
- Import `MetricsCollector` with `try/except ImportError` guard.

**New tests: `tests/unit_tests/test_monitoring_metrics.py`**
- `test_metrics_collector_records_prediction`: Verify counter increments and histogram observations.
- `test_metrics_collector_records_drift`: Verify gauge updates.
- `test_setup_metrics_without_prometheus`: Verify graceful degradation when `prometheus_client` is missing.
- `test_streaming_drift_monitor`: Verify drift detection with synthetic data.

## Task 4: Streaming Broker Abstraction (`streaming/broker.py`)

Pluggable broker interface supporting Kafka and Redpanda.

**New file: `src/fraudshield/streaming/broker.py`**
- Enum `BrokerType` with values `KAFKA`, `REDPANDA`.
- Abstract class `BrokerFactory` with methods:
  - `create_producer(settings) -> Producer`
  - `create_consumer(settings) -> Consumer`
- Class `KafkaBrokerFactory(BrokerFactory)`: Delegates to existing `resources.create_kafka_producer/consumer`.
- Class `RedpandaBrokerFactory(BrokerFactory)`: Same implementation (Redpanda is Kafka-protocol compatible) but with Redpanda-specific config tweaks (e.g., `security.protocol` handling).
- Function `get_broker_factory(broker_type: str) -> BrokerFactory`: Factory dispatcher.

**Modify: `src/fraudshield/config/settings.py`**
- Add `broker_type: str` field to `KafkaSettings` (default `"kafka"`, env var `FRAUDSHIELD_KAFKA_BROKER_TYPE`).

**Modify: `src/fraudshield/runtime/resources.py`**
- Add `create_broker_producer(kafka) -> Producer` and `create_broker_consumer(kafka) -> Consumer` that use the broker factory based on `kafka.broker_type`.

**New tests: `tests/unit_tests/test_broker_abstraction.py`**
- `test_kafka_broker_factory_creates_producer`: Mock confluent_kafka, verify factory returns producer.
- `test_redpanda_broker_factory_creates_producer`: Same for Redpanda.
- `test_get_broker_factory_dispatcher`: Verify correct factory returned for each type.
- `test_invalid_broker_type_raises`: Verify ValueError on unknown type.

## Task 5: Docker Infrastructure

Add a Dockerfile for the application and update docker-compose with monitoring services.

**New file: `Dockerfile`**
- Multi-stage build: Python 3.10 slim base, copy `pyproject.toml` + `src/`, install with `pip install -e .`, expose port 8000 (FastAPI) and 9090 (Prometheus).
- ENTRYPOINT: `uvicorn fraudshield.ml.inference.api:app --host 0.0.0.0 --port 8000`

**Modify: `infra/docker-compose.yml`**
- Add `fraudshield` service: builds from Dockerfile, depends on kafka + neo4j, exposes 8000 + 9090.
- Add `prometheus` service: `prom/prometheus:v2.47.0`, port 9091, with scrape config targeting `fraudshield:8000`.
- Add `grafana` service: `grafana/grafana:10.1.0`, port 3000, with Prometheus datasource.
- Add Prometheus config file: `infra/prometheus.yml` with scrape targets.

**New file: `infra/prometheus.yml`**
- Scrape config for `fraudshield` service at `fraudshield:8000/metrics`.

## Task 6: Integration with Risk Engine

**Modify: `src/fraudshield/core/risk_engine/engine.py`**
- Add optional `ring_detector: FraudRingDetector` parameter to constructor.
- In `evaluate_transaction()`, if `ring_detector` is provided, compute `ring_score = ring_detector.assess_account(payload.get("account_id", ""))` and blend it into `graph_score` (e.g., `graph_score = max(graph_score, ring_score)`).
- Import `FraudRingDetector` with `try/except ImportError` guard.

**Modify existing test: `tests/unit_tests/test_realtime_architecture.py`**
- Add `test_risk_engine_with_ring_detector`: Mock ring detector, verify ring score influences composite score.

## Task 7: Tests and Verification

- Run `uv run ruff check src tests` -- all checks passed.
- Run `uv run mypy src/` -- no issues in all source files.
- Run `uv run pytest tests/ -v` -- all tests pass.
- Run `docker compose -f infra/docker-compose.yml config` -- validate compose syntax.

## Task 8: Documentation Updates

**Modify: `CHANGELOG.md`**
- Expand `[3.0.0] - Unreleased` section with all new additions.

**Modify: `README.md`**
- Add "Fraud ring detection" and "Prometheus monitoring" to Key Features.
- Add monitoring configuration section.
- Update Docker section with new services.

**Modify: `AGENTS.md`**
- Update planned modules table to show completed status.
- Add monitoring settings to conventions.
- Update data artifacts table.

**Modify: `docs/PRD_v3.0.0.md`**
- Update implementation status review to reflect completed modules.

**New file: `docs/monitoring.md`**
- Prometheus metrics reference (names, types, labels).
- Grafana dashboard setup instructions.
- Drift monitoring configuration.

**New file: `docs/fraud_ring_detection.md`**
- Algorithm explanation (Louvain community detection).
- Configuration options and thresholds.
- Neo4j query patterns.
