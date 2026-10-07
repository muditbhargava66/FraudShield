# Prometheus Monitoring

FraudShield emits Prometheus-compatible metrics for the streaming and inference pipelines. Metrics are collected via `prometheus_client` and exposed over HTTP for scraping.

## Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `FRAUDSHIELD_MONITORING_ENABLED` | `true` | Enable or disable metrics collection |
| `FRAUDSHIELD_MONITORING_PORT` | `9090` | HTTP port for the Prometheus metrics endpoint |
| `FRAUDSHIELD_MONITORING_METRICS_PATH` | `/metrics` | URL path for the metrics endpoint |

Metrics collection uses a per-instance `CollectorRegistry` to avoid registration conflicts in multi-process or test environments. The FastAPI app mounts that same registry at `FRAUDSHIELD_MONITORING_METRICS_PATH` (default `/metrics`); the streaming orchestrator exposes it on the configured monitoring port when run on its own.

## Metrics Reference

### Counters

| Metric | Labels | Description |
|--------|--------|-------------|
| `fraudshield_transactions_total` | `source` (e.g. `streaming`, `trained_model`, `rules_fallback`), `status` (`processed`/`failed`) | Total transactions processed |
| `fraudshield_risk_level_total` | `level` (HIGH/MEDIUM/LOW) | Predictions grouped by assigned risk level |

### Histograms

| Metric | Labels | Buckets | Description |
|--------|--------|---------|-------------|
| `fraudshield_inference_latency_seconds` | `model_name`, `source` | 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0 | Inference latency per prediction |
| `fraudshield_fraud_probability` | — | 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95 | Distribution of fraud probability scores |

### Gauges

| Metric | Description |
|--------|-------------|
| `fraudshield_active_fraud_rings` | Current number of detected fraud rings |
| `fraudshield_drift_ratio` | Latest data drift ratio from KS-test validation |
| `fraudshield_drifted_features` | Number of features that drifted beyond threshold |

## Automatic Recording

The `FraudInferenceService.predict()` method automatically records:
- Inference latency (via `time.perf_counter()`)
- Fraud probability distribution
- Risk level classification (derived from probability using the same thresholds as `HybridRiskEngine`)
- Transaction count

Recording is a silent no-op when `prometheus_client` is not installed or when the `MetricsCollector` returns `None`.

## Drift Monitoring

### Batch Pipeline

`run_drift_check_with_metrics()` runs a two-sample KS test per feature, emits Prometheus gauges after each check, and raises `RuntimeError` when the drift ratio exceeds `max_drift_ratio` (default 0.3).

A feature counts as drifted only when **both** conditions hold:

1. Its p-value is below `drift_threshold` (default 0.05) **after Benjamini-Hochberg FDR correction** (`use_fdr=True` by default) — testing ~45 features at once inflates false discoveries without correction.
2. Its KS statistic reaches `min_ks_statistic` (default 0.10) — the KS test over-rejects at large sample sizes, so statistical significance alone would flag practically identical distributions.

Both knobs are exposed through `run_data_drift_check()` and therefore through the Airflow drift task. On the shipped synthetic dataset the corrected gate reports ~27% drifted features (12/45, KS statistics 0.15-0.51 on genuinely divergent rolling-count windows) and passes the default 30% limit.

### Streaming Pipeline

`streaming_drift_monitor()` performs a lightweight z-score comparison of recent feature values against baseline statistics. Features are flagged when the z-score exceeds `z_threshold` (default 3.0 standard deviations). Aggregate drift metrics are emitted after each check.

## Docker Integration

The Docker Compose stack includes:
- **Prometheus** (host port 9091 -> container 9090): Scrapes `fraudshield:8000/metrics` every 15 seconds
- **Grafana** (port 3000): Uses the administrator password supplied through `infra/.env` (`FRAUDSHIELD_GRAFANA_ADMIN_PASSWORD`)

Scrape configuration is in `infra/prometheus.yml`.

## Grafana Dashboards

After starting the stack, create dashboards in Grafana:

1. Navigate to `http://localhost:3000` and log in
2. Add a Prometheus data source pointing to `http://prometheus:9090`
3. Create panels using the metric names above:
   - **Transaction throughput**: `rate(fraudshield_transactions_total[5m])`
   - **Inference latency p99**: `histogram_quantile(0.99, rate(fraudshield_inference_latency_seconds_bucket[5m]))`
   - **Fraud probability distribution**: `histogram_quantile(0.5, rate(fraudshield_fraud_probability_bucket[5m]))`
   - **Active fraud rings**: `fraudshield_active_fraud_rings`
   - **Drift ratio**: `fraudshield_drift_ratio`

## Performance: Targets vs Measured

Measured on Apple Silicon (local machine) with `scripts/benchmark_performance.py`
against the committed v3 model artifacts; PRD targets in parentheses.

| Component | Measured | PRD target | Status |
|---|---|---|---|
| Stateful feature store (per event) | ~54,000 events/s, 0.02 ms avg | >= 10,000 TPS | Met |
| ML inference (service-level predict) | 3.1-3.6 ms avg | < 100 ms | Met |
| `/predict` API incl. SHAP explanation | 6.9 ms avg, 9.1 ms p99 | < 100 ms | Met |
| Hybrid risk engine | ~165,000 evaluations/s | - | Met |
| C++ data cleaning vs NumPy fallback | 326k rows/s vs 79k rows/s (4.2x) | - | Met |
| Neo4j transaction MERGE (local Docker) | 11.3 ms avg | < 10 ms | Marginal miss |
| End-to-end single consumer pipeline | ~300 TPS | >= 10,000 TPS | Not met |

Notes:

- **Single-consumer throughput** is bounded by per-event model inference in one
  Python process. The 10k TPS target requires horizontal scale-out: partition
  the Kafka topic and run multiple consumer replicas behind the stateless
  inference API. `StatefulFeatureStore` is per-process, so multi-instance
  deployments need a shared store (e.g., Redis) or user-keyed partitioning so
  each user's events land on the same replica.
- **Neo4j write latency** varies with storage; the 11.3 ms average comes from
  Docker Desktop on macOS with per-write sessions. Batching writes or using
  an SSD-backed deployment closes the remaining gap.
- **Message loss**: the Kafka consumer commits offsets only after successful
  processing and records a `failed` transaction metric on decode/processing
  errors, so unprocessed messages are redelivered rather than dropped.
