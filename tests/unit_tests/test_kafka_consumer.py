"""
Unit tests for the Kafka transaction consumer message-handling loop.
"""

from unittest.mock import MagicMock, patch

from fraudshield.streaming.kafka_consumer import TransactionConsumer


class _FakeMessage:
    def __init__(self, value: bytes):
        self._value = value

    def value(self) -> bytes:
        return self._value

    def error(self):
        return None


class TestStartConsuming:
    def _make_consumer(self, messages):
        mock_kafka_consumer = MagicMock()
        mock_kafka_consumer.poll.side_effect = list(messages) + [KeyboardInterrupt]
        consumer = TransactionConsumer(consumer=mock_kafka_consumer)
        return consumer, mock_kafka_consumer

    def test_commits_after_each_successful_message(self):
        consumer, mock_kafka_consumer = self._make_consumer(
            [_FakeMessage(b'{"transaction_id": "tx_1"}'), _FakeMessage(b'{"transaction_id": "tx_2"}')]
        )
        handler = MagicMock()

        consumer.start_consuming(handler)

        assert handler.call_count == 2
        assert mock_kafka_consumer.commit.call_count == 2

    def test_failed_handler_still_commits_and_records_failure(self):
        """A failing handler must not silently drop messages: the offset is
        committed explicitly and the failure is recorded in metrics."""
        consumer, mock_kafka_consumer = self._make_consumer(
            [_FakeMessage(b'{"transaction_id": "tx_1"}'), _FakeMessage(b'{"transaction_id": "tx_2"}')]
        )
        handler = MagicMock(side_effect=[None, RuntimeError("processing boom")])

        with patch("fraudshield.monitoring.metrics.get_metrics") as mock_get_metrics:
            collector = MagicMock()
            mock_get_metrics.return_value = collector
            consumer.start_consuming(handler)

        assert handler.call_count == 2
        assert mock_kafka_consumer.commit.call_count == 2
        collector.record_transaction.assert_called_once_with(source="streaming", status="failed")

    def test_malformed_json_is_skipped_and_committed(self):
        """Undecodable payloads are logged, counted as failed, and committed so
        they cannot stall the partition."""
        consumer, mock_kafka_consumer = self._make_consumer(
            [_FakeMessage(b"not-json"), _FakeMessage(b'{"transaction_id": "tx_2"}')]
        )
        handler = MagicMock()

        with patch("fraudshield.monitoring.metrics.get_metrics") as mock_get_metrics:
            collector = MagicMock()
            mock_get_metrics.return_value = collector
            consumer.start_consuming(handler)

        assert handler.call_count == 1
        assert mock_kafka_consumer.commit.call_count == 2
        collector.record_transaction.assert_called_once_with(source="streaming", status="failed")
