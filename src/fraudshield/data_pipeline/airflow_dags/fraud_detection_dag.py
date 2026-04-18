"""
FraudShield Airflow DAG definition.
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Ensure src/ is on the path for DAG imports (src layout).
SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from fraudshield.config.settings import configure_airflow_environment  # noqa: E402

SETTINGS = configure_airflow_environment()

try:
    from airflow.providers.standard.operators.python import PythonOperator
    from airflow.sdk import DAG, Variable
except ImportError:  # pragma: no cover - Airflow 2 fallback
    from airflow.models import Variable
    from airflow.operators.python import PythonOperator

    from airflow import DAG

from fraudshield.data_pipeline.pipeline_tasks import (  # noqa: E402
    run_data_ingestion,
    run_data_preprocessing,
    run_model_deployment,
    run_model_evaluation,
    run_model_training,
)

try:
    from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
except ImportError as exc:  # pragma: no cover - optional provider
    logging.getLogger(__name__).warning("SnowflakeOperator not available: %s", exc)
    SnowflakeOperator = None
except Exception as exc:  # pragma: no cover - defensive logging
    logging.getLogger(__name__).error("Unexpected error importing SnowflakeOperator: %s", exc)
    SnowflakeOperator = None


default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(2023, 1, 1),
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    "fraud_detection_pipeline",
    default_args=default_args,
    description="End-to-end fraud detection pipeline",
    schedule=timedelta(days=1),
    catchup=False,
)


def _variable_get(key: str, default: str) -> Any:
    try:
        return Variable.get(key, default=default)
    except TypeError:  # pragma: no cover - Airflow 2 fallback
        return Variable.get(key, default_var=default)


def _data_ingestion_task() -> None:
    run_data_ingestion(
        database=_variable_get("database", SETTINGS.database.sqlalchemy_url),
        table=_variable_get("table", "fraud_data"),
        data_path=_variable_get("data_path", "data/raw"),
        input_file=_variable_get("input_file", "synthetic_fraud_data.csv"),
        output_file=_variable_get("output_file", "data/processed/ingested_data.csv"),
    )


def _data_preprocessing_task() -> None:
    run_data_preprocessing(
        input_data=_variable_get("input_data", "data/processed/ingested_data.csv"),
        train_data=_variable_get("train_data", "data/models/preprocessed_data.npy"),
        test_data=_variable_get("test_data", "data/models/test_data.npy"),
        preprocessor_path=_variable_get("preprocessor_path", str(SETTINGS.models.preprocessor_path)),
        metadata_path=_variable_get("metadata_path", str(SETTINGS.models.metadata_path)),
    )


def _model_training_task() -> None:
    run_model_training(
        preprocessed_data=_variable_get("train_data", "data/models/preprocessed_data.npy"),
        test_data=_variable_get("test_data", "data/models/test_data.npy"),
        output_dir=_variable_get("model_output_dir", str(SETTINGS.models.model_dir)),
        model=_variable_get("model_type", "both"),
        hyperparameters=_variable_get("hyperparameters", ""),
    )


def _model_evaluation_task() -> None:
    model_name = _variable_get("evaluation_model_name", SETTINGS.models.default_model_name)
    run_model_evaluation(
        model_path=str(SETTINGS.models.model_path(model_name)),
        test_data=_variable_get("test_data", "data/models/test_data.npy"),
        output_path=_variable_get("evaluation_output_path", "data/models/evaluation_report.csv"),
        confusion_matrix_path=_variable_get("confusion_matrix_path", "data/plots/confusion_matrix.png"),
        normalize_cm=_variable_get("normalize_confusion_matrix", "False").strip().lower() in {"1", "true", "yes", "on"},
    )


data_ingestion_task = PythonOperator(task_id="data_ingestion", python_callable=_data_ingestion_task, dag=dag)
data_preprocessing_task = PythonOperator(
    task_id="data_preprocessing",
    python_callable=_data_preprocessing_task,
    dag=dag,
)
model_training_task = PythonOperator(task_id="model_training", python_callable=_model_training_task, dag=dag)
model_evaluation_task = PythonOperator(task_id="model_evaluation", python_callable=_model_evaluation_task, dag=dag)

if SnowflakeOperator is not None:
    model_deployment_task = SnowflakeOperator(
        task_id="model_deployment",
        snowflake_conn_id="snowflake_default",
        sql="CALL deploy_fraud_detection_model()",
        dag=dag,
    )
else:
    model_deployment_task = PythonOperator(task_id="model_deployment", python_callable=run_model_deployment, dag=dag)

data_ingestion_task >> data_preprocessing_task >> model_training_task >> model_evaluation_task >> model_deployment_task
