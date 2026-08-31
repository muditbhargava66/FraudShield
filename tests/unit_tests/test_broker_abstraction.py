"""
Unit tests for the streaming broker abstraction layer.
"""

from unittest.mock import MagicMock, patch

import pytest

from fraudshield.config.settings import KafkaSettings
from fraudshield.streaming.broker import (
    BrokerType,
    KafkaBrokerFactory,
    RedpandaBrokerFactory,
    create_broker_consumer,
    create_broker_producer,
    get_broker_factory,
)


def _make_kafka_settings(**overrides):
    defaults = {
        "bootstrap_servers": "localhost:9092",
        "topic": "test-topic",
        "group_id": "test-group",
        "producer_client_id": "test-producer",
        "consumer_client_id": "test-consumer",
        "poll_timeout_seconds": 1.0,
        "broker_type": "kafka",
    }
    defaults.update(overrides)
    return KafkaSettings(**defaults)


class TestBrokerTypeEnum:
    def test_kafka_value(self):
        assert BrokerType.KAFKA.value == "kafka"

    def test_redpanda_value(self):
        assert BrokerType.REDPANDA.value == "redpanda"


class TestKafkaBrokerFactory:
    @patch("fraudshield.streaming.broker.Producer")
    def test_create_producer(self, mock_producer_cls):
        mock_producer_cls.return_value = MagicMock(name="producer")
        factory = KafkaBrokerFactory()
        settings = _make_kafka_settings()

        producer = factory.create_producer(settings)
        assert producer is not None

        mock_producer_cls.assert_called_once()
        config = mock_producer_cls.call_args[0][0]
        assert config["bootstrap.servers"] == "localhost:9092"
        assert config["acks"] == "all"
        assert config["compression.type"] == "lz4"
        assert config["enable.idempotence"] is True

    @patch("fraudshield.streaming.broker.Consumer")
    def test_create_consumer(self, mock_consumer_cls):
        mock_consumer_cls.return_value = MagicMock(name="consumer")
        factory = KafkaBrokerFactory()
        settings = _make_kafka_settings()

        consumer = factory.create_consumer(settings)
        assert consumer is not None

        mock_consumer_cls.assert_called_once()
        config = mock_consumer_cls.call_args[0][0]
        assert config["bootstrap.servers"] == "localhost:9092"
        assert config["group.id"] == "test-group"
        assert config["auto.offset.reset"] == "latest"

    @patch("fraudshield.streaming.broker.Producer")
    def test_create_producer_with_overrides(self, mock_producer_cls):
        mock_producer_cls.return_value = MagicMock()
        factory = KafkaBrokerFactory()
        settings = _make_kafka_settings()

        factory.create_producer(settings, acks="1", **{"linger.ms": 10})

        config = mock_producer_cls.call_args[0][0]
        assert config["acks"] == "1"  # overridden
        assert config["linger.ms"] == 10  # overridden

    @patch("fraudshield.streaming.broker.Producer")
    def test_create_producer_wires_sasl_credentials(self, mock_producer_cls):
        mock_producer_cls.return_value = MagicMock()
        factory = KafkaBrokerFactory()
        settings = _make_kafka_settings(sasl_username="svc-fraud", sasl_password="secret")

        factory.create_producer(settings)

        config = mock_producer_cls.call_args[0][0]
        assert config["sasl.username"] == "svc-fraud"
        assert config["sasl.password"] == "secret"
        assert config["security.protocol"] == "SASL_SSL"
        assert config["sasl.mechanisms"] == "PLAIN"

    @patch("fraudshield.streaming.broker.Consumer")
    def test_create_consumer_wires_sasl_credentials(self, mock_consumer_cls):
        mock_consumer_cls.return_value = MagicMock()
        factory = KafkaBrokerFactory()
        settings = _make_kafka_settings(sasl_username="svc-fraud", sasl_password="secret")

        factory.create_consumer(settings)

        config = mock_consumer_cls.call_args[0][0]
        assert config["sasl.username"] == "svc-fraud"
        assert config["sasl.password"] == "secret"

    @patch("fraudshield.streaming.broker.Producer")
    def test_create_producer_without_credentials_omits_sasl(self, mock_producer_cls):
        mock_producer_cls.return_value = MagicMock()
        factory = KafkaBrokerFactory()
        settings = _make_kafka_settings()

        factory.create_producer(settings)

        config = mock_producer_cls.call_args[0][0]
        assert "sasl.username" not in config
        assert "sasl.password" not in config
        assert "security.protocol" not in config

    @patch("fraudshield.streaming.broker.Producer")
    def test_sasl_defaults_are_overridable(self, mock_producer_cls):
        mock_producer_cls.return_value = MagicMock()
        factory = KafkaBrokerFactory()
        settings = _make_kafka_settings(sasl_username="svc-fraud", sasl_password="secret")

        factory.create_producer(settings, **{"security.protocol": "SASL_PLAINTEXT", "sasl.mechanisms": "SCRAM-SHA-512"})

        config = mock_producer_cls.call_args[0][0]
        assert config["security.protocol"] == "SASL_PLAINTEXT"
        assert config["sasl.mechanisms"] == "SCRAM-SHA-512"


class TestRedpandaBrokerFactory:
    @patch("fraudshield.streaming.broker.Producer")
    def test_create_producer_has_redpanda_defaults(self, mock_producer_cls):
        mock_producer_cls.return_value = MagicMock()
        factory = RedpandaBrokerFactory()
        settings = _make_kafka_settings(broker_type="redpanda")

        factory.create_producer(settings)

        config = mock_producer_cls.call_args[0][0]
        assert config["security.protocol"] == "SASL_SSL"
        assert config["sasl.mechanisms"] == "SCRAM-SHA-256"
        assert config["acks"] == "all"

    @patch("fraudshield.streaming.broker.Consumer")
    def test_create_consumer_has_redpanda_defaults(self, mock_consumer_cls):
        mock_consumer_cls.return_value = MagicMock()
        factory = RedpandaBrokerFactory()
        settings = _make_kafka_settings(broker_type="redpanda")

        factory.create_consumer(settings)

        config = mock_consumer_cls.call_args[0][0]
        assert config["security.protocol"] == "SASL_SSL"
        assert config["sasl.mechanisms"] == "SCRAM-SHA-256"


class TestGetBrokerFactory:
    def test_kafka_dispatcher(self):
        factory = get_broker_factory("kafka")
        assert isinstance(factory, KafkaBrokerFactory)

    def test_redpanda_dispatcher(self):
        factory = get_broker_factory("redpanda")
        assert isinstance(factory, RedpandaBrokerFactory)

    def test_case_insensitive(self):
        factory = get_broker_factory("KAFKA")
        assert isinstance(factory, KafkaBrokerFactory)

    def test_invalid_broker_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported broker type"):
            get_broker_factory("rabbitmq")

    def test_whitespace_stripped(self):
        factory = get_broker_factory("  kafka  ")
        assert isinstance(factory, KafkaBrokerFactory)


class TestBrokerConvenienceFunctions:
    @patch("fraudshield.streaming.broker.Producer")
    def test_create_broker_producer_uses_settings(self, mock_producer_cls):
        mock_producer_cls.return_value = MagicMock()
        settings = _make_kafka_settings(broker_type="kafka")

        create_broker_producer(kafka=settings)

        mock_producer_cls.assert_called_once()

    @patch("fraudshield.streaming.broker.Consumer")
    def test_create_broker_consumer_uses_settings(self, mock_consumer_cls):
        mock_consumer_cls.return_value = MagicMock()
        settings = _make_kafka_settings(broker_type="redpanda")

        create_broker_consumer(kafka=settings)

        mock_consumer_cls.assert_called_once()
        config = mock_consumer_cls.call_args[0][0]
        assert config["security.protocol"] == "SASL_SSL"
