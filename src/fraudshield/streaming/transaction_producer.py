"""
Kafka Producer architecture for simulating real-time fraud transaction streams.
Author: Mudit Bhargava
"""

import json
import logging
import random
import time
import uuid
from typing import Dict, Any, Generator

from confluent_kafka import Producer
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class TransactionProducer:
    """
    Simulates high-frequency financial transactions and streams them to Kafka.
    """

    def __init__(self, bootstrap_servers: str = "localhost:9092", topic: str = "fraudshield-transactions"):
        """
        Initializes the Kafka producer connection.

        Args:
            bootstrap_servers (str): Comma-separated list of Kafka broker addresses.
            topic (str): The destination Kafka topic for the transactions.
        """
        self.topic = topic
        
        # Confluent Kafka Producer Configuration
        self.conf = {
            'bootstrap.servers': bootstrap_servers,
            'client.id': 'fraudshield-transaction-producer',
            'linger.ms': 5,
            'batch.num.messages': 1000,
            'compression.type': 'lz4'
        }
        
        try:
            self.producer = Producer(self.conf)
            logger.info("Kafka TransactionProducer successfully initialized targeting %s", bootstrap_servers)
        except Exception as e:
            logger.error("Failed to initialize Kafka Producer: %s", e)
            raise

    def _delivery_report(self, err, msg):
        """
        Callback triggered upon message delivery success or failure.
        """
        if err is not None:
            logger.error('Message delivery failed: %s', err)
            
    def generate_transaction(self) -> Dict[str, Any]:
        """
        Generates a synthetic transaction dictionary payload.

        Returns:
            Dict[str, Any]: The transaction payload.
        """
        transaction_id = str(uuid.uuid4())
        account_id = f"ACC_{random.randint(10000, 99999)}"
        device_id = f"DEV_{random.randint(1000, 9999)}"
        ip_address = f"192.168.{random.randint(0, 255)}.{random.randint(0, 255)}"
        
        return {
            "transaction_id": transaction_id,
            "account_id": account_id,
            "device_id": device_id,
            "ip_address": ip_address,
            "amount": round(random.uniform(1.00, 5000.00), 2),
            "currency": "USD",
            "transaction_time": datetime.now(timezone.utc).isoformat(),
            "merchant_id": f"MERCH_{random.randint(100, 999)}",
            "is_international": random.random() < 0.1,
            "is_online": random.random() < 0.8
        }

    def start_streaming(self, transactions_per_second: int = 100):
        """
        Starts the infinite loop streaming synthetic transactions to Kafka.

        Args:
            transactions_per_second (int): Target throughput rate.
        """
        logger.info("Starting transaction generation at %d TPS -> topic: %s", transactions_per_second, self.topic)
        
        sleep_interval = 1.0 / transactions_per_second
        
        try:
            while True:
                payload = self.generate_transaction()
                
                # Asynchronously produce the message
                self.producer.produce(
                    topic=self.topic,
                    key=payload["account_id"],
                    value=json.dumps(payload).encode('utf-8'),
                    callback=self._delivery_report
                )
                
                # Periodically trigger callbacks
                self.producer.poll(0)
                time.sleep(sleep_interval)
                
        except KeyboardInterrupt:
            logger.info("Streaming interrupted by user. Flushing producer buffer...")
        finally:
            self.producer.flush(10.0)
            logger.info("Producer shutdown complete.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    producer_app = TransactionProducer()
    producer_app.start_streaming(transactions_per_second=10)
