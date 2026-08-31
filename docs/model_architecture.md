# Model Architecture

FraudShield uses a **hybrid architecture** combining ML models (Random Forest, XGBoost), graph analytics (Neo4j), and rule-based constraints for fraud detection.

## Batch Pipeline

```
Raw CSV → Ingestion (SQLite) → Preprocessing → Feature Engineering → Data Drift Check → Training → Evaluation
```

1. **Data Ingestion**: Reads CSV data, validates schema, loads into SQLite
2. **Preprocessing**: Applies C++ data cleaning, encodes categoricals, imputes missing values
3. **Feature Engineering**: Computes rolling window aggregations and behavioral features
4. **Data Drift Validation**: Performs Kolmogorov-Smirnov tests between train and test splits to detect distributional shifts before training
5. **Training**: Fits Random Forest and/or XGBoost on preprocessed arrays
6. **Evaluation**: Computes metrics, generates confusion matrices, saves reports

## Real-Time Architecture (Optional)

Requires Docker (Kafka + Neo4j):

1. **Streaming Ingestion**: Transactions consumed via Kafka (or Redpanda through the `streaming/broker.py` abstraction) at configurable throughput
2. **Stateful Features**: `StatefulFeatureStore` computes rolling window aggregates in O(1) amortized time per event
3. **Neo4j Graph Tracking**: Entities (devices, IPs, accounts) tracked as graph nodes; entity risk plus Louvain fraud ring detection feed the graph score
4. **Hybrid Risk Engine**: Blends ML (0.6), graph (0.3), and rule (0.1) scores into a final risk value; overrides to >= 0.95 when all rules breach or the graph score >= 0.95. Risk levels: HIGH >= 0.75 (BLOCK), MEDIUM >= 0.40, else LOW (ALLOW)
5. **Monitoring**: Prometheus counters/histograms/gauges recorded for each prediction and drift check
6. **SHAP Explainability**: TreeExplainer generates per-prediction feature attributions for HIGH-risk transactions

## ML Models

### Random Forest

Ensemble of decision trees with bootstrap aggregation.

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `n_estimators` | 300 | Number of trees |
| `class_weight` | `balanced_subsample` | Handles class imbalance per-tree |
| `max_depth` | None (auto) | Tree depth limit |
| `min_samples_split` | 2 | Minimum samples for internal split |
| `min_samples_leaf` | 1 | Minimum samples at leaf |

### XGBoost

Gradient boosted trees with regularization.

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `n_estimators` | 300 | Boosting rounds |
| `scale_pos_weight` | auto | `neg_count / pos_count` for imbalance |
| `max_depth` | 6 | Tree depth limit |
| `learning_rate` | 0.1 | Step size shrinkage |
| `eval_metric` | `aucpr` | Optimizes area under PR curve |

## Feature Engineering

### Rolling Window Features

Computed per-entity (user, merchant, currency, status) with windows `[1h, 24h, 7d, 30d]`:

| Feature | Aggregation | Leakage Prevention |
|---------|-------------|-------------------|
| `*_txn_count_{window}` | count | `closed="left"` excludes current row |
| `*_amount_sum_{window}` | sum | `closed="left"` |
| `*_amount_mean_{window}` | mean | `closed="left"` |

### Behavioral Features

| Feature | Description | Leakage Prevention |
|---------|-------------|-------------------|
| `user_time_since_last_txn` | Seconds since user's previous transaction | Computed on time-sorted data |
| `user_amount_zscore` | Z-score vs user's expanding history | `shift(1)` excludes current, `ddof=1` |

### Raw Features

`amount`, `is_international`, `is_online`, `currency` (one-hot), `status` (one-hot)

## Training Process

1. **Time-based split**: When temporal features exist, data is split chronologically (no random shuffle)
2. **Label encoding**: String labels auto-detected and encoded; encoder saved for test consistency
3. **Class imbalance**: RF uses `balanced_subsample`, XGBoost uses `scale_pos_weight`
4. **Evaluation**: accuracy, precision, recall, F1, ROC-AUC, average precision (all use `zero_division=0`)
5. **Artifacts**: Models saved as `.pkl`, metrics as JSON, confusion matrices as PNG

## Model Selection

Both models train independently. Selection is based on test-set metrics saved to `training_metrics.json`. The default evaluation model is XGBoost.

## Deployment

Trained models are loaded by `FraudInferenceService` for:
- **Batch scoring**: Via CLI `fraudshield_evaluate`
- **Real-time API**: FastAPI endpoint at `/predict`
- **Kafka consumer**: Processes streaming events with the same preprocessor and model

The Airflow `model_deployment` task (`run_model_deployment` in
`data_pipeline/pipeline_tasks.py`) validates that the model, preprocessor, and
metadata artifacts load cleanly before the API serves them.

---
