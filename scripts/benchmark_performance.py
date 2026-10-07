#!/usr/bin/env python3
"""
Performance Benchmarking Script for FraudShield

Measures processing throughput (TPS) and latencies across key components:
- Data cleaning: C++ extension vs. pure-Python/NumPy fallback
- Stateful feature store (O(1) streaming aggregates per event)
- Inference service (trained model when artifacts exist, heuristic otherwise)
- Hybrid risk engine (composite scoring)
- Neo4j graph writes (live instance when reachable, simulated otherwise)

Usage:
    uv run python scripts/benchmark_performance.py
    python scripts/benchmark_performance.py
"""

from __future__ import annotations

import logging
import random
import statistics
import time
from datetime import datetime, timedelta
from typing import Any, Callable
from unittest.mock import MagicMock

import numpy as np

from fraudshield import __version__
from fraudshield.config.settings import get_settings
from fraudshield.core.risk_engine.engine import HybridRiskEngine
from fraudshield.data_cleaning import cpp_wrapper
from fraudshield.feature_engineering.stateful_aggregates import StatefulFeatureStore
from fraudshield.graph.fraud_ring_detector import FraudRingDetector
from fraudshield.ml.inference.service import FraudInferenceService

logging.getLogger("neo4j").setLevel(logging.ERROR)


def generate_mock_transaction() -> dict[str, Any]:
    return {
        "transaction_id": str(random.randint(100000, 999999)),
        "user_id": f"user_{random.randint(1, 1000)}",
        "account_id": f"acct_{random.randint(1, 1000)}",
        "amount": round(random.uniform(5.0, 10000.0), 2),
        "merchant_id": f"merchant_{random.randint(1, 100)}",
        "device_id": f"dev_{random.randint(1, 500)}",
        "ip_address": f"192.168.1.{random.randint(1, 254)}",
        "is_international": random.choice([True, False]),
        "is_online": random.choice([True, False]),
        "transaction_date": "2026-09-01 12:00:00",
        "currency": "USD",
        "status": "posted",
    }


def _percentiles(latencies_ms: list[float]) -> tuple[float, float, float]:
    mean = statistics.mean(latencies_ms)
    p95 = statistics.quantiles(latencies_ms, n=20)[18]
    p99 = statistics.quantiles(latencies_ms, n=100)[98]
    return mean, p95, p99


def _report(title: str, latencies_ms: list[float]) -> None:
    iterations = len(latencies_ms)
    mean, p95, p99 = _percentiles(latencies_ms)
    tps = iterations / (sum(latencies_ms) / 1000)
    print(f"{title}:")
    print(f"  Count: {iterations}")
    print(f"  Avg Latency: {mean:.4f} ms")
    print(f"  p95 Latency: {p95:.4f} ms")
    print(f"  p99 Latency: {p99:.4f} ms")
    print(f"  Projected TPS: {tps:,.0f}")


def _time_loop(items: list[Any], fn: Callable[[Any], Any]) -> list[float]:
    latencies = []
    for item in items:
        start = time.perf_counter()
        fn(item)
        latencies.append((time.perf_counter() - start) * 1000)
    return latencies


def benchmark_data_cleaning(iterations: int = 2000) -> None:
    print("\n--- Benchmarking Data Cleaning (C++ vs. NumPy fallback) ---")
    rows = [np.random.default_rng(seed).normal(100, 25, size=200) for seed in range(iterations)]
    for row in rows[::200]:
        row[random.randrange(200)] = np.nan

    def python_clean(row: np.ndarray) -> np.ndarray:
        cleaned = row[~np.isnan(row)]
        if len(cleaned) < 2:
            return cleaned
        mean, std = np.mean(cleaned), np.std(cleaned, ddof=1)
        if std == 0:
            return cleaned
        return cleaned[np.abs((cleaned - mean) / std) <= 3.0]

    if cpp_wrapper.is_cpp_available():

        def cpp_clean(row: np.ndarray) -> np.ndarray:
            return cpp_wrapper.remove_outliers(cpp_wrapper.remove_missing_values(row))

        _report("C++ cleaning (remove_missing_values + remove_outliers)", _time_loop(rows, cpp_clean))
    else:
        print("C++ extensions not compiled (run `uv sync` with CMake) - benchmarking Python path only.")

    _report("NumPy fallback cleaning", _time_loop(rows, python_clean))


def benchmark_stateful_features(iterations: int = 5000) -> None:
    print("\n--- Benchmarking Stateful Feature Store (streaming aggregates) ---")
    store = StatefulFeatureStore()
    events = [generate_mock_transaction() for _ in range(iterations)]
    base = datetime(2026, 9, 1, 12, 0, 0)
    for index, event in enumerate(events):
        event["transaction_date"] = (base + timedelta(seconds=index * 30)).strftime("%Y-%m-%d %H:%M:%S")
    _report("StatefulFeatureStore.build_features", _time_loop(events, store.build_features))


def benchmark_inference_service(iterations: int = 1000) -> None:
    print("\n--- Benchmarking Inference Service Latency ---")
    service = FraudInferenceService()
    mode = "trained model (artifacts loaded)" if service.model_loaded else "heuristic fallback (no artifacts)"
    transactions = [generate_mock_transaction() for _ in range(iterations)]
    _report(f"Inference Service [{mode}]", _time_loop(transactions, service.predict))


def benchmark_risk_engine(iterations: int = 1000) -> None:
    print("\n--- Benchmarking Hybrid Risk Engine Latency ---")
    mock_ring = MagicMock(spec=FraudRingDetector)
    mock_ring.assess_account.return_value = 0.45
    engine = HybridRiskEngine(ring_detector=mock_ring)

    cases = [(random.uniform(0.0, 1.0), random.uniform(0.0, 1.0), random.randint(0, 3)) for _ in range(iterations)]

    def evaluate(case: tuple[float, float, int]) -> None:
        ml_score, graph_score, rules_breached = case
        engine.evaluate_transaction(
            ml_score=ml_score,
            graph_score=graph_score,
            rules_breached=rules_breached,
            account_id="acct_123",
        )

    _report("Hybrid Risk Engine", _time_loop(cases, evaluate))


def benchmark_graph_operations(iterations: int = 100) -> None:
    print("\n--- Benchmarking Neo4j Operations ---")
    from neo4j import GraphDatabase

    s = get_settings()
    driver = None
    live = False
    try:
        driver = GraphDatabase.driver(s.neo4j.uri, auth=(s.neo4j.username, s.neo4j.password))
        with driver.session() as session:
            session.run("RETURN 1")
        live = True
        print("Live Neo4j instance detected - running live write benchmark.")
    except Exception:
        print("Neo4j instance offline - running simulated write benchmark.")
        driver = MagicMock()
        session_mock = MagicMock()
        session_mock.run.return_value = None
        driver.session.return_value.__enter__.return_value = session_mock

    query = "MERGE (t:Transaction {id: $tx_id}) SET t.amount = $amount, t.date = $date RETURN t"

    latencies = []
    try:
        for i in range(iterations):
            start = time.perf_counter()
            with driver.session() as session:
                session.run(
                    query,
                    tx_id=f"tx_bench_{i}",
                    amount=round(random.uniform(10.0, 5000.0), 2),
                    date="2026-09-01 12:00:00",
                )
            latencies.append((time.perf_counter() - start) * 1000)
    finally:
        if live and driver is not None:
            driver.close()

    mode = "live" if live else "simulated"
    _report(f"Neo4j Transaction Writes ({mode})", latencies)


def main() -> None:
    print("=" * 62)
    print(f"  FraudShield {__version__} Performance Benchmarking Suite")
    print("=" * 62)

    benchmark_data_cleaning(2000)
    benchmark_stateful_features(5000)
    benchmark_inference_service(1000)
    benchmark_risk_engine(1000)
    benchmark_graph_operations(100)

    print("\n" + "=" * 62)
    print("  Benchmark Run Complete")
    print("=" * 62)


if __name__ == "__main__":
    main()
