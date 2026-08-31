# Setup Instructions

Step-by-step instructions for setting up FraudShield locally.

## Prerequisites

- Python 3.10+
- C++ compiler (GCC 7+ or Clang 5+) — only needed for C++ extensions
- Docker and Docker Compose — only for Kafka/Neo4j real-time streaming
- Apache Airflow — optional, for DAG-based orchestration

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/muditbhargava66/FraudShield.git
   cd FraudShield
   ```

2. Install dependencies with [uv](https://docs.astral.sh/uv/):
   ```bash
   uv pip install -e .
   ```
   Or with pip:
   ```bash
   pip install -e .
   ```

3. Build C++ extensions (optional):
   ```bash
   uv pip install -e .   # triggers CMake + pybind11
   ```

4. Verify installation:
   ```bash
   uv run pytest tests/ -v
   uv run ruff check src tests
   uv run mypy src/
   ```

## Database Configuration

1. Copy `.env.example` and set the variables you need:
   ```bash
   cp .env.example .env
   ```

2. Set `FRAUDSHIELD_DATABASE_URL` to your SQLAlchemy connection string, e.g.:
   ```bash
   export FRAUDSHIELD_DATABASE_URL="sqlite:///data/processed/fraud_data.db"
   ```

3. For PostgreSQL or other databases:
   ```bash
   export FRAUDSHIELD_DATABASE_URL="postgresql://user:pass@localhost:5432/frauddb"
   ```

4. Run the SQL schema to create the required tables:
   ```bash
   # The schema is in src/fraudshield/sql/create_tables.sql.
   # SQLite ingestion creates the transactions table automatically; apply this
   # schema explicitly for PostgreSQL when you also need the users table.
   ```

## Real-Time Infrastructure (Optional)

For the streaming pipeline (Kafka + Neo4j + monitoring stack):

```bash
cd infra
cp ../.env.example ../.env
# Edit ../.env and replace every password placeholder before continuing.
docker compose up -d
```

This starts 6 services:
- **Zookeeper** (port 2181) and **Kafka** (port 9092)
- **Neo4j** (ports 7474 HTTP, 7687 Bolt)
- **FraudShield app** (port 8000 FastAPI and `/metrics`)
- **Prometheus** (port 9091) scraping `fraudshield:8000/metrics`
- **Grafana** (port 3000; password from `.env`) with Prometheus datasource

The batch pipeline works without Docker.

## Airflow (Optional)

1. Install with Airflow extras:
   ```bash
   uv pip install -e ".[airflow]"
   ```

2. Initialize the database:
   ```bash
   airflow db migrate
   ```

3. Start the webserver and scheduler:
   ```bash
   airflow webserver --port 8080 &
   airflow scheduler &
   ```

4. Access the UI at `http://localhost:8080` and enable the FraudShield DAG.

## Running the Pipeline

Run the batch pipeline end-to-end:

```bash
# 1. Generate synthetic data
uv run python data/raw/synthetic_fraud_data.py

# 2. Ingest
uv run fraudshield_ingest

# 3. Preprocess
uv run fraudshield_preprocess

# 4. Train
uv run fraudshield_train --model both

# 5. Evaluate
uv run fraudshield_evaluate --model_path data/models/xgboost.pkl
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| C++ modules fail to compile | Ensure GCC 7+ or Clang 5+ is installed. Run `uv pip install -e .` |
| `ModuleNotFoundError: fraudshield` | Run `uv pip install -e .` from the project root |
| Database connection errors | Check `FRAUDSHIELD_DATABASE_URL` environment variable |
| Import errors for Airflow operators | Install with `uv pip install -e ".[airflow]"` |
| Feature values look wrong | This is expected — rolling windows use `closed="left"` to prevent data leakage |
| Prometheus metrics not appearing | Set `FRAUDSHIELD_MONITORING_ENABLED=true` and request `http://localhost:8000/metrics` |
| Grafana shows no data | Ensure Prometheus datasource is configured at `http://prometheus:9090` |

## Verification

Run the comprehensive v3.0.0 component verification:

```bash
uv run python scripts/verify_v3_components.py
```

This runs 43 checks across all modules: fraud ring detection, Prometheus metrics, broker abstraction, drift hooks, risk engine, Docker config, and v2.x integration.

## Support

For issues or questions, open a GitHub issue with:
- Python version (`python --version`)
- Error traceback
- Steps to reproduce

---
