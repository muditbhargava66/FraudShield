"""
Task wrappers used by the FraudShield Airflow DAG.
"""

import logging
from typing import Any

from fraudshield.config.settings import get_settings
from fraudshield.data_ingestion.data_ingestion import DataIngestion
from fraudshield.data_preprocessing.data_preprocessing import preprocess_and_save
from fraudshield.model_evaluation.evaluation import evaluate_and_save
from fraudshield.model_training.train_models import train_and_save

logger = logging.getLogger(__name__)


def run_data_ingestion(
    database: str | None = None,
    table: str = "fraud_data",
    data_path: str = "data/raw",
    input_file: str = "synthetic_fraud_data.csv",
    output_file: str = "data/processed/ingested_data.csv",
) -> None:
    logger.info("Starting data ingestion task")
    ingestion = DataIngestion(data_path, database or get_settings().database.sqlalchemy_url)
    try:
        ingestion.run_ingestion_pipeline(input_file, table)
        ingestion.save_ingested_data(input_file, output_file)
        logger.info("Data ingestion task completed")
    finally:
        ingestion.close()


def run_data_preprocessing(
    input_data: str = "data/processed/ingested_data.csv",
    train_data: str = "data/models/preprocessed_data.npy",
    test_data: str = "data/models/test_data.npy",
    preprocessor_path: str = "data/models/preprocessor.joblib",
    metadata_path: str = "data/models/preprocessing_metadata.json",
    **kwargs: Any,
) -> None:
    logger.info("Starting data preprocessing task")
    preprocess_and_save(
        input_data=input_data,
        train_data=train_data,
        test_data=test_data,
        preprocessor_path=preprocessor_path,
        metadata_path=metadata_path,
        **kwargs,
    )
    logger.info("Data preprocessing task completed")


def run_model_training(
    preprocessed_data: str = "data/models/preprocessed_data.npy",
    test_data: str = "data/models/test_data.npy",
    output_dir: str = "data/models",
    model: str = "both",
    **kwargs: Any,
) -> None:
    logger.info("Starting model training task")
    train_and_save(
        preprocessed_data=preprocessed_data,
        test_data=test_data,
        output_dir=output_dir,
        model=model,
        **kwargs,
    )
    logger.info("Model training task completed")


def run_model_evaluation(
    model_path: str = "data/models/xgboost.pkl",
    test_data: str = "data/models/test_data.npy",
    output_path: str = "data/models/evaluation_report.csv",
    confusion_matrix_path: str = "data/plots/confusion_matrix.png",
    normalize_cm: bool = False,
) -> None:
    logger.info("Starting model evaluation task")
    evaluate_and_save(
        model_path=model_path,
        test_data=test_data,
        output_path=output_path,
        confusion_matrix_path=confusion_matrix_path,
        normalize_cm=normalize_cm,
    )
    logger.info("Model evaluation task completed")


def run_model_deployment() -> None:
    logger.info("Model deployment task placeholder - implement deployment integration here")
