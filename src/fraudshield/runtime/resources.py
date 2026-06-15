"""
Factories and loaders for external runtime resources.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import joblib

try:
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import Engine
except ImportError:  # pragma: no cover - optional dependency
    create_engine = None  # type: ignore[assignment]
    text = None  # type: ignore[assignment]
    Engine = Any  # type: ignore[assignment,misc]

from fraudshield.config.settings import DatabaseSettings, KafkaSettings, ModelArtifactSettings, Neo4jSettings, get_settings
from fraudshield.model_training.model_persistence import load_model

try:
    from confluent_kafka import Consumer, Producer
except ImportError:  # pragma: no cover - optional dependency
    Consumer = None  # type: ignore[assignment,misc]
    Producer = None  # type: ignore[assignment,misc]

try:
    from neo4j import GraphDatabase
except ImportError:  # pragma: no cover - optional dependency
    GraphDatabase = None  # type: ignore[assignment,misc]


@dataclass
class InferenceArtifacts:
    model: Any
    preprocessor: Any
    metadata: dict[str, Any]
    input_feature_columns: list[str]
    transformed_feature_names: list[str]


def create_sqlalchemy_engine(database: DatabaseSettings | None = None) -> Engine:
    if create_engine is None:
        raise ImportError("sqlalchemy is required to use SQL storage integrations.")
    database = database or get_settings().database
    if database.is_sqlite:
        sqlite_path = Path(database.sqlalchemy_url.replace("sqlite:///", "", 1))
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    connect_args = {"check_same_thread": False} if database.is_sqlite else {}
    kwargs: dict[str, Any] = {"future": True}
    if connect_args:
        kwargs["connect_args"] = connect_args
    if not database.is_sqlite:
        kwargs["pool_pre_ping"] = True
    return create_engine(database.sqlalchemy_url, **kwargs)


def verify_sqlalchemy_engine(engine: Engine) -> None:
    if text is None:
        raise ImportError("sqlalchemy is required to use SQL storage integrations.")
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def create_kafka_producer(
    kafka: KafkaSettings | None = None,
    *,
    bootstrap_servers: str | None = None,
    client_id: str | None = None,
):
    if Producer is None:
        raise ImportError("confluent_kafka is required to use Kafka producer integrations.")
    kafka = kafka or get_settings().kafka
    return Producer(
        {
            "bootstrap.servers": bootstrap_servers or kafka.bootstrap_servers,
            "client.id": client_id or kafka.producer_client_id,
            "acks": "all",
            "linger.ms": 5,
            "batch.num.messages": 1000,
            "compression.type": "lz4",
            "enable.idempotence": True,
        }
    )


def create_kafka_consumer(
    kafka: KafkaSettings | None = None,
    *,
    bootstrap_servers: str | None = None,
    group_id: str | None = None,
):
    if Consumer is None:
        raise ImportError("confluent_kafka is required to use Kafka consumer integrations.")
    kafka = kafka or get_settings().kafka
    return Consumer(
        {
            "bootstrap.servers": bootstrap_servers or kafka.bootstrap_servers,
            "group.id": group_id or kafka.group_id,
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,
        }
    )


def create_neo4j_driver(neo4j: Neo4jSettings | None = None):
    if GraphDatabase is None:
        raise ImportError("neo4j is required to use graph integrations.")
    neo4j = neo4j or get_settings().neo4j
    driver = GraphDatabase.driver(neo4j.uri, auth=(neo4j.username, neo4j.password))
    if neo4j.verify_connectivity:
        driver.verify_connectivity()
    return driver


def load_inference_artifacts(model_settings: ModelArtifactSettings | None = None, model_name: Optional[str] = None) -> InferenceArtifacts:
    model_settings = model_settings or get_settings().models
    model_path = model_settings.model_path(model_name)
    preprocessor_path = model_settings.preprocessor_path
    metadata_path = model_settings.metadata_path

    if not preprocessor_path.exists():
        raise FileNotFoundError(f"Preprocessor file not found: {preprocessor_path}")
    if not metadata_path.exists():
        raise FileNotFoundError(f"Preprocessing metadata file not found: {metadata_path}")

    metadata = json.loads(metadata_path.read_text())
    preprocessor = joblib.load(preprocessor_path)
    input_feature_columns = list(metadata.get("input_feature_columns") or getattr(preprocessor, "feature_names_in_", []))
    transformed_feature_names = list(metadata.get("feature_names", []))

    return InferenceArtifacts(
        model=load_model(str(model_path)),
        preprocessor=preprocessor,
        metadata=metadata,
        input_feature_columns=input_feature_columns,
        transformed_feature_names=transformed_feature_names,
    )
