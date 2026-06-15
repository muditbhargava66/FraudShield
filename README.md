<div align="center">

# FraudShield

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
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
- **Hybrid risk engine** blends ML score (0.6), graph score (0.25), and rule breaches (0.15).
- **SHAP explainability** provides per-transaction feature contributions for high-risk cases.

### Inference API

FastAPI app with two endpoints:
- `POST /predict` — Accepts a transaction, returns fraud probability, risk level, and recommended action.
- `GET /health` — Model status check.

## Key Features

- **Kafka & Neo4j integration** for real-time streaming and graph-based entity analysis
- **Explainable AI** via SHAP (TreeSHAP) for transparent scoring
- **Data drift validation** (KS test) in the Airflow DAG to catch distributional shifts before retraining
- **Data leakage prevention** in feature engineering (`closed="left"` rolling windows, `shift(1)` z-scores)
- **Time-based train/test split** to prevent temporal leakage
- **Class balancing** in model training (`scale_pos_weight`, balanced subsampling)
- **Stateful streaming aggregates** for real-time rolling counts, sums, means, and fraud rates
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
- C++ tests in `tests/cpp` run separately

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

Run linting and type checking:

```bash
make lint        # ruff check
make typecheck   # mypy
```

### Notebooks

- **[Pipeline Tutorial](notebooks/01_fraudshield_pipeline_tutorial.ipynb)** — End-to-end walkthrough
- **[Exploratory Data Analysis](notebooks/exploratory_data_analysis.ipynb)** — Data exploration and visualization
- **[Model Experimentation](notebooks/model_experimentation.ipynb)** — Training and hyperparameter tuning

## C++ Extensions

Two pybind11 modules built via CMake:

- **Data cleaning** (`data_cleaning/data_cleaning.cpp`): Missing value removal, z-score outlier removal. Used in the default preprocessing pipeline.
- **Feature engineering** (`feature_engineering/feature_engineering.cpp`): Moving average, EMA, RSI. **Experimental** — not used in the default pipeline. The default uses pandas rolling operations which are more flexible for time-based windows.

Each has a `cpp_wrapper.py` that attempts the C++ import and falls back to pure Python/NumPy if unavailable.

## Model Evaluation Results

Results on synthetic data (5,000 transactions, ~7% fraud rate) with threshold tuned for best F1.

### Random Forest

![Random Forest Confusion Matrix](data/plots/confusion_matrix_rf.png)

| Metric    | Value  |
|-----------|--------|
| Accuracy  | 0.878  |
| Precision | 0.300  |
| Recall    | 0.423  |
| F1 Score  | 0.351  |
| ROC AUC   | 0.744  |

### XGBoost

![XGBoost Confusion Matrix](data/plots/confusion_matrix_xg.png)

| Metric    | Value  |
|-----------|--------|
| Accuracy  | 0.864  |
| Precision | 0.216  |
| Recall    | 0.282  |
| F1 Score  | 0.244  |
| ROC AUC   | 0.719  |

Note: These results are on synthetic data (5,000 samples) with multi-factor fraud patterns (amount anomaly, user behavior, merchant concentration, channel combo, time-of-day). The default threshold of 0.5 yields low recall; fraud detection typically requires a lower decision threshold. Use `notebooks/model_experimentation.ipynb` to sweep thresholds for your use case.

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
