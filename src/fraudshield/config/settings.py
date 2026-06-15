"""
Central runtime configuration for FraudShield.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = PROJECT_ROOT / "src"
DATA_ROOT = PROJECT_ROOT / "data"
DEFAULT_SQLITE_PATH = DATA_ROOT / "processed" / "fraud_data.db"
DEFAULT_AIRFLOW_DB_PATH = PROJECT_ROOT / ".airflow" / "airflow.db"


def _getenv_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _getenv_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


@dataclass(frozen=True)
class DatabaseSettings:
    sqlalchemy_url: str

    @property
    def is_sqlite(self) -> bool:
        return self.sqlalchemy_url.startswith("sqlite")


@dataclass(frozen=True)
class AirflowSettings:
    home: Path
    dags_folder: Path
    base_log_folder: Path
    metadata_db_url: str
    executor: str
    load_examples: bool


@dataclass(frozen=True)
class KafkaSettings:
    bootstrap_servers: str
    topic: str
    group_id: str
    producer_client_id: str
    consumer_client_id: str
    poll_timeout_seconds: float


@dataclass(frozen=True)
class Neo4jSettings:
    uri: str
    username: str
    password: str
    verify_connectivity: bool


@dataclass(frozen=True)
class ModelArtifactSettings:
    model_dir: Path
    default_model_name: str
    preprocessor_path: Path
    metadata_path: Path

    def model_path(self, model_name: str | None = None) -> Path:
        name = (model_name or self.default_model_name).strip().lower()
        aliases = {"rf": "random_forest.pkl", "random_forest": "random_forest.pkl", "xgb": "xgboost.pkl", "xgboost": "xgboost.pkl"}
        file_name = aliases.get(name, name if name.endswith(".pkl") else f"{name}.pkl")
        return self.model_dir / file_name


@dataclass(frozen=True)
class RuntimeSettings:
    project_root: Path
    src_root: Path
    data_root: Path
    logging: "LoggingSettings"
    database: DatabaseSettings
    airflow: AirflowSettings
    kafka: KafkaSettings
    neo4j: Neo4jSettings
    models: ModelArtifactSettings

    @classmethod
    def from_env(cls) -> "RuntimeSettings":
        db_url = os.getenv("FRAUDSHIELD_DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")
        airflow_home = Path(os.getenv("AIRFLOW_HOME", PROJECT_ROOT / ".airflow"))
        airflow_db_url = os.getenv("AIRFLOW__DATABASE__SQL_ALCHEMY_CONN", f"sqlite:///{DEFAULT_AIRFLOW_DB_PATH}")
        default_executor = "SequentialExecutor" if airflow_db_url.startswith("sqlite") else "LocalExecutor"

        return cls(
            project_root=PROJECT_ROOT,
            src_root=SRC_ROOT,
            data_root=DATA_ROOT,
            logging=LoggingSettings(
                directory=Path(os.getenv("FRAUDSHIELD_LOG_DIR", PROJECT_ROOT / "logs")),
                level=os.getenv("FRAUDSHIELD_LOG_LEVEL", "INFO").upper(),
                enable_console=_getenv_bool("FRAUDSHIELD_LOG_ENABLE_CONSOLE", True),
                enable_file=_getenv_bool("FRAUDSHIELD_LOG_ENABLE_FILE", True),
                max_bytes=_getenv_int("FRAUDSHIELD_LOG_MAX_BYTES", 5_000_000),
                backup_count=_getenv_int("FRAUDSHIELD_LOG_BACKUP_COUNT", 5),
                format=os.getenv(
                    "FRAUDSHIELD_LOG_FORMAT",
                    "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                ),
            ),
            database=DatabaseSettings(sqlalchemy_url=db_url),
            airflow=AirflowSettings(
                home=airflow_home,
                dags_folder=Path(os.getenv("FRAUDSHIELD_AIRFLOW_DAGS_FOLDER", SRC_ROOT / "fraudshield" / "data_pipeline" / "airflow_dags")),
                base_log_folder=Path(os.getenv("FRAUDSHIELD_AIRFLOW_BASE_LOG_FOLDER", PROJECT_ROOT / "logs")),
                metadata_db_url=airflow_db_url,
                executor=os.getenv("FRAUDSHIELD_AIRFLOW_EXECUTOR", default_executor),
                load_examples=_getenv_bool("AIRFLOW__CORE__LOAD_EXAMPLES", False),
            ),
            kafka=KafkaSettings(
                bootstrap_servers=os.getenv("FRAUDSHIELD_KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
                topic=os.getenv("FRAUDSHIELD_KAFKA_TOPIC", "fraudshield-transactions"),
                group_id=os.getenv("FRAUDSHIELD_KAFKA_GROUP_ID", "fraudshield-ingestion-group"),
                producer_client_id=os.getenv("FRAUDSHIELD_KAFKA_PRODUCER_CLIENT_ID", "fraudshield-transaction-producer"),
                consumer_client_id=os.getenv("FRAUDSHIELD_KAFKA_CONSUMER_CLIENT_ID", "fraudshield-transaction-consumer"),
                poll_timeout_seconds=float(os.getenv("FRAUDSHIELD_KAFKA_POLL_TIMEOUT_SECONDS", "1.0")),
            ),
            neo4j=Neo4jSettings(
                uri=os.getenv("FRAUDSHIELD_NEO4J_URI", "neo4j://localhost:7687"),
                username=os.getenv("FRAUDSHIELD_NEO4J_USERNAME", "neo4j"),
                password=os.getenv("FRAUDSHIELD_NEO4J_PASSWORD", "fraudshield_secret_v3"),
                verify_connectivity=_getenv_bool("FRAUDSHIELD_NEO4J_VERIFY_CONNECTIVITY", True),
            ),
            models=ModelArtifactSettings(
                model_dir=Path(os.getenv("FRAUDSHIELD_MODEL_DIR", DATA_ROOT / "models")),
                default_model_name=os.getenv("FRAUDSHIELD_DEFAULT_MODEL", "xgboost"),
                preprocessor_path=Path(os.getenv("FRAUDSHIELD_PREPROCESSOR_PATH", DATA_ROOT / "models" / "preprocessor.joblib")),
                metadata_path=Path(os.getenv("FRAUDSHIELD_PREPROCESSING_METADATA_PATH", DATA_ROOT / "models" / "preprocessing_metadata.json")),
            ),
        )


@lru_cache(maxsize=1)
def get_settings() -> RuntimeSettings:
    return RuntimeSettings.from_env()


def configure_airflow_environment(settings: RuntimeSettings | None = None) -> RuntimeSettings:
    resolved = settings or get_settings()
    resolved.airflow.home.mkdir(parents=True, exist_ok=True)
    resolved.airflow.base_log_folder.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("AIRFLOW_HOME", str(resolved.airflow.home))
    os.environ.setdefault("AIRFLOW__DATABASE__SQL_ALCHEMY_CONN", resolved.airflow.metadata_db_url)
    os.environ.setdefault("AIRFLOW__CORE__LOAD_EXAMPLES", str(resolved.airflow.load_examples))
    os.environ.setdefault("AIRFLOW__CORE__EXECUTOR", resolved.airflow.executor)
    os.environ.setdefault("AIRFLOW__CORE__DAGS_FOLDER", str(resolved.airflow.dags_folder))
    os.environ.setdefault("AIRFLOW__LOGGING__BASE_LOG_FOLDER", str(resolved.airflow.base_log_folder))
    return resolved


@dataclass(frozen=True)
class LoggingSettings:
    directory: Path
    level: str
    enable_console: bool
    enable_file: bool
    max_bytes: int
    backup_count: int
    format: str
