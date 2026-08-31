"""
Pluggable streaming broker abstraction supporting Kafka and Redpanda.

Both brokers use the Kafka wire protocol, so ``confluent-kafka`` is the shared
client library. The factory classes differ only in broker-specific configuration
defaults (security protocol, SASL mechanisms, etc.).
"""

from __future__ import annotations

import enum
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from fraudshield.config.settings import KafkaSettings, get_settings

logger = logging.getLogger(__name__)

try:
    from confluent_kafka import Consumer, Producer
except ImportError:  # pragma: no cover - optional dependency
    Consumer = None  # type: ignore[assignment,misc]
    Producer = None  # type: ignore[assignment,misc]


class BrokerType(enum.Enum):
    """Supported streaming broker types."""

    KAFKA = "kafka"
    REDPANDA = "redpanda"


class BrokerFactory(ABC):
    """Abstract factory for creating streaming producers and consumers."""

    @abstractmethod
    def create_producer(self, kafka: KafkaSettings, **overrides: Any) -> Any:
        """Create a producer instance configured for this broker type."""

    @abstractmethod
    def create_consumer(self, kafka: KafkaSettings, **overrides: Any) -> Any:
        """Create a consumer instance configured for this broker type."""

    @staticmethod
    def _require_producer() -> None:
        if Producer is None:
            raise ImportError("confluent_kafka is required for streaming producer integrations.")

    @staticmethod
    def _require_consumer() -> None:
        if Consumer is None:
            raise ImportError("confluent_kafka is required for streaming consumer integrations.")

    @staticmethod
    def _apply_sasl(config: Dict[str, Any], kafka: KafkaSettings) -> None:
        if not kafka.sasl_username:
            return
        config.setdefault("security.protocol", "SASL_SSL")
        config.setdefault("sasl.mechanisms", "PLAIN")
        config["sasl.username"] = kafka.sasl_username
        if kafka.sasl_password:
            config["sasl.password"] = kafka.sasl_password


class KafkaBrokerFactory(BrokerFactory):
    """Factory for Apache Kafka brokers."""

    def create_producer(self, kafka: KafkaSettings, **overrides: Any) -> Any:
        self._require_producer()
        config: Dict[str, Any] = {
            "bootstrap.servers": kafka.bootstrap_servers,
            "client.id": kafka.producer_client_id,
            "acks": "all",
            "linger.ms": 5,
            "batch.num.messages": 1000,
            "compression.type": "lz4",
            "enable.idempotence": True,
        }
        self._apply_sasl(config, kafka)
        config.update(overrides)
        return Producer(config)  # type: ignore[misc]

    def create_consumer(self, kafka: KafkaSettings, **overrides: Any) -> Any:
        self._require_consumer()
        config: Dict[str, Any] = {
            "bootstrap.servers": kafka.bootstrap_servers,
            "group.id": kafka.group_id,
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
        }
        self._apply_sasl(config, kafka)
        config.update(overrides)
        return Consumer(config)  # type: ignore[misc]


class RedpandaBrokerFactory(BrokerFactory):
    """
    Factory for Redpanda brokers.

    Redpanda implements the Kafka wire protocol, so ``confluent-kafka`` is
    used as the client. The main differences from Kafka are:
    - ``security.protocol`` defaults to ``SASL_SSL`` for Redpanda Cloud.
    - ``sasl.mechanisms`` defaults to ``SCRAM-SHA-256``.
    - No Zookeeper dependency (not relevant at the client level).
    """

    def create_producer(self, kafka: KafkaSettings, **overrides: Any) -> Any:
        self._require_producer()
        config: Dict[str, Any] = {
            "bootstrap.servers": kafka.bootstrap_servers,
            "client.id": kafka.producer_client_id,
            "acks": "all",
            "linger.ms": 5,
            "compression.type": "lz4",
            "enable.idempotence": True,
            # Redpanda-specific defaults (overridable)
            "security.protocol": "SASL_SSL",
            "sasl.mechanisms": "SCRAM-SHA-256",
        }
        if kafka.sasl_username:
            config["sasl.username"] = kafka.sasl_username
        if kafka.sasl_password:
            config["sasl.password"] = kafka.sasl_password
        config.update(overrides)
        return Producer(config)  # type: ignore[misc]

    def create_consumer(self, kafka: KafkaSettings, **overrides: Any) -> Any:
        self._require_consumer()
        config: Dict[str, Any] = {
            "bootstrap.servers": kafka.bootstrap_servers,
            "group.id": kafka.group_id,
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
            # Redpanda-specific defaults (overridable)
            "security.protocol": "SASL_SSL",
            "sasl.mechanisms": "SCRAM-SHA-256",
        }
        if kafka.sasl_username:
            config["sasl.username"] = kafka.sasl_username
        if kafka.sasl_password:
            config["sasl.password"] = kafka.sasl_password
        config.update(overrides)
        return Consumer(config)  # type: ignore[misc]


_FACTORIES: Dict[BrokerType, BrokerFactory] = {
    BrokerType.KAFKA: KafkaBrokerFactory(),
    BrokerType.REDPANDA: RedpandaBrokerFactory(),
}


def get_broker_factory(broker_type: str = "kafka") -> BrokerFactory:
    """
    Return the broker factory for the given type string.

    Args:
        broker_type: One of ``"kafka"`` or ``"redpanda"`` (case-insensitive).

    Raises:
        ValueError: If the broker type is not supported.
    """
    try:
        key = BrokerType(broker_type.strip().lower())
    except ValueError:
        valid = ", ".join(bt.value for bt in BrokerType)
        raise ValueError(f"Unsupported broker type '{broker_type}'. Valid types: {valid}") from None
    return _FACTORIES[key]


def create_broker_producer(kafka: Optional[KafkaSettings] = None, **overrides: Any) -> Any:
    """Convenience: create a producer using the configured broker type."""
    kafka = kafka or get_settings().kafka
    factory = get_broker_factory(kafka.broker_type)
    return factory.create_producer(kafka, **overrides)


def create_broker_consumer(kafka: Optional[KafkaSettings] = None, **overrides: Any) -> Any:
    """Convenience: create a consumer using the configured broker type."""
    kafka = kafka or get_settings().kafka
    factory = get_broker_factory(kafka.broker_type)
    return factory.create_consumer(kafka, **overrides)
