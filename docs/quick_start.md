# FraudShield - Quick Start Guide

**30/30 tests passing** | Lint: ruff + mypy

---

## Installation

```bash
# Clone repository
git clone https://github.com/muditbhargava66/FraudShield.git
cd FraudShield

# Install with uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
```

---

## Quality Checks

```bash
# Run all tests
uv run pytest tests/ -v

# Lint
uv run ruff check src tests

# Type check
uv run mypy src/

# Format
uv run ruff format src tests
```

### Using Makefile
```bash
make test          # pytest
make lint          # ruff check
make typecheck     # mypy
make format        # ruff format
make clean         # remove build artifacts
```

---

## C++ Extensions (Optional)

```bash
# Check availability
uv run python -c "from fraudshield.feature_engineering import cpp_wrapper; print('C++ Available:', cpp_wrapper.is_cpp_available())"

# Build via editable install (triggers CMake + pybind11)
uv pip install -e .
```

C++ is optional. Python fallbacks work and are fully tested.

---

## Running the Pipeline

### 1. Data Ingestion
```bash
uv run fraudshield_ingest \
    --data_path data/raw \
    --input_file synthetic_fraud_data.csv \
    --output_file data/processed/ingested_data.csv
```

### 2. Data Preprocessing
```bash
uv run fraudshield_preprocess \
    --input_data data/processed/ingested_data.csv \
    --train_data data/models/preprocessed_data.npy \
    --test_data data/models/test_data.npy \
    --preprocessor_path data/models/preprocessor.joblib \
    --metadata_path data/models/preprocessing_metadata.json
```

### 3. Model Training
```bash
uv run fraudshield_train \
    --preprocessed_data data/models/preprocessed_data.npy \
    --test_data data/models/test_data.npy \
    --output_dir data/models \
    --model both
```

### 4. Model Evaluation
```bash
uv run fraudshield_evaluate \
    --model_path data/models/xgboost.pkl \
    --test_data data/models/test_data.npy \
    --output_path data/models/evaluation_report.csv \
    --confusion_matrix_path data/plots/confusion_matrix.png
```

---

## Generate Synthetic Data

```bash
uv run python data/raw/synthetic_fraud_data.py
```

Produces 5,000 transactions with ~7% fraud rate across 200 users and 80 merchants.

---

## Airflow (Optional)

```bash
# Install with airflow extras
uv pip install -e ".[airflow]"

# Initialize
airflow db migrate
airflow webserver --port 8080 &
airflow scheduler &
```

---
