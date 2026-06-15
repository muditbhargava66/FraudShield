"""
Module exposing the real-time Kafka streaming implementations for FraudShield.
"""

__all__ = ["TransactionProducer", "TransactionConsumer"]


def __getattr__(name: str):
    if name == "TransactionProducer":
        from fraudshield.streaming.transaction_producer import TransactionProducer

        return TransactionProducer
    if name == "TransactionConsumer":
        from fraudshield.streaming.kafka_consumer import TransactionConsumer

        return TransactionConsumer
    raise AttributeError(name)
