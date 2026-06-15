"""
Idempotent graph repository helpers for Neo4j persistence.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class FraudGraphRepository:
    def __init__(self, driver) -> None:
        self.driver = driver

    def initialize_constraints(self) -> None:
        constraints = [
            "CREATE CONSTRAINT account_id IF NOT EXISTS FOR (a:Account) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT device_id IF NOT EXISTS FOR (d:Device) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT ip_address IF NOT EXISTS FOR (i:IPAddress) REQUIRE i.address IS UNIQUE",
            "CREATE CONSTRAINT transaction_id IF NOT EXISTS FOR (t:Transaction) REQUIRE t.id IS UNIQUE",
        ]
        with self.driver.session() as session:
            for query in constraints:
                session.run(query)

    def upsert_transaction(self, payload: Dict[str, Any]) -> None:
        query = """
        MERGE (a:Account {id: $user_id})
        MERGE (d:Device {id: $device_id})
        MERGE (i:IPAddress {address: $ip_address})
        MERGE (t:Transaction {id: $transaction_id})
        ON CREATE SET
            t.amount = $amount,
            t.time = $transaction_time,
            t.merchant = $merchant_id,
            t.currency = $currency,
            t.status = $status
        ON MATCH SET
            t.amount = coalesce(t.amount, $amount),
            t.time = coalesce(t.time, $transaction_time),
            t.merchant = coalesce(t.merchant, $merchant_id),
            t.currency = coalesce(t.currency, $currency),
            t.status = coalesce(t.status, $status)
        MERGE (a)-[:INITIATED]->(t)
        MERGE (t)-[:FROM_DEVICE]->(d)
        MERGE (t)-[:FROM_IP]->(i)
        """
        with self.driver.session() as session:
            session.run(query, **self._params(payload))

    def entity_risk(self, payload: Dict[str, Any]) -> float:
        query = """
        OPTIONAL MATCH (:Device {id: $device_id})<-[:FROM_DEVICE]-(:Transaction)
        WITH count(*) AS device_count
        OPTIONAL MATCH (:IPAddress {address: $ip_address})<-[:FROM_IP]-(:Transaction)
        RETURN device_count, count(*) AS ip_count
        """
        with self.driver.session() as session:
            record = session.run(query, device_id=payload.get("device_id"), ip_address=payload.get("ip_address")).single()
        if record is None:
            return 0.0
        device_count = float(record.get("device_count", 0))
        ip_count = float(record.get("ip_count", 0))
        return min(max(device_count, ip_count) / 10.0, 1.0)

    @staticmethod
    def _params(payload: Dict[str, Any]) -> Dict[str, Optional[Any]]:
        return {
            "transaction_id": payload.get("transaction_id"),
            "user_id": payload.get("user_id") or payload.get("account_id"),
            "device_id": payload.get("device_id"),
            "ip_address": payload.get("ip_address"),
            "amount": payload.get("amount"),
            "transaction_time": payload.get("transaction_date") or payload.get("transaction_time"),
            "merchant_id": payload.get("merchant_id"),
            "currency": payload.get("currency"),
            "status": payload.get("status"),
        }
