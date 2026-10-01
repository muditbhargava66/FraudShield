"""
Fraud ring detection via community analysis on the Neo4j transaction graph.

Identifies coordinated fraud rings by finding communities of accounts connected
through shared devices and IP addresses. Uses Louvain community detection on
the 2-hop neighborhood subgraph.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Any, Dict, List

try:
    import networkx as nx

    _HAS_NETWORKX = True
except ImportError:  # pragma: no cover - optional dependency
    nx = None  # type: ignore[assignment]
    _HAS_NETWORKX = False

logger = logging.getLogger(__name__)

# Cypher: fetch the 2-hop neighborhood of an account via shared devices/IPs
_NEIGHBORHOOD_QUERY = """
MATCH (target:Account {id: $account_id})-[:INITIATED]->(:Transaction)-[:FROM_DEVICE|FROM_IP]->(shared)
      <-[:FROM_DEVICE|FROM_IP]-(:Transaction)<-[:INITIATED]-(neighbor:Account)
WHERE neighbor.id <> $account_id
RETURN neighbor.id AS neighbor_id,
       labels(shared) AS shared_labels,
       coalesce(shared.id, shared.address) AS shared_id,
       CASE WHEN 'Device' IN labels(shared) THEN shared.id ELSE NULL END AS device_id,
       CASE WHEN 'IPAddress' IN labels(shared) THEN shared.address ELSE NULL END AS ip_address,
       count(*) AS edge_weight
"""


@dataclass
class FraudRing:
    """Represents a detected fraud ring (community of suspicious accounts)."""

    ring_id: str
    member_accounts: List[str]
    shared_entities: List[str]
    risk_score: float
    density: float = 0.0

    def __post_init__(self) -> None:
        if self.risk_score > 1.0:
            self.risk_score = 1.0
        if self.risk_score < 0.0:
            self.risk_score = 0.0


class FraudRingDetector:
    """
    Detects coordinated fraud rings by analyzing account communities in the
    Neo4j transaction graph.

    Accounts that share devices or IP addresses are connected by edges weighted
    by the number of shared entities. Louvain community detection then partitions
    the graph into clusters, and clusters exceeding ``min_ring_size`` are scored
    as potential fraud rings.
    """

    def __init__(self, driver: Any, min_ring_size: int = 3) -> None:
        self.driver = driver
        self.min_ring_size = max(min_ring_size, 2)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def extract_subgraph(self, account_id: str) -> List[Dict[str, Any]]:
        """
        Fetch the 2-hop neighborhood of *account_id* from Neo4j.

        Returns a list of dicts with keys: ``neighbor_id``, ``shared_id``,
        ``device_id``, ``ip_address``, ``edge_weight``.
        """
        try:
            with self.driver.session() as session:
                result = session.run(_NEIGHBORHOOD_QUERY, account_id=account_id)
                return [dict(record) for record in result]
        except Exception as exc:
            logger.warning("Failed to extract subgraph for %s: %s", account_id, exc)
            return []

    def detect_rings(self, account_id: str) -> List[FraudRing]:
        """
        Build a graph from the neighborhood and detect fraud rings via Louvain
        community detection.
        """
        if not _HAS_NETWORKX:
            logger.warning("networkx is required for fraud ring detection.")
            return []

        records = self.extract_subgraph(account_id)
        if not records:
            return []

        graph = self._build_graph(account_id, records)
        if graph.number_of_nodes() < self.min_ring_size:
            return []

        return self._find_communities(graph)

    def assess_account(self, account_id: str) -> float:
        """
        Return the maximum ring risk score for *account_id*, or 0.0 if the
        account is not part of any detected ring.
        """
        rings = self.detect_rings(account_id)
        if not rings:
            return 0.0
        return max(r.risk_score for r in rings)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_graph(account_id: str, records: List[Dict[str, Any]]) -> "nx.Graph":
        """Build a weighted undirected graph from Neo4j neighborhood records."""
        graph: nx.Graph = nx.Graph()
        graph.add_node(account_id)
        entity_neighbors: Dict[str, set] = {}

        def add_edge(left: str, right: str, weight: int) -> None:
            if graph.has_edge(left, right):
                graph[left][right]["weight"] += weight
            else:
                graph.add_edge(left, right, weight=weight)

        def track_shared(node: str, entity: str) -> None:
            shared = graph.nodes[node].get("shared_entities", set())
            shared.add(entity)
            graph.nodes[node]["shared_entities"] = shared

        for record in records:
            neighbor = record.get("neighbor_id")
            shared_id = record.get("shared_id") or ""
            weight = int(record.get("edge_weight", 1))
            if neighbor is None:
                continue

            graph.add_node(neighbor)
            add_edge(account_id, neighbor, weight)
            if shared_id:
                track_shared(account_id, shared_id)
                track_shared(neighbor, shared_id)
                entity_neighbors.setdefault(shared_id, set()).add(neighbor)

        # Link neighbors that share the same device/IP with each other so
        # communities reflect coordination, not just target-centric stars.
        for neighbors in entity_neighbors.values():
            members = sorted(neighbors)
            for i, left in enumerate(members):
                for right in members[i + 1 :]:
                    add_edge(left, right, 1)

        return graph

    def _find_communities(self, graph: "nx.Graph") -> List[FraudRing]:
        """Run Louvain community detection and return fraud rings."""
        try:
            communities = nx.community.louvain_communities(
                graph, weight="weight", seed=42
            )
        except Exception as exc:
            logger.warning("Louvain community detection failed: %s", exc)
            return []

        rings: List[FraudRing] = []
        for community_nodes in communities:
            members = sorted(community_nodes)
            if len(members) < self.min_ring_size:
                continue

            subgraph = graph.subgraph(community_nodes)
            density = nx.density(subgraph)
            shared = set()
            for node in community_nodes:
                shared.update(graph.nodes[node].get("shared_entities", set()))

            ring_id = self._make_ring_id(members)
            risk_score = self._compute_risk_score(len(members), density)

            rings.append(
                FraudRing(
                    ring_id=ring_id,
                    member_accounts=members,
                    shared_entities=sorted(shared),
                    risk_score=risk_score,
                    density=round(density, 4),
                )
            )

        return sorted(rings, key=lambda r: r.risk_score, reverse=True)

    @staticmethod
    def _compute_risk_score(ring_size: int, density: float) -> float:
        """
        Compute a risk score in [0, 1] based on ring size and graph density.

        Larger, denser rings are more suspicious. The formula uses a sigmoid-like
        scaling: ``1 - exp(-0.3 * size * density)``.
        """
        import math

        raw = 1.0 - math.exp(-0.3 * ring_size * density)
        return round(min(raw, 1.0), 4)

    @staticmethod
    def _make_ring_id(members: List[str]) -> str:
        """Generate a deterministic ring ID from sorted member accounts."""
        key = "|".join(sorted(members))
        return "RING_" + hashlib.sha256(key.encode()).hexdigest()[:12]
