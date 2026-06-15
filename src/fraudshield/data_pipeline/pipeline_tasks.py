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
    """Verify inference artifacts are loadable and the API app can start."""
    from fraudshield.config.settings import get_settings
    from fraudshield.runtime.resources import load_inference_artifacts

    settings = get_settings()
    logger.info("Validating deployment artifacts at %s", settings.models.model_dir)
    artifacts = load_inference_artifacts(settings.models)
    logger.info(
        "Deployment validation passed: model loaded with %d input features",
        len(artifacts.input_feature_columns),
    )

def run_data_drift_check(
    train_data: str = "data/models/preprocessed_data.npy",
    test_data: str = "data/models/test_data.npy",
    metadata_path: str = "data/models/preprocessing_metadata.json",
    drift_threshold: float = 0.05,
    max_drift_ratio: float = 0.3,
) -> None:
    import json

    import numpy as np
    from scipy import stats

    logger.info("Starting data drift check")
    
    # Load arrays
    train_arr = np.load(train_data)
    test_arr = np.load(test_data)
    
    # Exclude the target column (last column)
    X_train = train_arr[:, :-1]
    X_test = test_arr[:, :-1]
    
    # Try to load feature names for better logging
    feature_names = None
    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
            feature_names = metadata.get("feature_names", None)
    except Exception as e:
        logger.warning("Could not load metadata for feature names: %s", e)
        
    num_features = X_train.shape[1]
    drifted_features = 0
    
    for i in range(num_features):
        feat_name = feature_names[i] if feature_names and i < len(feature_names) else f"feature_{i}"
        
        # KS-test
        stat, p_value = stats.ks_2samp(X_train[:, i], X_test[:, i])
        
        if p_value < drift_threshold:
            logger.warning("Drift detected in %s: KS stat=%.4f, p_value=%.4e", feat_name, stat, p_value)
            drifted_features += 1
            
    drift_ratio = drifted_features / num_features if num_features > 0 else 0
    logger.info("Data drift check completed: %d/%d (%.1f%%) features drifted.", drifted_features, num_features, drift_ratio * 100)
    
    if drift_ratio > max_drift_ratio:
        raise Exception(f"Data drift threshold exceeded! {drift_ratio*100:.1f}% > {max_drift_ratio*100:.1f}% limit.")
