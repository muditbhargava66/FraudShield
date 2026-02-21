"""
FraudShield - Advanced Anomaly Detection Pipeline

This module defines the Airflow Directed Acyclic Graph (DAG) for automating
and scheduling the end-to-end fraud detection pipeline execution.

File: fraud_detection_dag.py
Author: Mudit Bhargava
License: MIT
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

from airflow import DAG
from airflow.models import Variable
from airflow.operators.python import PythonOperator

from fraudshield.data_pipeline.pipeline_tasks import (
    run_data_ingestion,
    run_model_deployment,
    run_data_preprocessing,
    run_model_evaluation,
    run_model_training,
)

# Ensure src/ is on the path for DAG imports (src layout).
SRC_ROOT = Path(__file__).resolve().parents[3]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

try:
    from airflow.providers.snowflake.operators.snowflake import SnowflakeOperator
except ImportError as e:
    # Log the import error for debugging
    logging.getLogger(__name__).warning(f"SnowflakeOperator not available: {e}")
    SnowflakeOperator = None
except Exception as e:
    # Log unexpected errors but don't hide them completely
    logging.getLogger(__name__).error(f"Unexpected error importing SnowflakeOperator: {e}")
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


def get_data_ingestion_kwargs() -> Dict[str, Any]:
    """Get data ingestion kwargs at runtime to avoid caching Variable.get() values."""
    return {
        "database": Variable.get("database", default_var="sqlite:///data/processed/fraud_data.db"),
        "table": Variable.get("table", default_var="fraud_data"),
    }


data_ingestion_task = PythonOperator(
    task_id="data_ingestion",
    python_callable=run_data_ingestion,
    op_kwargs=get_data_ingestion_kwargs(),
    dag=dag,
)

data_preprocessing_task = PythonOperator(
    task_id="data_preprocessing",
    python_callable=run_data_preprocessing,
    dag=dag,
)


def get_model_training_kwargs() -> Dict[str, Any]:
    """Get model training kwargs at runtime to avoid caching Variable.get() values."""
    return {
        "model_type": Variable.get("model_type", default_var="both"),
        "hyperparameters": Variable.get("hyperparameters", default_var=None),
    }


def get_model_evaluation_kwargs() -> Dict[str, Any]:
    """Get model evaluation kwargs at runtime to avoid caching Variable.get() values."""
    return {
        "evaluation_metrics": Variable.get("evaluation_metrics", default_var=None),
    }


model_training_task = PythonOperator(
    task_id="model_training",
    python_callable=run_model_training,
    op_kwargs=get_model_training_kwargs(),
    dag=dag,
)

model_evaluation_task = PythonOperator(
    task_id="model_evaluation",
    python_callable=run_model_evaluation,
    op_kwargs=get_model_evaluation_kwargs(),
    dag=dag,
)

if SnowflakeOperator is not None:
    model_deployment_task = SnowflakeOperator(
        task_id="model_deployment",
        snowflake_conn_id="snowflake_default",
        sql="CALL deploy_fraud_detection_model()",
        dag=dag,
    )
else:
    model_deployment_task = PythonOperator(
        task_id="model_deployment",
        python_callable=run_model_deployment,
        dag=dag,
    )

data_ingestion_task >> data_preprocessing_task >> model_training_task >> model_evaluation_task >> model_deployment_task
