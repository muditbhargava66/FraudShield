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

`run_drift_check_with_metrics()` wraps the existing KS-test drift logic from `pipeline_tasks.py` and emits Prometheus gauges after each check. It raises `RuntimeError` when the drift ratio exceeds `max_drift_ratio`.

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
