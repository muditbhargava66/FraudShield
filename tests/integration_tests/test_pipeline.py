# tests/integration_tests/test_pipeline.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import numpy as np
import pandas as pd
from src.data_ingestion.data_ingestion import DataIngestion
from src.data_preprocessing.data_preprocessing import preprocess_data
from src.model_training.train_models import train_random_forest, train_xgboost
from src.model_evaluation.evaluation import ModelEvaluation

def test_pipeline(tmpdir):
    # Create sample data for testing
    data = pd.DataFrame({
        'transaction_id': [1, 2, 3, 4, 5],
        'amount': [100, 200, 300, 400, 500],
        'currency': ['USD', 'EUR', 'USD', 'GBP', 'USD'],
        'fraud': [0, 0, 1, 0, 1]
    })

    # Save the sample data as a CSV file
    data_path = tmpdir.join('data.csv')
    data.to_csv(data_path, index=False)

    # Initialize DataIngestion with the temporary directory
    data_ingestion = DataIngestion(data_path=tmpdir)

    # Ingest the data
    ingested_data = data_ingestion.read_csv_file(data_path.basename)

    # Preprocess the data
    preprocessed_data = preprocess_data(ingested_data)

    # Split the preprocessed data into features and target
    X = preprocessed_data.drop('fraud', axis=1)
    y = preprocessed_data['fraud']

    # Train the Random Forest model
    rf_model = train_random_forest(X, y)

    # Train the XGBoost model
    xgb_model = train_xgboost(X, y)

    # Evaluate the trained models
    rf_evaluation = ModelEvaluation(y, rf_model.predict(X))
    xgb_evaluation = ModelEvaluation(y, xgb_model.predict(X))

    # Assert the evaluation metrics
    assert rf_evaluation.calculate_metrics()[0] > 0.7  # Accuracy
    assert xgb_evaluation.calculate_metrics()[0] > 0.7  # Accuracy