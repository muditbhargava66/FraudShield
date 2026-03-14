"""
Module exposing the real-time Kafka streaming implementations for FraudShield.
"""

from .transaction_producer import TransactionProducer
from .kafka_consumer import TransactionConsumer

__all__ = ["TransactionProducer", "TransactionConsumer"]
