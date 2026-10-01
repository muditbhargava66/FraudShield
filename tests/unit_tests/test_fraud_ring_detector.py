"""
Unit tests for fraud ring detection via Louvain community analysis.
"""

from unittest.mock import MagicMock, patch

from fraudshield.graph.fraud_ring_detector import FraudRing, FraudRingDetector


class TestFraudRingDataclass:
    def test_risk_score_clamped_to_one(self):
        ring = FraudRing(
            ring_id="RING_test",
            member_accounts=["A", "B", "C"],
            shared_entities=["D1"],
            risk_score=1.5,
        )
        assert ring.risk_score == 1.0

    def test_risk_score_clamped_to_zero(self):
        ring = FraudRing(
            ring_id="RING_test",
            member_accounts=["A"],
            shared_entities=[],
            risk_score=-0.5,
        )
        assert ring.risk_score == 0.0


class TestFraudRingDetector:
    def test_extract_subgraph_with_mock_driver(self):
        mock_session = MagicMock()
        mock_record = {
            "neighbor_id": "acct_2",
            "shared_labels": ["Device"],
            "shared_id": "dev_1",
            "device_id": "dev_1",
            "ip_address": None,
            "edge_weight": 3,
        }
        mock_session.run.return_value = [mock_record]
        mock_driver = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        detector = FraudRingDetector(mock_driver, min_ring_size=2)
        records = detector.extract_subgraph("acct_1")

        assert len(records) == 1
        assert records[0]["neighbor_id"] == "acct_2"
        mock_session.run.assert_called_once()

    def test_extract_subgraph_returns_empty_on_failure(self):
        mock_driver = MagicMock()
        mock_driver.session.side_effect = Exception("Connection failed")

        detector = FraudRingDetector(mock_driver)
        records = detector.extract_subgraph("acct_1")

        assert records == []

    def test_detect_rings_empty_graph(self):
        mock_driver = MagicMock()
        mock_session = MagicMock()
        mock_session.run.return_value = []
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        detector = FraudRingDetector(mock_driver, min_ring_size=2)
        rings = detector.detect_rings("acct_1")

        assert rings == []

    def test_detect_rings_builds_graph(self):
        """Neighbors sharing a device with the target must form a detected ring."""
        mock_driver = MagicMock()
        mock_session = MagicMock()

        # Three neighbors all share the same device with the target account,
        # so they are mutually connected and form a dense 4-node community.
        records = [
            {"neighbor_id": f"acct_{i}", "shared_id": "dev_shared", "edge_weight": 2}
            for i in range(2, 5)
        ]
        mock_session.run.return_value = records
        mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        detector = FraudRingDetector(mock_driver, min_ring_size=3)
        rings = detector.detect_rings("acct_1")

        assert len(rings) == 1
        ring = rings[0]
        assert set(ring.member_accounts) == {"acct_1", "acct_2", "acct_3", "acct_4"}
        assert "dev_shared" in ring.shared_entities
        assert ring.risk_score > 0.0
        assert ring.density == 1.0  # fully connected community

    def test_build_graph_connects_neighbors_sharing_entities(self):
        """Neighbors sharing a device/IP must be linked to each other, not just the target."""
        records = [
            {"neighbor_id": "acct_2", "shared_id": "dev_shared", "edge_weight": 2},
            {"neighbor_id": "acct_3", "shared_id": "dev_shared", "edge_weight": 1},
            {"neighbor_id": "acct_4", "shared_id": "ip_other", "edge_weight": 1},
        ]

        graph = FraudRingDetector._build_graph("acct_1", records)

        assert graph.has_edge("acct_1", "acct_2")
        assert graph.has_edge("acct_1", "acct_3")
        # Neighbors that share dev_shared are connected to each other.
        assert graph.has_edge("acct_2", "acct_3")
        # acct_4 shares a different entity with the target only.
        assert not graph.has_edge("acct_2", "acct_4")
        assert not graph.has_edge("acct_3", "acct_4")
        # Shared entities are tracked on the target and neighbor nodes.
        assert "dev_shared" in graph.nodes["acct_1"]["shared_entities"]
        assert "dev_shared" in graph.nodes["acct_2"]["shared_entities"]
        assert "ip_other" in graph.nodes["acct_4"]["shared_entities"]

    def test_assess_account_with_ring(self):
        """Mock detect_rings to return a ring and verify risk score aggregation."""
        mock_driver = MagicMock()
        detector = FraudRingDetector(mock_driver, min_ring_size=3)

        fake_rings = [
            FraudRing(
                ring_id="RING_a",
                member_accounts=["acct_1", "acct_2", "acct_3"],
                shared_entities=["dev_1"],
                risk_score=0.85,
            ),
            FraudRing(
                ring_id="RING_b",
                member_accounts=["acct_1", "acct_4", "acct_5"],
                shared_entities=["ip_1"],
                risk_score=0.6,
            ),
        ]

        with patch.object(detector, "detect_rings", return_value=fake_rings):
            score = detector.assess_account("acct_1")
            assert score == 0.85  # max of 0.85 and 0.6

    def test_assess_account_no_rings(self):
        mock_driver = MagicMock()
        detector = FraudRingDetector(mock_driver)

        with patch.object(detector, "detect_rings", return_value=[]):
            score = detector.assess_account("acct_1")
            assert score == 0.0

    def test_graceful_degradation_on_neo4j_failure(self):
        """Verify assess_account returns 0.0 when Neo4j is unreachable."""
        mock_driver = MagicMock()
        mock_driver.session.side_effect = Exception("Neo4j unreachable")

        detector = FraudRingDetector(mock_driver, min_ring_size=2)
        score = detector.assess_account("acct_1")

        assert score == 0.0

    def test_compute_risk_score(self):
        score = FraudRingDetector._compute_risk_score(ring_size=5, density=0.8)
        assert 0.0 <= score <= 1.0
        # 1 - exp(-0.3 * 5 * 0.8) = 1 - exp(-1.2) ≈ 0.6988
        assert abs(score - 0.6988) < 0.01

    def test_make_ring_id_deterministic(self):
        id1 = FraudRingDetector._make_ring_id(["A", "B", "C"])
        id2 = FraudRingDetector._make_ring_id(["A", "B", "C"])
        assert id1 == id2
        assert id1.startswith("RING_")

    def test_make_ring_id_order_independent(self):
        """Sorted members should produce the same ID regardless of input order."""
        id1 = FraudRingDetector._make_ring_id(["C", "A", "B"])
        id2 = FraudRingDetector._make_ring_id(["A", "B", "C"])
        assert id1 == id2

    def test_min_ring_size_enforced(self):
        detector = FraudRingDetector(MagicMock(), min_ring_size=1)
        assert detector.min_ring_size == 2  # min enforced at 2
