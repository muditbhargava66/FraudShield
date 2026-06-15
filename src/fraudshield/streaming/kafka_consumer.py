"""
Kafka Consumer architecture for ingesting real-time transactions into FraudShield.
Author: Mudit Bhargava
"""

import json
import logging
from typing import Any, Callable, Dict

from fraudshield.config.settings import RuntimeSettings, get_settings
from fraudshield.runtime.logging import configure_logging
from fraudshield.runtime.resources import create_kafka_consumer

try:
    from confluent_kafka import KafkaError, KafkaException
except ImportError:  # pragma: no cover - optional dependency
    KafkaError = None  # type: ignore[assignment,misc]
    KafkaException = RuntimeError  # type: ignore[assignment,misc]

logger = logging.getLogger(__name__)


class TransactionConsumer:
    """
    Subscribes to high-frequency transaction streams from Kafka and passes them sequentially
    into the feature engineering and risk engine pipelines.
    """

    def __init__(
        self,
        bootstrap_servers: str | None = None,
        group_id: str | None = None,
        topic: str | None = None,
        *,
        settings: RuntimeSettings | None = None,
        consumer=None,
    ):
        """
        Initializes the Kafka consumer connection.

        Args:
            bootstrap_servers (str): Comma-separated list of Kafka broker addresses.
            group_id (str): The consumer group identifying this logical application.
            topic (str): The target Kafka topic for the transactions.
        """
        self.settings = settings or get_settings()
        self.topic = topic or self.settings.kafka.topic
        self.group_id = group_id or self.settings.kafka.group_id
        self.bootstrap_servers = bootstrap_servers or self.settings.kafka.bootstrap_servers

        try:
            self.consumer = consumer or create_kafka_consumer(
                self.settings.kafka,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
            )
            self.consumer.subscribe([self.topic])
            logger.info("Kafka TransactionConsumer successfully initialized and subscribed to %s", self.topic)
        except Exception as e:
            logger.error("Failed to initialize Kafka Consumer: %s", e)
            raise

    def start_consuming(self, message_handler: Callable[[Dict[str, Any]], None]):
        """
        Begins the continuous polling loop fetching messages from the Kafka topic.

        Args:
            message_handler (Callable): Target function triggered synchronously against every received JSON transaction.
        """
        logger.info("Starting continuous transaction ingestion tracking...")

        try:
            while True:
                msg = self.consumer.poll(timeout=self.settings.kafka.poll_timeout_seconds)

                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # Reached the end of the partition
                        continue
                    else:
                        raise KafkaException(msg.error())

                # Process the message
                try:
                    payload = json.loads(msg.value().decode("utf-8"))
                    message_handler(payload)
                except json.JSONDecodeError as decode_err:
                    logger.error("Failed to decode Kafka message payload: %s", decode_err)
                    continue
                except Exception as ex:
                    logger.error("Transaction processing pipeline failed organically: %s", ex)
                    continue

                self.consumer.commit(asynchronous=False)

        except KeyboardInterrupt:
            logger.info("Consumption interrupted by user signal.")
        finally:
            self.consumer.close()
            logger.info("Consumer shutdown complete.")

    def close(self) -> None:
        self.consumer.close()


def _dummy_print_handler(payload: Dict[str, Any]):
    """
    Basic output handler for local testing/verification.
    """
    print(f"Consumed Transaction -> ID: {payload.get('transaction_id')} | Amount: ${payload.get('amount')} | ACC: {payload.get('account_id')}")


if __name__ == "__main__":
    configure_logging(component="kafka_consumer")
    consumer_app = TransactionConsumer()
    consumer_app.start_consuming(_dummy_print_handler)
