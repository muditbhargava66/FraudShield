<div align="center">

# FraudShield

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-3.1.0-blue.svg)](CHANGELOG.md)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![CI](https://github.com/muditbhargava66/FraudShield/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/muditbhargava66/FraudShield/actions/workflows/ci.yml)
[![CodeQL](https://github.com/muditbhargava66/FraudShield/actions/workflows/github-code-scanning/codeql/badge.svg?branch=main)](https://github.com/muditbhargava66/FraudShield/actions/workflows/github-code-scanning/codeql)
[![Tested with Tox: 3.10 | 3.11 | 3.12 | 3.13](https://img.shields.io/badge/Tested%20with%20Tox-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](#testing)

</div>

## Overview

FraudShield is an anomaly detection pipeline for identifying fraudulent financial transactions. It supports two execution modes: **batch processing** via CLI entry points or Airflow DAG, and **real-time streaming** via Kafka with Neo4j graph analysis.

## Architecture

The pipeline has two modes:

### Batch Pipeline

Four CLI entry points run sequentially:

1. **`fraudshield_ingest`** — Reads CSV, writes to SQL (SQLite by default), saves a processed copy.
2. **`fraudshield_preprocess`** — Applies C++ data cleaning (outlier/missing value removal via pybind11), engineers rolling-window features with leakage prevention, performs time-based train/test split, fits a sklearn preprocessor.
3. **`fraudshield_train`** — Trains Random Forest and/or XGBoost with class balancing, saves model artifacts.
4. **`fraudshield_evaluate`** — Computes metrics (accuracy, precision, recall, F1, AUC), saves evaluation report and confusion matrix.

### Real-Time Pipeline

`RealTimeOrchestrator` coordinates streaming execution:

- **Kafka producer** generates synthetic transactions.
- **Kafka consumer** polls messages and passes them to the inference service.
- **Inference service** normalizes payloads, builds stateful rolling-window features, runs model prediction. Falls back to heuristic scoring when no model is loaded.
- **Graph builder** upserts transactions into Neo4j and computes entity risk.
- **Hybrid risk engine** blends ML score (0.6), graph score (0.3), and rule breaches (0.1). Optional ring detector boosts graph score when coordinated fraud rings are detected.
- **SHAP explainability** provides per-transaction feature contributions for high-risk cases.
- **Prometheus metrics** emitted automatically: transaction throughput, inference latency, fraud probability distribution, risk levels, active fraud rings, data drift ratio, and the drifted-feature count.

### Inference API

FastAPI app with three endpoints:
- `POST /predict` — Accepts a transaction, returns fraud probability, risk level, recommended action, and a top-5 SHAP `explanation` of the driving features.
- `GET /health` — Model status check.
- `GET /metrics/` — Prometheus metrics (when monitoring is enabled).

## Key Features

- **Kafka & Neo4j integration** for real-time streaming and graph-based entity analysis
- **Fraud ring detection** via Louvain community detection on Neo4j 2-hop neighborhood subgraphs (shared devices/IPs connecting accounts)
- **Prometheus monitoring** with counters, histograms, and gauges for transactions, inference latency, fraud probability, risk levels, drift ratio, and drifted-feature count
- **Explainable AI** via SHAP (TreeSHAP) for transparent scoring
- **Data drift validation** (KS test) in the Airflow DAG to catch distributional shifts before retraining
- **Data leakage prevention** in feature engineering (`closed="left"` rolling windows, `shift(1)` z-scores)
- **Time-based train/test split** to prevent temporal leakage
- **Class balancing** in model training (`scale_pos_weight`, balanced subsampling)
- **Stateful streaming aggregates** for real-time rolling counts, sums, and means without accepting caller-supplied fraud labels
- **Pluggable broker abstraction** supporting Kafka and Redpanda backends via factory pattern
- **Optional Airflow DAG** for orchestration with runtime variable fetching
- **C++ acceleration** for data cleaning via pybind11 (feature engineering C++ is experimental)
- **FastAPI inference API** for real-time predictions

## Installation

### Option A: `uv` (recommended)

```bash
uv sync
```

### Option B: `pip`

```bash
pip install -e .
```

### With Airflow support (optional)

```bash
pip install -e ".[airflow]"
```

Airflow is an optional dependency. Install it only if you need DAG-based orchestration.

### With development tools

```bash
pip install -e ".[dev]"
```

This installs ruff, mypy, pytest, and tox for local development.

Both base install paths include FastAPI, Uvicorn, Kafka, and Neo4j drivers. For environment overrides, start from `.env.example` and export the `FRAUDSHIELD_*` variables you need.

## Quickstart

Generate the synthetic dataset (optional; the repo includes a generated CSV):

```bash
python data/raw/synthetic_fraud_data.py
```

Run the pipeline using the installed CLI entry points:

```bash
fraudshield_ingest
fraudshield_preprocess
fraudshield_train
fraudshield_evaluate
```

By default, ingestion writes to SQLite at `data/processed/fraud_data.db`. To use a different database:

```bash
fraudshield_ingest --db_connection_string postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME
```

Or run modules directly:

```bash
python -m fraudshield.data_ingestion.data_ingestion
python -m fraudshield.data_preprocessing.data_preprocessing
python -m fraudshield.model_training.train_models
python -m fraudshield.model_evaluation.evaluation
```

Run the inference API locally:

```bash
uvicorn fraudshield.ml.inference.api:app --reload
```

## Docker

The project includes a multi-stage Dockerfile and a docker-compose setup with Zookeeper, Kafka, Neo4j, PostgreSQL, Prometheus, and Grafana:

```bash
docker compose -f infra/docker-compose.yml up --build
```

Services:
- **zookeeper** (port 2181): Kafka coordination
- **kafka** (port 9092): Apache Kafka broker (Confluent 7.5.0)
- **neo4j** (ports 7474, 7687): Graph database
- **postgres** (port 5432): PostgreSQL 15 metadata and transaction store
- **fraudshield** (port 8000): FastAPI inference API and Prometheus metrics at `/metrics`
- **prometheus** (port 9091): Metrics collection and alerting
- **grafana** (port 3000): Dashboards and visualization

Every infrastructure service declares a `healthcheck`, dependents start only on `condition: service_healthy`, and all seven services use `restart: unless-stopped`.

Before starting the stack, copy both templates: `.env.example` to `.env` for the application settings, and `infra/.env.example` to `infra/.env` for the compose stack. Compose reads `.env` from the compose file's own directory (`infra/`), not from the repository root, so both files are required for a full stack run. Replace every placeholder with a unique secret and ensure `FRAUDSHIELD_DATABASE_URL` contains the URL-encoded PostgreSQL password. All ports bind to `127.0.0.1` by default.

## Monitoring

Prometheus metrics are emitted automatically when `FRAUDSHIELD_MONITORING_ENABLED=true`:

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `fraudshield_transactions_total` | Counter | source, status | Total transactions processed |
| `fraudshield_inference_latency_seconds` | Histogram | model_name, source | Inference latency per prediction |
| `fraudshield_fraud_probability` | Histogram | — | Distribution of fraud probability scores |
| `fraudshield_risk_level_total` | Counter | level | Predictions grouped by risk level (HIGH/MEDIUM/LOW) |
| `fraudshield_active_fraud_rings` | Gauge | — | Current number of detected fraud rings |
| `fraudshield_drift_ratio` | Gauge | — | Latest data drift ratio from KS-test |
| `fraudshield_drifted_features` | Gauge | — | Number of features that drifted beyond threshold |

Grafana is available at `localhost:3000`; use the password configured as `FRAUDSHIELD_GRAFANA_ADMIN_PASSWORD` in `infra/.env`.

## Preprocessing & Feature Engineering

`fraudshield_preprocess` will:

- Use a **time-based train/test split** if `transaction_date` exists (prevents temporal leakage)
- Otherwise fall back to a random split (optionally stratified)
- Build rolling-window features with **data leakage prevention**:
  - Uses `closed="left"` to exclude current transaction
  - Z-scores computed with `shift(1)` to exclude current values
  - Sample standard deviation (`ddof=1`) for statistical correctness

CLI options:

- `--feature_windows`: comma list like `1h,24h,7d,30d`, or `auto` (default), or `none`
- `--id_columns`: comma list of identifier columns to drop, or `auto` (default), or `none`

Examples:

```bash
fraudshield_preprocess --feature_windows 1h,24h,7d
fraudshield_preprocess --feature_windows none --id_columns none
```

### Configuration

Runtime configuration flows through environment variables with `FRAUDSHIELD_*` prefix:

```bash
export FRAUDSHIELD_DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME
export FRAUDSHIELD_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export FRAUDSHIELD_NEO4J_URI=neo4j://localhost:7687
export FRAUDSHIELD_NEO4J_USERNAME=neo4j
export FRAUDSHIELD_NEO4J_PASSWORD=your_password
export FRAUDSHIELD_KAFKA_BROKER_TYPE=kafka      # or "redpanda"
export FRAUDSHIELD_MONITORING_ENABLED=true       # enable Prometheus metrics
export FRAUDSHIELD_MONITORING_PORT=9090         # metrics HTTP port
```

## Airflow (Optional)

DAGs live in `src/fraudshield/data_pipeline/airflow_dags/`. The default local configuration uses `SequentialExecutor` with a project-local SQLite metadata DB. The DAG includes six tasks: `data_ingestion`, `data_preprocessing`, `data_drift`, `model_training`, `model_evaluation`, and `model_deployment`.

To use Airflow locally:

```bash
pip install -e ".[airflow]"
export AIRFLOW_HOME=.airflow
airflow db migrate
airflow dags list
```

If you switch to `LocalExecutor`, switch the Airflow metadata database off SQLite first.

## Testing

- **pytest** for unit, integration, and smoke tests (markers: `slow`, `integration`, `smoke`)
- **tox** for multi-version testing (3.10, 3.11, 3.12, 3.13)
- **ruff** for linting and formatting
- **mypy** for type checking
- **C++ extensions** are covered by `tests/unit_tests/test_cpp_extensions.py` (27 tests), which asserts the compiled pybind11 path and the pure-Python fallback return identical results. The GoogleTest sources under `tests/cpp/` are not wired into any CMake target, so nothing compiles or runs them.

The suite reports 123 passed and 1 skipped; the skip is the live-PostgreSQL integration test, which runs only when `FRAUDSHIELD_DATABASE_URL` points at a reachable database. CI runs Python 3.10 only, while `tox` covers 3.10-3.13.

Run all tests:

```bash
pytest tests/ -v
```

Run across Python versions:

```bash
tox
```

Run specific test categories:

```bash
pytest tests/unit_tests/ -v
pytest tests/integration_tests/ -v
pytest tests/smoke/ -v
```

Run the C++ extension equivalence tests, the component verification harness, and the dependency audit:

```bash
make test-cpp   # pytest tests/unit_tests/test_cpp_extensions.py
make verify     # python scripts/verify_v3_components.py (43 checks)
make audit      # pip-audit against the locked all-extras export
```

Run linting and type checking:

```bash
make lint        # ruff check src tests scripts
make typecheck   # mypy
```

### Notebooks

- **[Pipeline Tutorial](notebooks/01_fraudshield_pipeline_tutorial.ipynb)** — End-to-end batch pipeline: ingestion, preprocessing, drift gate, XGBoost training, evaluation, scoring a new event, and SHAP explanations
- **[Real-Time Streaming & Graph](notebooks/02_realtime_streaming_and_graph.ipynb)** — Kafka/Redpanda broker factories, stateful streaming features, Louvain fraud-ring detection, hybrid risk scoring, and the in-process inference API
- **[Exploratory Data Analysis](notebooks/exploratory_data_analysis.ipynb)** — Fraud balance, amount and temporal patterns, merchant/channel risk, and rolling-feature correlations
- **[Model Experimentation](notebooks/model_experimentation.ipynb)** — Class-weighting experiments, decision-threshold sweep for best F1, and a Random Forest baseline

All four execute cleanly end-to-end against the v3 codebase.

### Scripts

- `scripts/benchmark_performance.py` — TPS/latency benchmarks for C++ vs. NumPy data cleaning, the stateful feature store, the inference service, the hybrid risk engine, and Neo4j writes (live when reachable, simulated otherwise)
- `scripts/verify_v3_components.py` — 43-check validation harness covering every v3 component and its integration with the batch pipeline

## C++ Extensions

Two pybind11 modules built via CMake:

- **Data cleaning** (`data_cleaning/data_cleaning.cpp`): Missing value removal, z-score outlier removal. Used in the default preprocessing pipeline.
- **Feature engineering** (`feature_engineering/feature_engineering.cpp`): Moving average, EMA, RSI. **Experimental** — not used in the default pipeline. The default uses pandas rolling operations which are more flexible for time-based windows.

Each has a `cpp_wrapper.py` that attempts the C++ import and falls back to pure Python/NumPy if unavailable.

## Model Evaluation Results

Verified against the committed artifacts in `data/models/` (synthetic data: 5,000 transactions, ~7% fraud rate; 1,000-row test split at 7.8% fraud). Reports are regenerated with `fraudshield_evaluate`; the confusion matrices below show the default 0.5 decision threshold.

### Random Forest

![Random Forest Confusion Matrix](data/plots/confusion_matrix_rf.png)

| Metric            | Default (0.5) | Tuned (0.14, best F1) |
|-------------------|---------------|-----------------------|
| Accuracy          | 0.922         | 0.857                 |
| Precision         | 0.000         | 0.259                 |
| Recall            | 0.000         | 0.449                 |
| F1 Score          | 0.000         | 0.329                 |
| ROC AUC           | 0.751         | —                     |
| Average Precision | 0.237         | —                     |

### XGBoost

![XGBoost Confusion Matrix](data/plots/confusion_matrix_xg.png)

| Metric            | Default (0.5) | Tuned (0.05, best F1) |
|-------------------|---------------|-----------------------|
| Accuracy          | 0.912         | 0.863                 |
| Precision         | 0.273         | 0.214                 |
| Recall            | 0.077         | 0.282                 |
| F1 Score          | 0.120         | 0.243                 |
| ROC AUC           | 0.709         | —                     |
| Average Precision | 0.191         | —                     |

Note: These results are on synthetic data with multi-factor fraud patterns (amount anomaly, user behavior, merchant concentration, channel combo, time-of-day). At the default threshold of 0.5 the Random Forest predicts no fraud at all — fraud detection typically requires a lower decision threshold, which roughly doubles F1 for both models. Use `notebooks/model_experimentation.ipynb` to sweep thresholds for your use case.

---

<div align="center">

## Star History

<a href="https://www.star-history.com/#muditbhargava66/FraudShield&type=date&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=muditbhargava66/FraudShield&type=date&theme=dark&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=muditbhargava66/FraudShield&type=date&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=muditbhargava66/FraudShield&type=date&legend=top-left" />
 </picture>
</a>

**Star this repo if you find it useful!**

**Contact**: [@muditbhargava66](https://github.com/muditbhargava66) |
**Report Issues**: [Issue Tracker](https://github.com/muditbhargava66/FraudShield/issues) |
**Security**: [SECURITY.md](SECURITY.md) |
**Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)

© 2026 Mudit Bhargava. [MIT](LICENSE)
<!-- Copyright symbol using HTML entity for better compatibility -->

</div>
