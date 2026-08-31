# Fraud Ring Detection

FraudShield detects coordinated fraud rings by finding communities of accounts connected through shared devices and IP addresses in the Neo4j transaction graph.

## Algorithm

The detection pipeline uses **Louvain community detection** on the 2-hop neighborhood subgraph of a target account:

1. **Subgraph extraction**: A Cypher query fetches all accounts connected to the target account within 2 hops via shared `Device` or `IPAddress` nodes. The query pattern is:
   ```
   (target:Account)-[:INITIATED]->(:Transaction)-[:FROM_DEVICE|FROM_IP]->(shared)
     <-[:FROM_DEVICE|FROM_IP]-(:Transaction)<-[:INITIATED]-(neighbor:Account)
   ```

2. **Graph construction**: The Neo4j records are converted into a `networkx.Graph` where:
   - Nodes are accounts (including the target)
   - Edges connect accounts that share devices/IPs, weighted by the number of shared entities
   - Node attributes track the set of shared entity IDs

3. **Community detection**: `nx.community.louvain_communities()` partitions the graph into clusters. Communities with fewer members than `min_ring_size` are discarded.

4. **Risk scoring**: Each community is scored using a sigmoid-like function:
   ```
   risk_score = 1 - exp(-0.3 * ring_size * density)
   ```
   Larger, denser rings produce higher scores. The score is clamped to [0.0, 1.0].

5. **Ring ID generation**: A deterministic SHA-256 hash of the sorted member account IDs, prefixed with `RING_`.

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_ring_size` | 3 | Minimum number of accounts in a community to qualify as a ring (enforced minimum: 2) |

## API

### `FraudRingDetector`

```python
from fraudshield.graph.fraud_ring_detector import FraudRingDetector

detector = FraudRingDetector(neo4j_driver, min_ring_size=3)

# Extract the 2-hop neighborhood from Neo4j
records = detector.extract_subgraph("account_123")

# Detect fraud rings via community analysis
rings = detector.detect_rings("account_123")

# Get the maximum ring risk score for an account (0.0 if no ring)
risk = detector.assess_account("account_123")
```

### `FraudRing` Dataclass

| Field | Type | Description |
|-------|------|-------------|
| `ring_id` | `str` | Deterministic hash identifier (e.g., `RING_a1b2c3d4e5f6`) |
| `member_accounts` | `List[str]` | Sorted list of account IDs in the ring |
| `shared_entities` | `List[str]` | Sorted list of shared device/IP IDs connecting the ring |
| `risk_score` | `float` | Risk score in [0.0, 1.0] |
| `density` | `float` | Graph density of the ring subgraph |

## Integration with Hybrid Risk Engine

The `HybridRiskEngine` accepts an optional `ring_detector` parameter. When provided, `evaluate_transaction()` computes the ring score for the given `account_id` and blends it into the graph score:

```python
from fraudshield.core.risk_engine.engine import HybridRiskEngine
from fraudshield.graph.fraud_ring_detector import FraudRingDetector

detector = FraudRingDetector(neo4j_driver)
engine = HybridRiskEngine(ring_detector=detector)

result = engine.evaluate_transaction(
    ml_score=0.5,
    graph_score=0.1,
    rules_breached=0,
    account_id="acct_123",
)
# If ring_score > graph_score, the composite score is boosted
```

The ring score replaces the graph score only when it is higher (`graph_score = max(graph_score, ring_score)`).

## Graceful Degradation

- If Neo4j is unreachable, `extract_subgraph()` returns an empty list and `assess_account()` returns 0.0
- If `networkx` is not installed, `detect_rings()` returns an empty list
- All exceptions in ring detection are caught and logged, never propagated to the caller

## Neo4j Schema Requirements

The fraud ring detector expects the following Neo4j graph structure:

- **Account nodes**: `(:Account {id: "..."})`
- **Transaction nodes**: `(:Transaction {...})`
- **Device nodes**: `(:Device {id: "..."})`
- **IPAddress nodes**: `(:IPAddress {address: "..."})`
- **Relationships**:
  - `(Account)-[:INITIATED]->(Transaction)`
  - `(Transaction)-[:FROM_DEVICE]->(Device)`
  - `(Transaction)-[:FROM_IP]->(IPAddress)`

These are populated by the existing `graph/repository.py` upsert logic.

## Testing

The test suite (`tests/unit_tests/test_fraud_ring_detector.py`) covers:

- Dataclass validation (risk score clamping)
- Subgraph extraction with mock Neo4j driver
- Empty graph handling
- Community detection on synthetic neighborhoods
- Risk score computation and determinism
- Ring ID generation (deterministic, order-independent)
- Graceful degradation on Neo4j failure
- Minimum ring size enforcement
