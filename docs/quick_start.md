# FraudShield - Quick Start Guide

**97 tests** | Lint: ruff + mypy |

---

## Installation

```bash
# Clone repository
git clone https://github.com/muditbhargava66/FraudShield.git
cd FraudShield

# Install with uv (recommended)
uv pip install -e .

# Or install from the committed lockfile (used by CI and the Dockerfile)
uv sync

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

## v3.0.0 Features

### Verify All Components

```bash
uv run python scripts/verify_v3_components.py
```

Runs 43 checks validating fraud ring detection, Prometheus metrics, broker abstraction, drift hooks, risk engine integration, and Docker configuration.

### Performance Benchmarking

```bash
uv run python scripts/benchmark_performance.py
```

Measures throughput (TPS) and latency percentiles for data cleaning (C++ vs. Python),
the stateful feature store, the inference service, the hybrid risk engine, and Neo4j
graph writes (simulated when no live instance is reachable).

### Notebooks

- `notebooks/01_fraudshield_pipeline_tutorial.ipynb` — end-to-end batch pipeline walkthrough
- `notebooks/02_realtime_streaming_and_graph.ipynb` — streaming, graph, and risk engine tour
- `notebooks/exploratory_data_analysis.ipynb` — EDA on the synthetic dataset
- `notebooks/model_experimentation.ipynb` — model comparison and threshold sweeps

### Prometheus Monitoring

```bash
# Metrics are enabled by default; toggle and retarget as needed
export FRAUDSHIELD_MONITORING_ENABLED=true
export FRAUDSHIELD_MONITORING_PORT=9090
export FRAUDSHIELD_MONITORING_METRICS_PATH=/metrics
```

The FastAPI inference app exposes the metrics registry at `http://localhost:8000/metrics/`.
Running the real-time orchestrator directly also starts a standalone Prometheus
HTTP server on `FRAUDSHIELD_MONITORING_PORT` (default 9090):

```bash
uv run python -m fraudshield.main
```

### Fraud Ring Detection

```python
from fraudshield.graph.fraud_ring_detector import FraudRingDetector

# Requires a running Neo4j instance
detector = FraudRingDetector(neo4j_driver, min_ring_size=3)
rings = detector.detect_rings(account_id="U_102")
risk = detector.assess_account(account_id="U_102")
```

### Inference API

Start the FastAPI app (serves `/predict`, `/health`, and `/metrics/` on port 8000):

```bash
uv run uvicorn fraudshield.ml.inference.api:app --port 8000
```

`transaction_id` must be a string in the request payload:

```bash
curl -s -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"transaction_id": "tx-1001", "account_id": "U_102", "amount": 4200.0, "is_online": false}'
```

Response fields: `transaction_id`, `fraud_probability`, `risk_level`
(`HIGH`/`MEDIUM`/`LOW`), `action` (`BLOCK`/`ALLOW`), `model_loaded`, `source`,
and `explanation` — the top-5 SHAP feature contributions behind the score
(`null` when no trained model is loaded).

### Broker Abstraction (Kafka / Redpanda)

```bash
# Switch broker backend via environment variable
export FRAUDSHIELD_KAFKA_BROKER_TYPE=redpanda  # or "kafka" (default)

# SASL credentials (Redpanda defaults to SASL_SSL + SCRAM-SHA-256)
export FRAUDSHIELD_KAFKA_SASL_USERNAME=<username>
export FRAUDSHIELD_KAFKA_SASL_PASSWORD=<password>
```

Both backends use the `confluent-kafka` client (`get_broker_factory("kafka" | "redpanda")`,
`create_broker_producer()`, `create_broker_consumer()` in `src/fraudshield/streaming/broker.py`).

### Full Stack with Docker

```bash
cd infra
# Docker Compose reads .env from its own directory, so create it here
cp ../.env.example .env
# Edit .env and replace every password placeholder before continuing.
# Required by compose: FRAUDSHIELD_NEO4J_PASSWORD, FRAUDSHIELD_POSTGRES_PASSWORD,
# FRAUDSHIELD_DATABASE_URL, FRAUDSHIELD_GRAFANA_ADMIN_PASSWORD
docker compose up -d
```

Starts: Zookeeper, Kafka (Confluent 7.5.0), Neo4j 5.12.0, PostgreSQL 15,
FraudShield app (port 8000), Prometheus (host 9091 -> 9090), Grafana (port 3000).
All host ports are bound to 127.0.0.1.

---
