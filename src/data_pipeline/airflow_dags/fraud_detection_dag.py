# src/data_pipeline/airflow_dags/fraud_detection_dag.py

from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.contrib.operators.spark_submit_operator import SparkSubmitOperator
from airflow.contrib.operators.snowflake_operator import SnowflakeOperator
from airflow.models import Variable
from datetime import datetime, timedelta
from fraud_detection_pipeline import data_ingestion, data_preprocessing, model_training, model_evaluation, model_deployment

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2023, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'fraud_detection_pipeline',
    default_args=default_args,
    description='End-to-end fraud detection pipeline',
    schedule_interval=timedelta(days=1),
)

data_ingestion_task = PythonOperator(
    task_id='data_ingestion',
    python_callable=data_ingestion,
    op_kwargs={'database': Variable.get('database'), 'table': Variable.get('table')},
    dag=dag,
)

data_preprocessing_task = SparkSubmitOperator(
    task_id='data_preprocessing',
    application='data_preprocessing.py',
    conn_id='spark_default',
    dag=dag,
)

model_training_task = PythonOperator(
    task_id='model_training',
    python_callable=model_training,
    op_kwargs={'model_type': Variable.get('model_type'), 'hyperparameters': Variable.get('hyperparameters')},
    dag=dag,
)

model_evaluation_task = PythonOperator(
    task_id='model_evaluation',
    python_callable=model_evaluation,
    op_kwargs={'evaluation_metrics': Variable.get('evaluation_metrics')},
    dag=dag,
)

model_deployment_task = SnowflakeOperator(
    task_id='model_deployment',
    snowflake_conn_id='snowflake_default',
    sql='CALL deploy_fraud_detection_model()',
    dag=dag,
)

data_ingestion_task >> data_preprocessing_task >> model_training_task >> model_evaluation_task >> model_deployment_task
