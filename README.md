<div align="center">

# FraudShield

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![CodeQL](https://github.com/muditbhargava66/FraudShield/actions/workflows/github-code-scanning/codeql/badge.svg?branch=main)](https://github.com/muditbhargava66/FraudShield/actions/workflows/github-code-scanning/codeql)
[![CI](https://github.com/muditbhargava66/FraudShield/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/muditbhargava66/FraudShield/actions/workflows/ci.yml)
[![Linting: Flake8 & Pylint](https://img.shields.io/badge/Linting-Flake8%20%7C%20Pylint-success)](#testing)
[![Tested with Tox: 3.10 | 3.11 | 3.12 | 3.13](https://img.shields.io/badge/Tested%20with%20Tox-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](#testing)

</div>

## Overview
FraudShield is an advanced anomaly detection pipeline designed to identify and prevent fraudulent activities within large datasets. By leveraging cutting-edge machine learning techniques, efficient C++ data processing modules, and a robust SQL-based data storage and retrieval system, FraudShield ensures the integrity and security of financial transactions.

## Architecture
The FraudShield pipeline consists of the following synergistic components forming a complete end-to-end framework:
1. **Real-time Streaming Ingestion**: High-throughput transaction ingestion via Kafka/Redpanda bypassing legacy batch bottlenecks.
2. **Graph Detection Engine**: Deep entity monitoring using Neo4j to isolate rings by connecting Devices, IPs, and Accounts securely.
3. **Data Cleaning and Preprocessing**: Polished C++ capabilities handling rapid normalization, outlier identification, and windowed aggregation mapping natively.
4. **Hybrid Risk Engine**: Evaluates transactions seamlessly by blending Machine Learning (Random Forest, XGBoost), rule-bounds, and Graph signals into a unified prediction.
5. **SHAP Explainability**: Fully integrated explainability arrays providing dynamic, localized insights explaining high-risk anomalies automatically.
6. **Monitoring and Alerting**: Standard Airflow & deployment topologies monitoring matrix integrity.

## Key Features

- **Kafka & Neo4j Integration**: Natively scalable real-time streaming and graph network detections.
- **Explainable AI (XAI)**: Immediate transparent scoring evaluations via `shap` computations.
- Transactional schema sample data generator (`data/raw/synthetic_fraud_data.py`)
- **Secure SQL/Stream bindings** tracking high frequency inputs autonomously.
- Preprocessing with **time-based split** to prevent temporal leakage
- **Data leakage prevention** in feature engineering (rolling-window user/merchant/currency aggregates)
- Model training (Random Forest, XGBoost) with **class balancing** and evaluation utilities
- Optional Airflow DAG for orchestration with **runtime variable fetching**
- **Production-ready C++ modules** with bounds checking and safety improvements
- Comprehensive error handling and unified testing matrices

## Installation

Option A (recommended): `uv`

```bash
uv sync
```

Option B: `pip`

```bash
python -m pip install -e .
```

Both paths now install the API/runtime dependencies as well, including FastAPI, Uvicorn, Airflow, Kafka, and Neo4j drivers.

If you need environment overrides, start from `.env.example` and export the `FRAUDSHIELD_*` variables you need.

## Quickstart

Generate the synthetic dataset (optional; the repo includes a generated CSV already):

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

By default, ingestion writes to SQLite at `data/processed/fraud_data.db`. To use a different database, pass a SQLAlchemy URL:

```bash
fraudshield_ingest --db_connection_string postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME
```

If you prefer running modules directly:

```bash
python -m fraudshield.data_ingestion.data_ingestion
python -m fraudshield.data_preprocessing.data_preprocessing
python -m fraudshield.model_training.train_models
python -m fraudshield.model_evaluation.evaluation
```

Run the inference API locally:

```bash
uv run uvicorn fraudshield.ml.inference.api:app --reload
```

## Preprocessing & Feature Engineering

`fraudshield_preprocess` will:

- Use a **time-based train/test split** if `transaction_date` exists and is non-null (prevents temporal leakage)
- Otherwise fall back to a random split (optionally stratified)
- Build rolling-window features with **data leakage prevention**:
  - Uses `closed="left"` to exclude current transaction
  - Z-scores computed with `shift(1)` to exclude current values
  - Sample standard deviation (ddof=1) for statistical correctness
  - Explicit division by zero handling

Important CLI options:

- `--feature_windows`: comma list like `1h,24h,7d,30d`, or `auto` (default), or `none`
- `--id_columns`: comma list of identifier columns to drop, or `auto` (default), or `none`

Examples:

```bash
fraudshield_preprocess --feature_windows 1h,24h,7d
fraudshield_preprocess --feature_windows none --id_columns none
```

**Security Note**: Database and runtime configuration now flow through the shared `FRAUDSHIELD_*` settings layer. For example:

```bash
export FRAUDSHIELD_DATABASE_URL=postgresql+psycopg2://USER:PASSWORD@HOST:5432/DBNAME
export FRAUDSHIELD_KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export FRAUDSHIELD_NEO4J_URI=neo4j://localhost:7687
export FRAUDSHIELD_NEO4J_USERNAME=neo4j
export FRAUDSHIELD_NEO4J_PASSWORD=your_password
```

## Airflow (Optional)

- DAGs live in `src/fraudshield/data_pipeline/airflow_dags/`.
- A sample Airflow config is in `airflow/airflow.cfg`.
- The default local configuration uses `SequentialExecutor` with a project-local SQLite metadata DB.

To use Airflow locally:

```bash
export AIRFLOW_HOME=.airflow
airflow db migrate
airflow dags list
```

If you switch to `LocalExecutor`, also switch Airflow metadata off SQLite to a real database first.

## Testing

- Python testing & isolated environments: `tox` (3.10, 3.11, 3.12, 3.13)
- Standard test runner: `pytest`
- C++ tests: located in `tests/cpp` and run separately with GoogleTest

Run all unit tests in isolated environments for multiple Python versions:
```bash
tox
```

### Notebooks

- **[Updated Best Practices](notebooks/updated_best_practices.ipynb)** - Interactive guide to security and quality improvements
- **[Exploratory Data Analysis](notebooks/exploratory_data_analysis.ipynb)** - Data exploration and visualization
- **[Model Experimentation](notebooks/model_experimentation.ipynb)** - Model training and hyperparameter tuning

## Recent Improvements (v2.0)

### Critical Fixes
-  **Data Leakage Prevention**: Fixed z-score calculation to exclude current transaction
-  **SQL Injection Protection**: Secure database connections using SQLAlchemy URL builder
-  **Buffer Overflow Prevention**: Fixed C++ modules with proper bounds checking
-  **Index Out of Bounds**: Added validation in moving average calculations

### Security Enhancements
-  Parameterized SQL queries throughout
-  Environment-based credential management
-  Improved error handling without information disclosure
-  NULL pointer validation in C++ modules

### Data Quality Improvements
-  Time-based splitting for temporal data
-  Sample standard deviation for statistical correctness
-  Explicit division by zero handling
-  Label encoding validation

### Performance Optimizations
-  Prediction caching (50% reduction in redundant calls)
-  Runtime variable fetching in Airflow DAGs
-  Efficient memory management in C++ modules

### Architectural Code Simplification
-  **Redundancy Eliminated**: Enforced static memory allocations across C++ missing-value/outlier removal integrations.
-  **Unified Testing**: Rewired the `Makefile` test targets combining unit tests, end-to-end integration tests, and C++ extensions natively through scoped `uv run` loops circumventing virtual environment bindings.
-  **Tutorial Validation**: Re-generated Python notebook outputs fixing nested string execution states within `01_fraudshield_pipeline_tutorial.ipynb` and `exploratory_data_analysis.ipynb`.

## Model Evaluation Results

The trained models were evaluated on a separate test dataset using various performance metrics. Here are the evaluation results for the Random Forest and XGBoost models:

### Random Forest Model
![Random Forest Confusion Matrix](data/plots/confusion_matrix_rf.png)

| Metric     | Value                |
|------------|----------------------|
| Accuracy   | 0.95                 |
| Precision  | 0.9333333333333333   |
| Recall     | 0.9545454545454546   |
| F1 Score   | 0.9438202247191011   |
| AUC        | 0.9864549512987013   |

### XGBoost Model
![XGBoost Confusion Matrix](data/plots/confusion_matrix_xg.png)

| Metric     | Value                |
|------------|----------------------|
| Accuracy   | 0.965                |
| Precision  | 0.9550561797752809   |
| Recall     | 0.9659090909090909   |
| F1 Score   | 0.96045197740113     |
| AUC        | 0.991984577922078    |

The confusion matrices provide a visual representation of the models' performance in terms of true positives, true negatives, false positives, and false negatives. The evaluation metrics demonstrate the high accuracy and effectiveness of both models in detecting fraudulent transactions.

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

📫 **Contact**: [@muditbhargava66](https://github.com/muditbhargava66) | 
🐛 **Report Issues**: [Issue Tracker](https://github.com/muditbhargava66/FraudShield/issues) | 
**Contributing Guidelines**: [CONTRIBUTING.md](CONTRIBUTING.md)

© 2026 Mudit Bhargava. [MIT](LICENSE)
<!-- Copyright symbol using HTML entity for better compatibility -->

</div>
