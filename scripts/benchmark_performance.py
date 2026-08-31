#!/usr/bin/env python3
"""
Performance Benchmarking Script for FraudShield

Measures processing throughput (TPS) and latencies across key components:
- C++ Data Cleaning vs. Pure Python
- Inference Service (ML predictions)
- Neo4j Graph operations (mocked/live fallback)
- Hybrid Risk Engine (composite scoring)

Usage:
    python scripts/benchmark_performance.py
    uv run python scripts/benchmark_performance.py
"""

from __future__ import annotations

import random
import statistics
import time
from typing import Any
from unittest.mock import MagicMock

# Attempt to load FraudShield modules
try:
    from fraudshield.data_cleaning.cpp_wrapper import clean_data
    _HAS_CPP = True
except ImportError:
    _HAS_CPP = False

from fraudshield.config.settings import get_settings
from fraudshield.core.risk_engine.engine import HybridRiskEngine
from fraudshield.graph.fraud_ring_detector import FraudRingDetector
from fraudshield.ml.inference.service import FraudInferenceService


def generate_mock_transaction() -> dict[str, Any]:
    return {
        "transaction_id": random.randint(100000, 999999),
        "user_id": f"user_{random.randint(1, 1000)}",
        "account_id": f"acct_{random.randint(1, 1000)}",
        "amount": round(random.uniform(5.0, 10000.0), 2),
        "merchant_id": f"merchant_{random.randint(1, 100)}",
        "device_id": f"dev_{random.randint(1, 500)}",
        "ip_address": f"192.168.1.{random.randint(1, 254)}",
        "is_international": random.choice([True, False]),
        "is_online": random.choice([True, False]),
        "transaction_date": "2026-07-01 12:00:00",
    }


def benchmark_cpp_cleaning(iterations: int = 1000):
    print("\n--- Benchmarking C++ Data Cleaning vs. Python ---")
    if not _HAS_CPP:
        print("C++ extensions not compiled. Skipping C++ benchmark.")
        return

    # Create dummy dirty datasets
    dummy_data = [[float(i) if i % 10 != 0 else float('nan') for i in range(100)] for _ in range(iterations)]

    # C++ implementation
    start_time = time.perf_counter()
    for row in dummy_data:
        clean_data(row)
    cpp_duration = time.perf_counter() - start_time
    cpp_tps = iterations / cpp_duration

    print(f"C++ data cleaning: {iterations} iterations in {cpp_duration:.4f}s ({cpp_tps:.2f} iterations/sec)")


def benchmark_inference_service(iterations: int = 1000):
    print("\n--- Benchmarking Inference Service Latency ---")
    # Initialize service. If artifacts missing, it falls back to heuristic model.
    service = FraudInferenceService()
    
    latencies = []
    
    for _ in range(iterations):
        txn = generate_mock_transaction()
        start = time.perf_counter()
        # Call predict using inference service
        service.predict(txn)
        duration = time.perf_counter() - start
        latencies.append(duration * 1000) # Convert to ms

    avg_lat = statistics.mean(latencies)
    p95_lat = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
    p99_lat = statistics.quantiles(latencies, n=100)[98] # 99th percentile
    tps = iterations / (sum(latencies) / 1000)

    print("Inference Service (Mocked/Heuristic fallback):")
    print(f"  Count: {iterations}")
    print(f"  Avg Latency: {avg_lat:.2f} ms")
    print(f"  p95 Latency: {p95_lat:.2f} ms")
    print(f"  p99 Latency: {p99_lat:.2f} ms")
    print(f"  Projected TPS: {tps:.2f}")


def benchmark_risk_engine(iterations: int = 1000):
    print("\n--- Benchmarking Hybrid Risk Engine Latency ---")
    # Initialize mock ring detector for testing blend engine speed
    mock_ring = MagicMock(spec=FraudRingDetector)
    mock_ring.assess_account.return_value = 0.45
    
    engine = HybridRiskEngine(ring_detector=mock_ring)
    
    latencies = []
    
    for _ in range(iterations):
        start = time.perf_counter()
        engine.evaluate_transaction(
            ml_score=random.uniform(0.0, 1.0),
            graph_score=random.uniform(0.0, 1.0),
            rules_breached=random.randint(0, 5),
            account_id="acct_123"
        )
        duration = time.perf_counter() - start
        latencies.append(duration * 1000) # Convert to ms

    avg_lat = statistics.mean(latencies)
    p95_lat = statistics.quantiles(latencies, n=20)[18]
    p99_lat = statistics.quantiles(latencies, n=100)[98]
    tps = iterations / (sum(latencies) / 1000)

    print("Hybrid Risk Engine:")
    print(f"  Count: {iterations}")
    print(f"  Avg Latency: {avg_lat:.4f} ms")
    print(f"  p95 Latency: {p95_lat:.4f} ms")
    print(f"  p99 Latency: {p99_lat:.4f} ms")
    print(f"  Projected TPS: {tps:.2f}")


def benchmark_graph_operations(iterations: int = 100):
    print("\n--- Benchmarking Neo4j Operations (Simulated / Live Connection Check) ---")
    # Check if a live Neo4j driver is configured and running
    from neo4j import GraphDatabase
    s = get_settings()
    
    driver = None
    try:
        driver = GraphDatabase.driver(s.neo4j.uri, auth=(s.neo4j.username, s.neo4j.password))
        with driver.session() as session:
            session.run("RETURN 1")
        print("Live Neo4j instance detected! Running live write benchmark...")
    except Exception:
        print("Neo4j instance offline. Running simulated/mock write benchmark...")
        driver = MagicMock()
        session_mock = MagicMock()
        session_mock.run.return_value = None
        driver.session.return_value.__enter__.return_value = session_mock

    latencies = []
    
    # Simple write representation: MERGE Transaction node
    query = (
        "MERGE (t:Transaction {id: $tx_id}) "
        "SET t.amount = $amount, t.date = $date "
        "RETURN t"
    )
    
    for i in range(iterations):
        tx_id = f"tx_bench_{i}"
        amount = round(random.uniform(10.0, 5000.0), 2)
        date_str = "2026-07-01 12:00:00"
        
        start = time.perf_counter()
        with driver.session() as session:
            session.run(query, tx_id=tx_id, amount=amount, date=date_str)
        duration = time.perf_counter() - start
        latencies.append(duration * 1000)
        
    avg_lat = statistics.mean(latencies)
    p95_lat = statistics.quantiles(latencies, n=20)[18]
    p99_lat = statistics.quantiles(latencies, n=100)[98]
    tps = iterations / (sum(latencies) / 1000)

    print("Neo4j Transaction Writes:")
    print(f"  Count: {iterations}")
    print(f"  Avg Latency: {avg_lat:.2f} ms")
    print(f"  p95 Latency: {p95_lat:.2f} ms")
    print(f"  p99 Latency: {p99_lat:.2f} ms")
    print(f"  Projected TPS: {tps:.2f}")


def main():
    print("=" * 60)
    print("  FraudShield v3.0.0 Performance Benchmarking Suite")
    print("=" * 60)
    
    benchmark_cpp_cleaning(2000)
    benchmark_inference_service(1000)
    benchmark_risk_engine(1000)
    benchmark_graph_operations(100)
    
    print("\n" + "=" * 60)
    print("  Benchmark Run Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
