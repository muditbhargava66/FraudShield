"""
FraudShield Graph Builder utilizing Neo4j to assemble transactional edges.
Author: Mudit Bhargava
"""

import logging
from typing import Dict, Any

try:
    from neo4j import GraphDatabase
except ImportError:
    pass

logger = logging.getLogger(__name__)

class FraudGraphBuilder:
    """
    Connects to Neo4j to securely ingest real-time transactions into an active graph network.
    Maps Accounts, IPs, and Devices as distinct nodes to track networked fraud rings.
    """

    def __init__(self, uri: str = "bolt://localhost:7687", user: str = "neo4j", password: str = "fraudshield_secret_v3"):
        self._uri = uri
        self._user = user
        self._password = password
        
        try:
            self.driver = GraphDatabase.driver(self._uri, auth=(self._user, self._password))
            logger.info("Successfully bound to Neo4j Database at %s", self._uri)
            self._initialize_constraints()
        except Exception as e:
            logger.warning("Failed to initialize Neo4j Graph Builder connection natively: %s", e)
            self.driver = None

    def _initialize_constraints(self):
        """
        Builds Neo4j schema constraints silently ensuring nodal uniqueness avoiding duplication anomalies.
        """
        constraints = [
            "CREATE CONSTRAINT account_id IF NOT EXISTS FOR (a:Account) REQUIRE a.id IS UNIQUE",
            "CREATE CONSTRAINT device_id IF NOT EXISTS FOR (d:Device) REQUIRE d.id IS UNIQUE",
            "CREATE CONSTRAINT ip_address IF NOT EXISTS FOR (i:IPAddress) REQUIRE i.address IS UNIQUE",
            "CREATE CONSTRAINT transaction_id IF NOT EXISTS FOR (t:Transaction) REQUIRE t.id IS UNIQUE"
        ]
        if self.driver:
            with self.driver.session() as session:
                for query in constraints:
                    session.run(query)
            logger.info("Successfully established Neo4j uniqueness constraints.")

    def add_transaction(self, payload: Dict[str, Any]):
        """
        Injects a single streaming payload directly into the Graph Database mapping edges securely.
        """
        query = """
        MERGE (a:Account {id: $account_id})
        MERGE (d:Device {id: $device_id})
        MERGE (i:IPAddress {address: $ip_address})
        
        CREATE (t:Transaction {
            id: $transaction_id, 
            amount: $amount, 
            time: $time,
            merchant: $merchant_id
        })
        
        CREATE (a)-[:INITIATED]->(t)
        CREATE (t)-[:FROM_DEVICE]->(d)
        CREATE (t)-[:FROM_IP]->(i)
        """
        params = {
            "account_id": payload.get("account_id"),
            "device_id": payload.get("device_id"),
            "ip_address": payload.get("ip_address"),
            "transaction_id": payload.get("transaction_id"),
            "amount": payload.get("amount"),
            "time": payload.get("transaction_time"),
            "merchant_id": payload.get("merchant_id")
        }
        
        if self.driver:
            try:
                with self.driver.session() as session:
                    session.run(query, **params)
            except Exception as e:
                logger.error("Failed executing structural graph projection: %s", e)
        else:
            # Mock structure logging
            logger.debug("Neo4j inactive. Skipped appending transaction %s to graph.", params["transaction_id"])
            
    def close(self):
        """Close graph drivers safely."""
        if self.driver:
            self.driver.close()
