# Changelog

All notable changes to FraudShield are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.1.0] - 2026-10-08

### Added
- `tests/unit_tests/test_cpp_extensions.py`: 27 tests asserting that the compiled pybind11 extensions and their pure-Python fallbacks return identical results (missing-value removal, z-score outlier removal, moving average, EMA, RSI) and that both paths handle empty, all-NaN, constant, single-element, and out-of-range arguments the same way.
- `infra/.env.example`: template for the four variables `docker compose` requires. Compose loads `.env` from its own directory, so the root `.env.example` alone left a fresh clone unable to start the stack.
- Docker Compose healthchecks for every infrastructure service, `condition: service_healthy` startup ordering, and `restart: unless-stopped`; the app image declares a `HEALTHCHECK` against `/health`.
- Makefile `verify` (component harness) and `audit` (pip-audit on the locked all-extras export) targets; `make test-cpp` now runs the extension equivalence tests.
- CI gate for `scripts/verify_v3_components.py`, and `astral-sh/setup-uv` replacing the `python -m pip install uv` bootstrap.
- `FRAUDSHIELD_PROJECT_ROOT` environment override, documented in `.env.example` along with the previously undocumented `FRAUDSHIELD_LOG_FORMAT`, `FRAUDSHIELD_KAFKA_POLL_TIMEOUT_SECONDS`, `FRAUDSHIELD_AIRFLOW_DAGS_FOLDER`, and `FRAUDSHIELD_AIRFLOW_BASE_LOG_FOLDER`.

### Changed
- Dependency refresh: click 8.4.2 to 8.5.0, confluent-kafka 2.14.2 to 2.15.1 (librdkafka 2.15.1), joblib 1.5.3 to 1.6.0, neo4j 6.2.0 to 6.3.1, pybind11 3.0.4 to 3.1.0, pydantic 2.13.4 to 2.13.5 (pydantic-core 2.46.4 to 2.46.5), pytz 2026.2 to 2026.4, sqlalchemy 2.0.50 to 2.0.54, typing-inspection 0.4.2 to 0.4.4. Verified with ruff, mypy (43 source files), 124 passing tests locally and 125 in CI (the PostgreSQL service container makes the live integration test runnable there), the 43-check harness, a live Neo4j 6.3.1 driver run against a 5.12.0 server (graph build plus ring detection), a 25-message Kafka produce/consume roundtrip through the production consumer loop, live `/health` and `/predict` calls with SHAP explanations, and reloads of all eight committed model artifacts under joblib 1.6.0.
- FastAPI stays at 0.136.3: `apache-airflow-core` 3.3.2 (the latest release) requires `fastapi>=0.129.0,<0.137.0`, so 0.142.2 is unresolvable while the `airflow` extra is in the lock. `.github/dependabot.yml` now ignores `fastapi>=0.137` and `neo4j>=6.4` (the 6.4.0 driver has an open busy-loop regression, neo4j-python-driver#1360) until the upstream constraints change.
- The version is declared once. `fraudshield.__version__` is read from the installed distribution metadata and the FastAPI app reports it, replacing four independent copies of the string.
- Dockerfile is now a genuine two-stage build: the builder compiles the extensions with `uv sync --no-dev --no-editable --locked`, and the runtime stage contains only the resolved virtualenv plus `data/`, so no compiler toolchain ships to production. The entrypoint invokes `uvicorn` directly instead of `uv run`, which previously attempted a dependency re-sync at container start.
- Removed `EXPOSE 9090` from the image; metrics are served by the ASGI app mounted on port 8000.
- CI pins `ubuntu-24.04` (GitHub migrates `ubuntu-latest` to Ubuntu 26 on 2026-10-19), runs on `version-*` branches as well as `main`, and sets `concurrency` and `timeout-minutes`.
- `make lint`, `make format`, and the tox ruff environment now cover `scripts/` as CI does; `make install` and `make build-cpp` use `uv sync --locked` instead of `uv pip install -r requirements.txt`, removing the second source of truth for dependencies.
- `build-system.requires` pins `pybind11>=3.1.0,<3.2` so the compiled ABI matches the lockfile; pybind11 3.1.0 raised `PYBIND11_INTERNALS_VERSION` from 11 to 12, and the unpinned requirement let the isolated build environment drift from the locked version.
- Project-root resolution now detects the source layout, honors `FRAUDSHIELD_PROJECT_ROOT`, and otherwise defaults to the working directory, so a wheel install no longer resolves `data/` and the model directory inside `site-packages`. The Airflow DAGs folder default resolves inside the installed package for the same reason.
- `TransactionConsumer` sends `client.id` from `FRAUDSHIELD_KAFKA_CONSUMER_CLIENT_ID`, a setting that was declared, documented, and read by nothing.

### Fixed
- `HybridRiskEngine` normalized its weights with the builtin `sum()`, whose float behaviour changed in CPython 3.12 (Neumaier summation). On 3.10 and 3.11 `sum((0.6, 0.3, 0.1))` is `0.9999999999999999`, so every normalized weight came out one ulp high and `ml_weight` was `0.6000000000000001` rather than `0.6`. Published scores were unaffected because they are rounded to four decimals, but the risk level is chosen from the unrounded score, so a transaction sitting exactly on the 0.40 or 0.75 boundary could classify differently between runtimes. Now uses `math.fsum`, which is correctly rounded on every supported version. CI on Python 3.10 caught this; the local 3.13 suite could not.
- `calculate_exponential_moving_average` crashed the interpreter (SIGSEGV) on an empty input array: the C++ implementation wrote `ema[0]` without a bounds check, and the Python fallback raised `IndexError` for the same input. Both now return an empty array. A segfault is not catchable, so the wrapper's fallback could not mask it.
- The C++ RSI divided its initial average gain and loss by `window_size` instead of `window_size - 1`, so the extension disagreed with the Python reference on every value it produced.
- `remove_outliers` diverged on non-finite input: the C++ path returned the data unchanged because NaN poisoned the mean and no z-score comparison matched, while the Python fallback returned an empty array. Both now drop non-finite values and skip the z-score test when fewer than two finite values remain, matching the `remove_missing_values` → `remove_outliers` order the preprocessing pipeline already uses.
- `calculate_moving_average` returned `[nan]` for `window_size=0`, and `calculate_relative_strength_index` surfaced `ValueError: negative dimensions are not allowed` when the window exceeded the series length. Both now raise a clear `ValueError`, and a moving average over a series shorter than its window returns an empty array.
- `calculate_exponential_moving_average` validates `alpha` on both paths; previously only the C++ implementation rejected values outside `[0, 1]`.
- The verification harness asserted the literal string `EXPOSE 8000 9090` in the Dockerfile. It now checks the properties that matter (multi-stage layout, locked install, non-root user, healthcheck) and additionally validates compose healthchecks, restart policies, and the presence of `infra/.env.example`.
- The Airflow DAG bootstrap no longer prepends `site-packages` to `sys.path` when the package is installed instead of running from a source tree.

### Removed
- `runtime.resources.verify_sqlalchemy_engine()`, `create_kafka_producer()`, and `create_kafka_consumer()`: unused, and the latter two duplicated `streaming.broker` while silently omitting SASL credentials and `broker_type`. Use `create_broker_producer()` / `create_broker_consumer()`.
- `monitoring.setup_metrics()`: unused wrapper over `get_metrics().start_server()`.
- `FraudGraphBuilder.detect_fraud_rings()` and `FraudGraphBuilder.ring_risk()`: unused wrappers that swallowed exceptions and returned empty or zero results. Call `FraudRingDetector.detect_rings()` / `assess_account()` directly.
- The pydantic v1 `dict()` compatibility branch in `TransactionRequest.to_event()` (unreachable, since the module imports `ConfigDict` at module scope) and the SQLAlchemy 1.4 `future=True` no-op in `create_sqlalchemy_engine()`.

### Security
- Pinned `fsspec>=2026.6.0` in override-dependencies to resolve CVE-2026-104851 (GHSA-27vj-qcqg-25rc): `fsspec`'s Kerchunk `ReferenceFileSystem` rendered attacker-controlled reference JSON through unsandboxed Jinja2 templates. Transitive via `apache-airflow-task-sdk` and `universal-pathlib`, so it only reaches the optional `airflow` extra and never the runtime export; resolves to 2026.9.0. `pip-audit --strict --no-deps` is clean for both the runtime and the all-extras exports.
- The production image no longer contains `build-essential` or `cmake`, shrinking the runtime attack surface.

## [3.0.0] - 2026-10-02

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
- **Per-prediction explainability**: `POST /predict` now returns an `explanation` field with the top-5 SHAP feature contributions (null when no trained model is loaded), satisfying PRD objective 3 for every scored transaction. Endpoint latency with explanations: ~7 ms avg / ~9 ms p99.
- Drift-gate tuning knobs `min_ks_statistic` and `use_fdr` exposed through `run_data_drift_check()` and the Airflow drift task.

### Changed
- `HybridRiskEngine.evaluate_transaction()` signature extended with `account_id` parameter (backward compatible, defaults to `""`).
- Kafka advertised listeners in docker-compose updated to support both internal (`kafka:29092`) and external (`localhost:9092`) access.
- Removed obsolete `version` attribute from `infra/docker-compose.yml`.
- `Resources.py` now exposes `create_producer_via_broker()` and `create_consumer_via_broker()` convenience functions.
- Rewrote `scripts/benchmark_performance.py` against the real v3.0.0 APIs: benchmarks `cpp_wrapper` C++ vs. NumPy-fallback cleaning side by side, adds the stateful feature store, labels the inference section with the actual loaded mode, measures distinct events instead of one repeated payload, and runs Neo4j writes live when reachable (simulated otherwise).
- Drift gate now applies Benjamini-Hochberg FDR correction plus a KS effect-size floor (`min_ks_statistic=0.10`): a feature counts as drifted only when the adjusted p-value is below `drift_threshold` **and** the KS statistic shows a practically meaningful difference. The previous raw-significance test flagged ~44% of features on the shipped dataset (KS over-rejects at large n), blocking every Airflow retraining run; the corrected gate reports 27% (12/45 genuine divergences) and passes at defaults.
- Regenerated `evaluation_report*.csv` and confusion-matrix plots from the committed models, and replaced the stale README metrics tables with verified numbers at both the default (0.5) and best-F1 decision thresholds.
- Moved the working PRD and implementation-record documents out of `docs/` into the untracked local project archive; `docs/model_architecture.md` now documents the repository-layout deviation from the PRD target, and `docs/monitoring.md` records measured performance vs. PRD targets.

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
- `tests/smoke/test_startup.py` now clears the cached settings at teardown; previously the toy-model env overrides leaked into later tests, silently swapping the inference artifacts for the whole rest of the suite.

### Security
- Pinned `starlette>=1.3.1` in override-dependencies to resolve High severity CVE-2026-54283.
- Pinned `pydantic-settings>=2.14.2` in override-dependencies to resolve Moderate severity GHSA-4xgf-cpjx-pc3j.
- Updated the optional Apache Airflow integration to `>=3.3.1` to resolve five known advisories in 3.2.2 plus eight PYSEC-2026 advisories in 3.3.0.
- Updated the lockfile to Click 8.4.2 and Pillow 12.3.0, resolving the known advisories for Click 8.3.1 and Pillow 12.2.0.
- Pinned `cryptography>=50.0.0` to resolve the High severity PKCS#7 Bleichenbacher oracle advisory (GHSA-g6cj-pr64-35w5).
- Pinned `sqlparse>=0.6.0` to resolve four advisories (ReDoS/CPU DoS/quadratic grouping/snippet breakout).
- Pinned `aiosmtplib>=5.1.2` to resolve the STARTTLS response injection advisory (GHSA-vxj7-4xrp-5vr4).
- Pinned `setuptools>=83.0.0` to resolve the MANIFEST.in Unicode normalization bypass (GHSA-h35f-9h28-mq5c).
- Pinned `anyio>=4.14.2` in override-dependencies to resolve PYSEC-2026-4024 and PYSEC-2026-4025.
- Pinned `pyjwt>=2.15.0` in override-dependencies to resolve seven PYSEC-2026-414x advisories (Airflow transitive).
- Raised `urllib3>=2.8.0` in override-dependencies to resolve PYSEC-2026-4177.
- Pinned `virtualenv>=21.7.13` in override-dependencies to resolve four PYSEC-2026-401x advisories (Airflow transitive).
- Updated the optional Apache Airflow extra to `>=3.3.2` to resolve PYSEC-2026-3988, PYSEC-2026-3989, and PYSEC-2026-3990.
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
- `test_inference_api.py`: 3 tests covering the hybrid prediction flow, metrics availability, and the per-prediction SHAP explanation.
- `test_drift_hooks.py`: 4 tests covering the effect-size floor, FDR correction, gate tripping on genuine shifts, and floor opt-out.
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
