# FraudShield v3.0.0 -- Product Requirements Document (PRD)

## 1. Overview

FraudShield v3.0.0 represents the transition of the project from a batch-oriented ML fraud detection system (version 2.x) into a real-time, graph-aware fraud detection platform. The goal of this release is to introduce streaming transaction ingestion, graph-based fraud analysis, explainable AI capabilities, and a scalable architecture that supports future hardware acceleration and MLOps automation.

This version focuses on enabling the system to detect coordinated fraud patterns in real time rather than analyzing isolated historical transactions only.

## 2. Objectives

Primary goals of v3.0.0:

1. Introduce real-time transaction ingestion using a streaming system (Kafka or Redpanda).
2. Implement graph-based fraud detection using transaction relationship networks.
3. Add explainability outputs to every fraud prediction.
4. Build a modular risk scoring engine combining rules, ML models, and graph signals.
5. Prepare the architecture for future low-latency hardware acceleration.
6. Enable monitoring hooks for future concept drift and MLOps integration.

## 3. Key Capabilities

The new platform capabilities include:

### Real-Time Processing

Transactions are processed immediately as they arrive in a streaming pipeline rather than periodic batch jobs.

### Graph Fraud Detection

Accounts, devices, and transactions are represented as nodes and edges in a transaction graph to detect fraud rings.

### Hybrid Risk Scoring

The fraud score will combine three independent signals:

- Machine learning model score
- Rule engine score
- Graph anomaly score

### Explainability

Each prediction will produce a human-readable explanation describing the main factors behind the risk score.

## 4. High-Level Architecture

Core architecture components introduced in v3.0.0:

| Component | Description |
|-----------|-------------|
| **Transaction Producer** | Simulates real-world financial transaction streams |
| **Streaming Layer** | Kafka or Redpanda used as the primary ingestion bus |
| **Feature Extraction Engine** | C++ modules compute real-time features |
| **Model Inference Service** | Loads trained models and produces risk predictions |
| **Graph Engine** | Maintains dynamic transaction networks for fraud ring detection |
| **Risk Engine** | Combines ML predictions, rule evaluation, and graph signals |
| **Explainability Service** | Generates explanations using SHAP analysis |
| **Storage** | PostgreSQL for structured data and Neo4j for graph relationships |

## 5. System Architecture Diagram

```
Transaction Source
        |
Streaming Broker (Kafka / Redpanda)
        |
Stream Consumer
        |
Feature Engineering (C++)
        |
ML Inference Service
        |
Graph Analysis Engine
        |
Risk Scoring Engine
        |
Explainability Module
        |
Fraud Alert Database
```

## 6. Core Modules

1. **Streaming Module** -- Handles transaction ingestion, consumer management, and message validation.
2. **Feature Engine** -- Real-time feature extraction using optimized C++ modules.
3. **Model Inference** -- Loads trained XGBoost / RandomForest models and performs scoring.
4. **Graph Engine** -- Builds and updates a transaction graph representing account relationships.
5. **Risk Engine** -- Combines multiple risk signals to produce a final fraud probability.
6. **Explainability Engine** -- Produces SHAP-based explanation vectors for flagged transactions.
7. **Monitoring Hooks** -- Expose metrics for latency, prediction distribution, and drift signals.

## 7. Repository Structure (Target)

```
fraudshield/
    core/
        feature_engine/
        risk_engine/
    ml/
        training/
        inference/
        explainability/
    streaming/
        kafka_consumer/
        transaction_producer/
    graph/
        graph_builder/
        fraud_ring_detector/
    monitoring/
        metrics/
        drift_hooks/
    simulator/
        synthetic_transactions/
    infra/
        docker/
        configs/
```

## 8. Performance Requirements

Target system performance metrics:

| Metric | Target |
|--------|--------|
| Transaction throughput | Minimum 10,000 transactions per second |
| Inference latency | < 100 milliseconds per transaction |
| Streaming stability | No message loss under sustained load |
| Graph updates | Edge updates must complete within 10 ms |
| Scalability | System must scale horizontally with container replication |

## 9. Future Extensions (v4 and beyond)

Future versions will extend FraudShield with:

- Graph Neural Networks for advanced fraud ring detection
- Concept drift monitoring and automated model retraining
- Fraud investigation dashboards
- FPGA-based ultra-low-latency feature processing
- Synthetic fraud attack simulators
- Full Infrastructure-as-Code deployment

## 10. Milestones

| Milestone | Description |
|-----------|-------------|
| 1 | Streaming infrastructure integration |
| 2 | Real-time inference API |
| 3 | Graph engine implementation |
| 4 | Risk scoring engine |
| 5 | Explainability integration |
| 6 | End-to-end streaming fraud detection pipeline |

---

## Implementation Status Review

The following assessment maps each PRD requirement against the current v2.3.0 codebase to identify what is already implemented, what needs work for v3.0.0, and what should be deferred.

### Already Implemented in v2.3.0

These capabilities exist in the current codebase and do not need to be rebuilt:

| PRD Requirement | v2.3.0 Implementation | Location |
|-----------------|----------------------|----------|
| Real-time processing | Kafka producer/consumer | `streaming/transaction_producer.py`, `streaming/kafka_consumer.py` |
| Graph fraud detection | Neo4j upserts + entity risk | `graph/graph_builder/builder.py`, `graph/repository.py` |
| Hybrid risk scoring | ML (0.6) + graph (0.3) + rules (0.1) | `core/risk_engine/engine.py` |
| Explainability | SHAP TreeSHAP for high-risk transactions | `ml/explainability/shap_explainer.py` |
| Model inference service | FastAPI + model/preprocessor loading | `ml/inference/service.py`, `ml/inference/api.py` |
| Feature engineering (C++) | pybind11 data cleaning, experimental feature engineering | `data_cleaning/data_cleaning.cpp`, `feature_engineering/feature_engineering.cpp` |
| Data drift validation | KS test in Airflow DAG | `data_pipeline/pipeline_tasks.py` |

### Needs Work for v3.0.0

These areas require new development or significant enhancement:

| PRD Requirement | Gap | Status |
|-----------------|-----|--------|
| **Fraud ring detection** | Current graph engine computes entity risk (per-node), but does not detect fraud rings (community detection across subgraphs) | **Implemented** — `graph/fraud_ring_detector.py` with Louvain community detection on Neo4j 2-hop subgraphs. Integrated into `HybridRiskEngine`. |
| **Monitoring hooks** | No metrics endpoint, no prediction distribution tracking, no latency histograms | **Implemented** — `monitoring/metrics.py` with Prometheus client, `monitoring/drift_hooks.py` with KS-test and streaming z-score hooks. Docker Compose includes Prometheus + Grafana. |
| **Redpanda support** | Only Kafka is configured | **Implemented** — `streaming/broker.py` with `BrokerFactory` ABC, `KafkaBrokerFactory`, and `RedpandaBrokerFactory`. Configurable via `FRAUDSHIELD_KAFKA_BROKER_TYPE`. |
| **Performance benchmarking** | No load testing or throughput measurement exists | **Implemented** — `scripts/benchmark_performance.py` measures TPS/latency for the C++ cleaning wrapper, inference service, graph operations, and hybrid risk engine. |
| **Horizontal scaling** | `docker-compose.yml` runs single instances | Partially addressed — `Dockerfile` added, docker-compose includes app + monitoring stack. Full Kubernetes manifests deferred. |
| **PostgreSQL support** | SQLite is the default; PostgreSQL is listed in config but not actively tested | **Implemented** — `tests/integration_tests/test_postgresql.py` validates ingestion against a live PostgreSQL instance; CI provides a `postgres:15-alpine` service with `FRAUDSHIELD_DATABASE_URL` wired into the test run. |
| **Repository structure alignment** | Current `src/fraudshield/` layout differs from the PRD target structure | Not started — Reorganize into the target structure or document the deviation and justify it |

### Should Be Deferred

These items are aspirational and should remain in the "Future Extensions" section:

| PRD Requirement | Reason to Defer |
|-----------------|----------------|
| **FPGA-based feature processing** | Requires specialized hardware and is premature for v3.0.0 |
| **Graph Neural Networks** | Requires significant ML research investment; current hybrid approach is effective |
| **Fraud investigation dashboards** | UI/UX effort; better suited for a dedicated v4.0.0 release |
| **Synthetic fraud attack simulators** | Research-oriented; current synthetic data generator is sufficient for training |
| **Full Infrastructure-as-Code** | Docker Compose is adequate for current scale; Terraform/Pulumi adds complexity without immediate benefit |

### Performance Targets -- Feasibility Assessment

| Target | Assessment |
|--------|------------|
| 10,000 TPS | Ambitious for a Python-based pipeline. Achievable with C++ feature extraction + batched Kafka consumption + async model inference. Requires benchmarking. |
| < 100ms inference latency | Realistic for a single model prediction with pre-loaded artifacts. The current `InferenceService` caches models in memory. |
| No message loss | Achievable with Kafka consumer commit-after-processing and proper error handling. Already partially implemented. |
| 10ms graph edge updates | Tight for Neo4j MERGE operations. Achievable with proper indexing and connection pooling, but requires benchmarking. |
| Horizontal scaling | Requires stateless services. The `StatefulFeatureStore` is currently in-memory per-process; needs Redis or a shared store for multi-instance deployment. |

### Recommendations

1. **Prioritize fraud ring detection and monitoring** as the two genuinely new capabilities for v3.0.0.
2. **Align the repository structure** with the PRD target or explicitly document the deviation in AGENTS.md.
3. **Add performance benchmarks** early in the v3.0.0 cycle to identify bottlenecks before feature development.
4. **Defer FPGA, GNN, and dashboards** to v4.0.0 -- they add scope without improving the core fraud detection capability.
5. **Make the streaming broker pluggable** (Kafka vs Redpanda) as a minor enhancement, not a major milestone.
