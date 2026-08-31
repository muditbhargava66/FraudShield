# Changelog

All notable changes to FraudShield are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.0.0] - 2026-09-01

### Added
- `.gitattributes` for GitHub Linguist language detection overrides.
- **Fraud ring detection** (`graph/fraud_ring_detector.py`): Louvain community detection on Neo4j 2-hop neighborhood subgraphs to identify coordinated fraud rings connected via shared devices/IPs.
- `FraudRing` dataclass with `ring_id`, `member_accounts`, `shared_entities`, `risk_score`, and `density`.
- `FraudRingDetector.assess_account()` returns the max ring risk score for an account, integrated into `HybridRiskEngine` as an optional `ring_detector` parameter.
- **Prometheus monitoring** (`monitoring/metrics.py`): `MetricsCollector` with counters (transactions_total, risk_level_total), histograms (inference_latency_seconds, fraud_probability), and gauges (active_fraud_rings, drift_ratio, drifted_features). Uses per-instance `CollectorRegistry` for test isolation.
- **Drift detection hooks** (`monitoring/drift_hooks.py`): `run_drift_check_with_metrics()` wraps KS-test logic with Prometheus emission; `streaming_drift_monitor()` uses lightweight z-score comparison for streaming features.
- **Streaming broker abstraction** (`streaming/broker.py`): `BrokerFactory` ABC with `KafkaBrokerFactory` and `RedpandaBrokerFactory`. Both use `confluent-kafka` (Kafka wire protocol). Redpanda factory adds `SASL_SSL`/`SCRAM-SHA-256` defaults.
- `MonitoringSettings` dataclass with `enabled`, `port`, and `metrics_path` fields.
- `broker_type` field on `KafkaSettings` (env: `FRAUDSHIELD_KAFKA_BROKER_TYPE`, default `"kafka"`).
- `HybridRiskEngine` now accepts optional `ring_detector` and `account_id` parameter on `evaluate_transaction()`.
- Inference service wraps `predict()` with `time.perf_counter()` latency timing and automatic metrics recording.
- `Dockerfile` for the application (Python 3.10 slim, uv-based build with CMake for C++ extensions). Fixed to include `README.md`, `CMakeLists.txt`, and full `src/` before `uv sync`.
- `.dockerignore` to exclude build artifacts, IDE configs, notebooks, and docs from Docker build context.
- `infra/prometheus.yml` scrape configuration targeting `fraudshield:8000/metrics`.
- Docker Compose services: `fraudshield` (app), `prometheus` (v2.47.0), `grafana` (10.1.0).
- `networkx>=3.2` and `prometheus_client>=0.21.0` added to core dependencies.
- **Updated `main.py`** (`RealTimeOrchestrator`): v3.0.0 integration with ring detector auto-wiring into risk engine, Prometheus metrics server startup, transaction metric recording, and account ID extraction for ring assessment.
- **Verification script** (`scripts/verify_v3_components.py`): 43-check comprehensive validation of all v3.0.0 components and their integration with v2.x components.
- **Performance benchmark** (`scripts/benchmark_performance.py`): TPS/latency benchmark covering the C++ cleaning wrapper, inference service, graph operations, and hybrid risk engine.
- **Notebook suite rebuilt for v3.0.0**: `01_fraudshield_pipeline_tutorial` (ingestion → preprocessing → drift gate → XGBoost training → evaluation → live scoring → SHAP), new `02_realtime_streaming_and_graph` (Kafka/Redpanda broker factories, stateful streaming features, Louvain ring detection, hybrid risk engine, in-process inference API), plus refreshed `exploratory_data_analysis` and `model_experimentation`. All four execute cleanly end-to-end and ship with embedded outputs.

### Changed
- `HybridRiskEngine.evaluate_transaction()` signature extended with `account_id` parameter (backward compatible, defaults to `""`).
- Kafka advertised listeners in docker-compose updated to support both internal (`kafka:29092`) and external (`localhost:9092`) access.
- Removed obsolete `version` attribute from `infra/docker-compose.yml`.
- `Resources.py` now exposes `create_producer_via_broker()` and `create_consumer_via_broker()` convenience functions.
- Rewrote `scripts/benchmark_performance.py` against the real v3.0.0 APIs: benchmarks `cpp_wrapper` C++ vs. NumPy-fallback cleaning side by side, adds the stateful feature store, labels the inference section with the actual loaded mode, measures distinct events instead of one repeated payload, and runs Neo4j writes live when reachable (simulated otherwise).

### Fixed
- Fixed missing `broker_type` attribute in `KafkaSettings` (`src/fraudshield/config/settings.py`) which caused mypy failures.
- Resolved numpy `bool_` to python `bool` typecasting issue in `streaming_drift_monitor` (`src/fraudshield/monitoring/drift_hooks.py`).
- Wired the Kafka/Redpanda broker factory into the producer and consumer, so `FRAUDSHIELD_KAFKA_BROKER_TYPE` now changes live connection settings.
- Made the API use the same ML + graph + rule hybrid assessment as the stream.
- Exposed the Prometheus collector's private registry through both FastAPI and the standalone streaming metrics server.
- Routed Airflow drift checks through the shared metrics-aware implementation and aligned default ingestion with the `transactions` schema.
- Passed transformed model features—not raw input columns—to SHAP explainers.
- Graph repository no longer crashes Neo4j when `device_id`/`ip_address` are absent: entity MERGEs are conditional, and payloads missing `transaction_id` or `user_id`/`account_id` fail fast with a clear error.
- `KafkaBrokerFactory` now wires `sasl.username`/`sasl.password` (with `SASL_SSL`/`PLAIN` defaults) when SASL credentials are configured; previously they were silently dropped.
- Fraud ring detection now connects neighbors that share a device/IP with each other instead of building target-only star graphs, and `shared_id` resolves for shared IP addresses (`coalesce(shared.id, shared.address)`).
- Kafka consumer commits every offset explicitly and records a `failed` transaction metric for decode/processing failures instead of silently dropping messages.
- `create_tables.sql` is idempotent (`CREATE INDEX IF NOT EXISTS`) and `transaction_date` is `TIMESTAMP` per the data dictionary.
- Payload normalization no longer treats a legitimate `amount` of `0` as missing, and deprecated `pd.Timestamp.utcnow()` calls were replaced with `pd.Timestamp.now(tz="UTC")`.
- PostgreSQL integration test only skips on connectivity failures instead of masking any error as a skip.
- Inference feature frame now passes `None` instead of `pd.NA` for missing input columns, fixing a `TypeError` in the sklearn imputer that turned `/predict` into a 500 whenever a payload omitted model input columns.
- Normalized rolling-window units for pandas >= 3.0 (`7d` → `7D` at parse time only) via a new `pandas_window()` helper, removing deprecation warnings from `parse_windows`, rolling aggregates, and the stateful feature store.
- `train_and_save(model=...)` now accepts `xgboost`/`random_forest` aliases and raises `ValueError` for unknown model names instead of silently writing empty metrics with no saved model.

### Security
- Pinned `starlette>=1.3.1` in override-dependencies to resolve High severity CVE-2026-54283.
- Pinned `pydantic-settings>=2.14.2` in override-dependencies to resolve Moderate severity GHSA-4xgf-cpjx-pc3j.
- Updated the optional Apache Airflow integration to `>=3.3.1` to resolve five known advisories in 3.2.2 plus eight PYSEC-2026 advisories in 3.3.0.
- Updated the lockfile to Click 8.4.2 and Pillow 12.3.0, resolving the known advisories for Click 8.3.1 and Pillow 12.2.0.
- Pinned `cryptography>=50.0.0` to resolve the High severity PKCS#7 Bleichenbacher oracle advisory (GHSA-g6cj-pr64-35w5).
- Pinned `sqlparse>=0.6.0` to resolve four advisories (ReDoS/CPU DoS/quadratic grouping/snippet breakout).
- Pinned `aiosmtplib>=5.1.2` to resolve the STARTTLS response injection advisory (GHSA-vxj7-4xrp-5vr4).
- Pinned `setuptools>=83.0.0` to resolve the MANIFEST.in Unicode normalization bypass (GHSA-h35f-9h28-mq5c).
- Removed the unused Snowflake Airflow provider and its large transitive tree.
- Removed the orphaned `pyopenssl` override-dependencies entry (package is not in the dependency graph).
- Removed embedded Docker Compose credentials, disabled unneeded Neo4j APOC file import/export settings, bound development ports to loopback, and run the application image as an unprivileged user.
- Prevented caller-controlled fraud labels from entering online features and removed label-derived merchant fraud-rate features to avoid poisoning and target leakage.

### Tests
- `test_fraud_ring_detector.py`: 14 tests covering subgraph extraction, ring detection, neighbor-to-neighbor graph construction, graceful degradation, risk scoring, and ring ID determinism.
- `test_monitoring_metrics.py`: 13 tests covering collector initialization, prediction recording, drift monitoring, and singleton behavior.
- `test_broker_abstraction.py`: 19 tests covering Kafka/Redpanda factory creation, config defaults, overrides, SASL credential wiring, dispatcher, and convenience functions.
- `test_graph_repository.py`: 6 tests covering upsert validation, null device/IP handling, and entity risk scoring.
- `test_kafka_consumer.py`: 3 tests covering commit behavior on success, handler failure, and malformed payloads.
- `test_inference_api.py`: 2 tests covering the hybrid prediction flow and metrics availability.
- `test_postgresql.py`: integration test validating ingestion against a live PostgreSQL instance (skips when `FRAUDSHIELD_DATABASE_URL` is unset).
- `test_realtime_architecture.py`: 2 new tests for ring detector integration in `HybridRiskEngine`.
- `test_transaction_features.py`: added coverage for `pandas_window()` day-unit normalization.
- `test_model_training.py`: 2 new tests covering `train_and_save` model aliases and unknown-model rejection.

## [2.3.0] - 2026-06-15

### Added
- Native Data Drift Validation task (KS test) inserted into the Airflow DAG to catch distributional shifts.
- Shared runtime settings and resource factories for SQL, Kafka, Neo4j, Airflow, and model artifacts.
- Inference service that loads trained model, preprocessor, and preprocessing metadata together.
- Stateful streaming aggregates for rolling counts, sums, means, fraud rates, and user-level running statistics.
- Idempotent Neo4j graph persistence with `MERGE`-based writes.
- Startup smoke tests for the API, Airflow DAG import, and inference artifact loading.
- FastAPI inference API with `/predict` and `/health` endpoints.
- Real-time orchestrator combining Kafka streaming, ML inference, Neo4j graph risk, and hybrid risk scoring.
- Centralized runtime logging with rotating file handlers.
- Ruff configuration in `pyproject.toml` and a `ruff` environment in `tox.ini`.
- mypy type checking in `pyproject.toml`, `tox.ini`, CI pipeline, and `Makefile`.
- `MANIFEST.in` for proper source distribution packaging.
- `SECURITY.md` with vulnerability reporting guidelines and supported versions.
- `CODE_OF_CONDUCT.md` using the Contributor Covenant v2.1.
- Synthetic data generator improvements: 5,000 transactions, 15 fraudster users, 8 high-risk merchants, multi-factor fraud patterns.
- `is_international` and `is_online` columns to the transactions schema and synthetic data.
- `pytest.ini` markers for `slow`, `integration`, and `smoke` test categories.

### Changed
- Moved `apache-airflow` from hard dependency to optional extra (`pip install fraudshield[airflow]`).
- Moved `pytest` from core dependencies to `[dev]` optional extra.
- Replaced Flake8, Pylint, and Black with Ruff for linting and formatting.
- Fixed PyPI classifier from `Build Tools` to `Scientific/Engineering :: Artificial Intelligence`.
- Changed development status from `Production/Stable` to `Beta`.
- Airflow DAG task wiring defers variable resolution to execution time via zero-arg callables.
- Model deployment task validates inference artifacts instead of being a placeholder.
- C++ data preprocessing now uses cleaned array min/max for outlier bounds instead of recomputing from scratch.
- C++ feature engineering module documented as experimental (not used in default pipeline).
- CI lint job uses Ruff and mypy instead of Flake8/Pylint with `|| true` silencing.
- CI deploy job uses twine upload instead of a comment placeholder.
- Rewrote all 8 docs files (`quick_start.md`, `setup_instructions.md`, `model_architecture.md`, `security_and_quality.md`, `cpp_modules.md`, `data_dictionary.md`, `migration_guide.md`, `sql_schema.md`).
- Updated `README.md` model evaluation metrics with actual results from 5,000-sample dataset.
- Re-executed all 3 notebooks (`01_fraudshield_pipeline_tutorial.ipynb`, `exploratory_data_analysis.ipynb`, `model_experimentation.ipynb`) with fresh outputs, fixed kernel specs (Python 3), and added cell IDs for nbformat compliance.
- EDA notebook: added explicit `fillna(0.0)` for cross-version pandas compatibility, displays mid-dataset rows where features are populated, added NaN behavior explanation.
- Model experimentation notebook: added `warnings.filterwarnings` to suppress sklearn `InconsistentVersionWarning` when loading preprocessor pickled in a different environment, added retrain note for inference demo.

### Fixed
- API model loading so the FastAPI surface initializes correctly against saved model files.
- Small-dataset preprocessing so stratified splits degrade gracefully instead of raising `ValueError`.
- Package version aligned across Python package, API version, and project metadata.
- Optional dependency handling so tests skip automatically when Airflow or SQLAlchemy are unavailable.
- mypy type errors across 10 source files (Dict return types, optional import guards, None checks).
- **Critical**: `transaction_features.py` duplicate-index bug — `groupby().apply().reset_index()` failed with `ValueError: cannot reindex on an axis with duplicate labels` when DatetimeIndex had repeated timestamps. Rewrote `_rolling_group_agg` and `_compute_user_amount_zscore` to use integer position columns (`__pos__`) instead of index alignment.

### Security
- Pinned 10 vulnerable transitive dependencies via `[tool.uv] override-dependencies`.
- Upgraded `apache-airflow` to `>=3.2.2`, `fastapi` to `>=0.136.0`, `pytest` to `>=9.0.3`.

---

## [2.2.0] - 2026-04-18

### Security
- Updated `apache-airflow` from `>=3.1.7` to `>=3.2.0` to address CVE-2025-57735, CVE-2026-33858, and CVE-2025-54550.
- Regenerated lock file with `uv lock --upgrade` to update transitive dependencies.

---

## [2.1.0] - 2026-03-14

### Changed
- Rebuilt notebooks around the current runtime/config architecture.
- Simplified `.gitignore` to focus on generated artifacts and local secrets.
- Hardened `CMakeLists.txt` with explicit C++ standard, reusable extension helper, and consistent compiler warnings.

### Fixed
- Removed import-time `logging.basicConfig(...)` calls that caused handler duplication.
- Standardized CLI and service entrypoints so logs land in predictable per-component files under `logs/`.

---

## [2.0.0] - 2026-02-21

### Added
- Initial batch pipeline for ingestion, preprocessing, training, and evaluation.
- C++ acceleration hooks for data cleaning and feature engineering via pybind11.
- Tox-based multi-version test execution and local build automation.
