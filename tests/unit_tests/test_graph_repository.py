"""
Unit tests for the Neo4j graph repository helpers.
"""

from unittest.mock import MagicMock

import pytest

from fraudshield.graph.repository import FraudGraphRepository


def _make_repository():
    mock_session = MagicMock()
    mock_driver = MagicMock()
    mock_driver.session.return_value.__enter__ = MagicMock(return_value=mock_session)
    mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)
    return FraudGraphRepository(mock_driver), mock_session


class TestUpsertTransaction:
    def test_requires_transaction_id(self):
        repository, _ = _make_repository()
        with pytest.raises(ValueError, match="transaction_id"):
            repository.upsert_transaction({"user_id": "acct_1"})

    def test_requires_user_or_account_id(self):
        repository, _ = _make_repository()
        with pytest.raises(ValueError, match="user_id"):
            repository.upsert_transaction({"transaction_id": "tx_1"})

    def test_allows_null_device_and_ip(self):
        """Payloads without device/IP must upsert instead of crashing Neo4j."""
        repository, mock_session = _make_repository()

        repository.upsert_transaction(
            {
                "transaction_id": "tx_1",
                "user_id": "acct_1",
                "device_id": None,
                "ip_address": None,
                "amount": 10.0,
            }
        )

        mock_session.run.assert_called_once()
        query = mock_session.run.call_args[0][0]
        params = mock_session.run.call_args[1]
        assert params["device_id"] is None
        assert params["ip_address"] is None
        # Null entities are skipped via conditional FOREACH clauses.
        assert query.count("FOREACH") == 2

    def test_upsert_with_device_and_ip(self):
        repository, mock_session = _make_repository()

        repository.upsert_transaction(
            {
                "transaction_id": "tx_2",
                "account_id": "acct_9",
                "device_id": "dev_1",
                "ip_address": "10.0.0.1",
            }
        )

        params = mock_session.run.call_args[1]
        assert params["user_id"] == "acct_9"
        assert params["device_id"] == "dev_1"
        assert params["ip_address"] == "10.0.0.1"


class TestEntityRisk:
    def test_returns_zero_without_record(self):
        repository, mock_session = _make_repository()
        mock_session.run.return_value.single.return_value = None

        assert repository.entity_risk({"device_id": "dev_1", "ip_address": "10.0.0.1"}) == 0.0

    def test_caps_risk_at_one(self):
        repository, mock_session = _make_repository()
        record = MagicMock()
        record.get.side_effect = lambda key, default=None: {"device_count": 25, "ip_count": 3}[key]
        mock_session.run.return_value.single.return_value = record

        assert repository.entity_risk({"device_id": "dev_1", "ip_address": "10.0.0.1"}) == 1.0
