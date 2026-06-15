"""
FraudShield Graph Builder utilizing Neo4j to assemble transactional edges.
Author: Mudit Bhargava
"""

import logging
from typing import Any, Dict, Optional

from fraudshield.config.settings import RuntimeSettings, get_settings
from fraudshield.graph.repository import FraudGraphRepository
from fraudshield.runtime.resources import create_neo4j_driver

logger = logging.getLogger(__name__)


class FraudGraphBuilder:
    """
    Connects to Neo4j to securely ingest real-time transactions into an active graph network.
    Maps Accounts, IPs, and Devices as distinct nodes to track networked fraud rings.
    """

    def __init__(self, settings: Optional[RuntimeSettings] = None, driver=None):
        self.settings = settings or get_settings()
        self.driver = None
        self.repository: Optional[FraudGraphRepository] = None

        try:
            self.driver = driver or create_neo4j_driver(self.settings.neo4j)
            self.repository = FraudGraphRepository(self.driver)
            self.repository.initialize_constraints()
            logger.info("Successfully bound to Neo4j Database at %s", self.settings.neo4j.uri)
        except Exception as e:
            logger.warning("Failed to initialize Neo4j Graph Builder connection natively: %s", e)
            self.driver = None
            self.repository = None

    def add_transaction(self, payload: Dict[str, Any]):
        """
        Injects a single streaming payload directly into the Graph Database mapping edges securely.
        """
        if self.repository:
            try:
                self.repository.upsert_transaction(payload)
            except Exception as e:
                logger.error("Failed executing structural graph projection: %s", e)
        else:
            logger.debug("Neo4j inactive. Skipped appending transaction %s to graph.", payload.get("transaction_id"))

    def graph_risk(self, payload: Dict[str, Any]) -> float:
        if not self.repository:
            return 0.0
        try:
            return self.repository.entity_risk(payload)
        except Exception as exc:
            logger.warning("Failed calculating graph risk: %s", exc)
            return 0.0

    def close(self):
        """Close graph drivers safely."""
        if self.driver:
            self.driver.close()
