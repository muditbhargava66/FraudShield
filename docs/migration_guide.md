# Migration Guide: v2.2.0 → v2.3.0 → v3.0.0 → v3.1.0

## Overview of Changes

- **Tooling**: Replaced flake8/pylint/black with ruff + mypy
- **Data**: New synthetic data generator (5,000 transactions, multi-factor fraud)
- **Schema**: Added `is_international` and `is_online` columns
- **Features**: Fixed duplicate-index bug in rolling window computation
- **Config**: Added `[tool.mypy]` and `[tool.ruff]` to `pyproject.toml`

## Breaking Changes

### 1. Database Schema

Two new columns added to the `transactions` table:

```sql
is_international BOOLEAN NOT NULL DEFAULT 0,
is_online        BOOLEAN NOT NULL DEFAULT 1,
```

**Action**: Delete old SQLite DB and re-ingest:

```bash
rm data/processed/fraud_data.db data/processed/ingested_data.csv
uv run python data/raw/synthetic_fraud_data.py
uv run fraudshield_ingest
```

### 2. Feature Engineering

The `_rolling_group_agg` and `_compute_user_amount_zscore` functions now use integer position columns (`__pos__`) instead of DatetimeIndex alignment. This fixes a `ValueError: cannot reindex on an axis with duplicate labels` error that occurred with larger datasets.

The API is unchanged — `add_transaction_features(df, config)` works the same way.

**Action**: Re-preprocess and retrain models:

```bash
uv run fraudshield_preprocess
uv run fraudshield_train --model both
```

### 3. Linting Toolchain

| Old | New |
|-----|-----|
| `flake8 src tests` | `ruff check src tests` |
| `pylint src/` | `mypy src/` |
| `black src tests` | `ruff format src tests` |

**Action**: Update CI configs and IDE settings:

```bash
# Run new linters
uv run ruff check src tests
uv run mypy src/
uv run ruff format --check src tests
```

### 4. Synthetic Data

The old generator produced 1,000 samples with simplistic fraud patterns. The new generator produces 5,000 samples with:

- 15 designated fraudster users
- 8 high-risk merchants
- Multi-factor fraud: amount, user behavior, merchant, channel, time-of-day
- ~7% fraud rate

**Action**: Regenerate data and retrain. Model metrics will differ from v2.2.0.

## Migration Steps

```bash
# 1. Pull latest
git checkout version-2.3.0
git pull

# 2. Reinstall (picks up new ruff/mypy configs)
uv pip install -e ".[dev]"

# 3. Regenerate data
uv run python data/raw/synthetic_fraud_data.py

# 4. Run full pipeline
uv run fraudshield_ingest
uv run fraudshield_preprocess
uv run fraudshield_train --model both
uv run fraudshield_evaluate --model_path data/models/xgboost.pkl

# 5. Verify quality
uv run pytest tests/ -v
uv run ruff check src tests
uv run mypy src/
```

## Expected Model Performance

With the v2.3.0 synthetic data:

| Model | ROC-AUC | Precision@0.3 | Recall@0.3 |
|-------|---------|---------------|------------|
| Random Forest | ~0.76 | ~0.24 | ~0.40 |
| XGBoost | ~0.72 | ~0.25 | ~0.12 |

At default threshold (0.5), recall is low because fraud detection typically requires a lower decision threshold. Use the threshold sweep in `notebooks/model_experimentation.ipynb` to find the right operating point.

## Rollback

```bash
git checkout version-2.2.0
uv pip install -e .
uv run fraudshield_ingest
uv run fraudshield_preprocess
uv run fraudshield_train --model both
```

---

## v2.3.0 → v3.0.0

### Overview of Changes

- **Fraud ring detection**: New `graph/fraud_ring_detector.py` with Louvain community detection on Neo4j 2-hop subgraphs
- **Prometheus monitoring**: New `monitoring/metrics.py` with counters, histograms, and gauges
- **Drift hooks**: New `monitoring/drift_hooks.py` with KS-test + streaming z-score hooks
- **Broker abstraction**: New `streaming/broker.py` with `BrokerFactory` ABC supporting Kafka and Redpanda
- **Docker stack**: New `Dockerfile`, plus PostgreSQL, Prometheus, and Grafana services in docker-compose
- **Dependencies**: Added `networkx>=3.2` and `prometheus_client>=0.21.0`

### Breaking Changes

**None.** All v3.0.0 changes are additive:
- `HybridRiskEngine.evaluate_transaction()` gains an optional `account_id` parameter (defaults to `""`).
- `KafkaSettings` gains a `broker_type` field (defaults to `"kafka"`).
- `RuntimeSettings` gains a `monitoring: MonitoringSettings` field (defaults to enabled on port 9090).

### Migration Steps

```bash
# 1. Pull latest
git checkout version-3.1.0

# 2. Reinstall (picks up networkx + prometheus_client)
uv sync

# 3. Verify all components
uv run python scripts/verify_v3_components.py

# 4. Run full pipeline (unchanged)
uv run fraudshield_ingest
uv run fraudshield_preprocess
uv run fraudshield_train --model both
uv run fraudshield_evaluate --model_path data/models/xgboost.pkl

# 5. Verify quality
uv run pytest tests/ -v
uv run ruff check src tests scripts
uv run mypy src/

# 6. (Optional) Start full Docker stack
cp .env.example .env                 # application settings, repository root
cp infra/.env.example infra/.env     # compose stack secrets
# Edit both: FRAUDSHIELD_NEO4J_PASSWORD, FRAUDSHIELD_POSTGRES_PASSWORD,
# FRAUDSHIELD_DATABASE_URL, FRAUDSHIELD_GRAFANA_ADMIN_PASSWORD are required
cd infra
docker compose up -d
```

### New Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FRAUDSHIELD_MONITORING_ENABLED` | `true` | Enable Prometheus metrics |
| `FRAUDSHIELD_MONITORING_PORT` | `9090` | Metrics HTTP port |
| `FRAUDSHIELD_MONITORING_METRICS_PATH` | `/metrics` | Metrics URL path |
| `FRAUDSHIELD_KAFKA_BROKER_TYPE` | `kafka` | Broker backend (`kafka` or `redpanda`) |
| `FRAUDSHIELD_KAFKA_SASL_USERNAME` | (empty) | SASL username; enables SASL on the Kafka factory when set |
| `FRAUDSHIELD_KAFKA_SASL_PASSWORD` | (empty) | SASL password |

### Behavioral Notes

- **Model naming**: `train_and_save(..., model=...)` now uses `rf` / `xgb` / `both`
  as the canonical values. The v2.x names `random_forest` and `xgboost` are still
  accepted as aliases, so existing `fraudshield_train --model both` / `--model xgboost`
  commands keep working; unknown values raise `ValueError`.
- **pandas 3.x window units**: `transaction_features.pandas_window()` normalizes
  day-unit windows (`'7d'` -> `'7D'`) for pandas >= 3.0 compatibility. Feature
  names keep the original unit string (`user_txn_count_7d`, `merchant_amount_mean_7d`, ...),
  so persisted feature columns do not change. Use `pandas_window()` when converting
  window strings for pandas APIs.
- **Inference API payload**: `POST /predict` requires `transaction_id` as a string
  (e.g. `"tx-1001"`), unlike the `BIGINT` column in the SQL `transactions` table.
  Extra/unknown fields are rejected (`extra="forbid"`), including caller-supplied
  fraud labels.
- **Broker abstraction**: both Kafka and Redpanda use `confluent-kafka` (Kafka wire
  protocol). `RedpandaBrokerFactory` defaults to `security.protocol=SASL_SSL` and
  `sasl.mechanisms=SCRAM-SHA-256`; `KafkaBrokerFactory` only adds SASL
  (`SASL_SSL` + `PLAIN`) when `FRAUDSHIELD_KAFKA_SASL_USERNAME` is set. All defaults
  are overridable via keyword overrides in `create_broker_producer()` /
  `create_broker_consumer()`.
- **Hybrid risk engine**: default blend weights are ML 0.6 / graph 0.3 / rules 0.1.
  The composite score is raised to at least 0.95 when all rules breach or the graph
  score >= 0.95. Risk levels: `HIGH` >= 0.75 (action `BLOCK`), `MEDIUM` >= 0.40,
  else `LOW` (`ALLOW`). The fraud ring detector (Louvain over the Neo4j 2-hop
  neighborhood) is blended into the graph score via `assess_account()`.
- **Docker stack**: `infra/docker-compose.yml` reads `infra/.env` and fails fast if
  `FRAUDSHIELD_NEO4J_PASSWORD`, `FRAUDSHIELD_POSTGRES_PASSWORD`,
  `FRAUDSHIELD_DATABASE_URL`, or `FRAUDSHIELD_GRAFANA_ADMIN_PASSWORD` is missing.

### Rollback

```bash
git checkout version-2.3.0
uv pip install -e .
uv run fraudshield_ingest
uv run fraudshield_preprocess
uv run fraudshield_train --model both
```

---

## v3.0.0 → v3.1.0

### Overview of Changes

- **Dependency refresh**: click 8.5.0, confluent-kafka 2.15.1, joblib 1.6.0,
  neo4j 6.3.1, pybind11 3.1.0, pydantic 2.13.5 (pydantic-core 2.46.5),
  pytz 2026.4, sqlalchemy 2.0.54, typing-inspection 0.4.4. FastAPI is held at
  0.136.3 because `apache-airflow-core` 3.3.2 requires `fastapi<0.137.0`.
- **Security pin**: `fsspec>=2026.6.0` added to `[tool.uv] override-dependencies`
  for CVE-2026-104851.
- **Single version source**: `fraudshield.__version__` is read from the installed
  distribution metadata (`pyproject.toml` declares 3.1.0) and passed to
  `FastAPI(version=...)`.
- **Container**: the Dockerfile is a genuine two-stage build, runs as the
  unprivileged `fraudshield` user, declares a `HEALTHCHECK` against `/health`,
  exposes 8000 only, and starts `uvicorn` directly.
- **Compose stack**: healthchecks on every infrastructure service,
  `condition: service_healthy` startup ordering, `restart: unless-stopped`, and a
  tracked `infra/.env.example` template.
- **Tests**: 27 new C++ extension equivalence tests in
  `tests/unit_tests/test_cpp_extensions.py`. The suite reports 124 passed,
  1 skipped.
- **CI**: runs on `ubuntu-24.04` with `astral-sh/setup-uv@v10.0.0` and gates on
  `scripts/verify_v3_components.py` (43 checks) in addition to ruff, mypy, pytest,
  `python -m build`, and pip-audit.

### Removed APIs

| Removed in 3.1.0 | Use instead |
|---|---|
| `fraudshield.runtime.resources.verify_sqlalchemy_engine` | No replacement. Issue `SELECT 1` against the engine from `create_sqlalchemy_engine()` yourself. |
| `fraudshield.runtime.resources.create_kafka_producer` | `fraudshield.streaming.broker.create_broker_producer` |
| `fraudshield.runtime.resources.create_kafka_consumer` | `fraudshield.streaming.broker.create_broker_consumer` |
| `fraudshield.monitoring.setup_metrics` | `fraudshield.monitoring.get_metrics().start_server()` |
| `FraudGraphBuilder.detect_fraud_rings` | `FraudRingDetector.detect_rings()`, reachable via the `FraudGraphBuilder.ring_detector` attribute (`None` when Neo4j is unavailable) |
| `FraudGraphBuilder.ring_risk` | `FraudRingDetector.assess_account()`, reachable via the same `ring_detector` attribute |

The `streaming.broker` factories are the only supported path for Kafka and
Redpanda clients; the removed `resources` helpers duplicated them while omitting
SASL credentials and `broker_type`.

### C++ Extension Fixes

- `calculate_exponential_moving_average` crashed the interpreter (SIGSEGV) on an
  empty input array: the C++ implementation wrote `ema[0]` without a bounds check,
  and the Python fallback raised `IndexError` for the same input. Both now return
  an empty array. A segfault is not catchable, so the wrapper's fallback could not
  mask it.
- The C++ RSI divided its initial average gain and loss by `window_size` instead of
  `window_size - 1`, so the extension disagreed with the Python reference on every
  value it produced. The divisor now matches the Python reference.
- `remove_outliers` diverged on non-finite input: the C++ path returned the data
  unchanged because NaN poisoned the mean, while the Python fallback returned an
  empty array. Both implementations now drop non-finite values and skip the z-score
  test when fewer than two finite values remain.
- Explicit argument validation on both paths: `calculate_moving_average` and
  `calculate_relative_strength_index` raise `ValueError` for non-positive or
  out-of-range windows, and `calculate_exponential_moving_average` validates
  `alpha` against `[0, 1]`. Previously only the C++ implementation rejected an
  out-of-range `alpha`.

`make test-cpp` runs `tests/unit_tests/test_cpp_extensions.py`, which asserts the
compiled pybind11 extensions and the pure-Python fallbacks produce identical
results. The GoogleTest sources under `tests/cpp/` are not wired into any CMake
target, so nothing compiles or runs them.

### Migration Steps

```bash
# 1. Pull latest
git checkout version-3.1.0

# 2. Reinstall from the lockfile and rebuild the C++ extensions
uv sync --all-extras --locked
make build-cpp

# 3. Verify quality
uv run pytest tests/ -q          # 124 passed, 1 skipped
uv run ruff check src tests scripts
uv run mypy src/
make verify                      # 43-check component harness
make audit                       # pip-audit on the locked all-extras export

# 4. Run the pipeline (unchanged)
uv run fraudshield_ingest
uv run fraudshield_preprocess
uv run fraudshield_train --model both
uv run fraudshield_evaluate --model_path data/models/xgboost.pkl
```

For the Docker stack, copy both templates before starting it: `.env.example` to
`.env` for the application settings, and `infra/.env.example` to `infra/.env` for
the compose stack. Compose reads `.env` from the compose file's own directory.

### Rollback

```bash
git checkout version-3.0.0
uv sync
uv run fraudshield_ingest
uv run fraudshield_preprocess
uv run fraudshield_train --model both
```

---
