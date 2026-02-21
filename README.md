<div align="center">

# FraudShield

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/muditbhargava66/FraudShield/actions/workflows/ci.yml/badge.svg)](https://github.com/muditbhargava66/FraudShield/actions/workflows/ci.yml)
[![Linting: Flake8 & Pylint](https://img.shields.io/badge/Linting-Flake8%20%7C%20Pylint-success)](#testing)
[![Tested with Tox: 3.10 | 3.11 | 3.12 | 3.13](https://img.shields.io/badge/Tested%20with%20Tox-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue)](#testing)

</div>

## Overview
FraudShield is an advanced anomaly detection pipeline designed to identify and prevent fraudulent activities within large datasets. By leveraging cutting-edge machine learning techniques, efficient C++ data processing modules, and a robust SQL-based data storage and retrieval system, FraudShield ensures the integrity and security of financial transactions.

## Architecture
The FraudShield pipeline consists of the following key components:
1. **Data Ingestion**: Collects transaction data from various sources and stores it in a centralized SQL database.
2. **Data Cleaning and Preprocessing**: Applies advanced data cleaning techniques to handle missing values, outliers, and inconsistencies.
3. **Feature Engineering**: Extracts relevant features from the preprocessed data to capture patterns and anomalies indicative of fraudulent behavior.
4. **Model Training and Evaluation**: Trains machine learning models (Random Forest and XGBoost) on the engineered features and evaluates their performance using cross-validation and hold-out datasets.
5. **Model Deployment**: Deploys the trained models in a production environment for real-time fraud detection and prevention.
6. **Monitoring and Alerting**: Continuously monitors the performance of the deployed models and triggers alerts for suspicious activities.

## Key Features

- Transactional schema sample data generator (`data/raw/synthetic_fraud_data.py`)
- **Secure SQL ingestion** via SQLAlchemy with URL builder (SQLite by default)
- Preprocessing with **time-based split** to prevent temporal leakage (when `transaction_date` exists)
- **Data leakage prevention** in feature engineering (rolling-window user/merchant/currency/status aggregates)
- Model training (Random Forest, XGBoost) with **class balancing** and evaluation utilities
- Optional Airflow DAG for orchestration with **runtime variable fetching**
- **Production-ready C++ modules** with bounds checking and safety improvements
- Comprehensive error handling and security best practices

## Installation

Option A (recommended): `uv`

```bash
uv sync
```

Option B: `pip`

```bash
python -m pip install -e .
```

If you need a legacy requirements file for tooling, use `requirements.txt` (kept for compatibility).

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

**Security Note**: Database connections now use SQLAlchemy's URL builder to prevent SQL injection. Set credentials via environment variables:

```bash
export DB_USER=your_username
export DB_PASSWORD=your_password
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=frauddb
```

## Airflow (Optional)

- DAGs live in `src/fraudshield/data_pipeline/airflow_dags/`.
- A sample Airflow config is in `airflow/airflow.cfg`.

To use Airflow locally, set `AIRFLOW_HOME` to a directory of your choice and configure `dags_folder` to point at the DAG directory above.

## Testing

- Python testing & isolated environments: `tox` (3.10, 3.11, 3.12, 3.13)
- Standard test runner: `pytest`
- C++ tests: located in `tests/cpp` and run separately with GoogleTest

Run all unit tests in isolated environments for multiple Python versions:
```bash
tox
```

## Documentation

Comprehensive documentation is available in the `docs/` directory:

- **[Quick Start Guide](docs/quick_start.md)** - Fast track installation and execution
- **[Setup Instructions](docs/setup_instructions.md)** - Detailed installation and configuration guide
- **[Migration Guide](docs/migration_guide.md)** - Upgrading from previous versions
- **[Security and Quality](docs/security_and_quality.md)** - Security improvements and data quality enhancements
- **[Data Dictionary](docs/data_dictionary.md)** - Feature descriptions and data leakage prevention details
- **[Model Architecture](docs/model_architecture.md)** - Model training and evaluation details
- **[SQL Schema](docs/sql_schema.md)** - Database schema and secure connection practices
- **[C++ Modules](docs/cpp_modules.md)** - C++ module documentation with safety improvements
- **[Fixes Summary](FIXES_SUMMARY.md)** - Complete list of all bug fixes and improvements

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

See [FIXES_SUMMARY.md](FIXES_SUMMARY.md) for complete details.

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