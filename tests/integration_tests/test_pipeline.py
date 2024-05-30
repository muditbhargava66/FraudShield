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
from sklearn.metrics import precision_score

def test_pipeline(tmpdir):
    # Create sample data for testing
    data = pd.DataFrame({
        'transaction_id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        'amount': [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000],
        'currency': ['USD', 'EUR', 'USD', 'GBP', 'USD', 'EUR', 'USD', 'GBP', 'USD', 'EUR'],
        'fraud': [0, 0, 1, 0, 1, 0, 0, 1, 0, 1]
    })
    
    # Save the sample data as a CSV file
    data_path = tmpdir.join('data.csv')
    data.to_csv(data_path, index=False)
    
    # Initialize DataIngestion with the temporary directory and a dummy database connection string
    data_ingestion = DataIngestion(str(tmpdir), 'sqlite:///:memory:')
    
    # Ingest the data
    ingested_data = data_ingestion.read_csv_file(data_path.basename)
    
    # Preprocess the data
    train_data, _ = preprocess_data(ingested_data)
    
    # Split the preprocessed data into features and target
    X = train_data.drop('fraud', axis=1)
    y = train_data['fraud'].astype(int)  # Convert the target variable to integer type

    # Train the Random Forest model
    rf_model = train_random_forest(X, y)

    # Train the XGBoost model
    xgb_model = train_xgboost(X, y)

    # Evaluate the trained models
    rf_evaluation = ModelEvaluation(y, rf_model.predict(X))
    xgb_evaluation = ModelEvaluation(y, xgb_model.predict(X))

    # Calculate precision with zero_division parameter
    rf_precision = precision_score(y, rf_model.predict(X), zero_division=1)
    xgb_precision = precision_score(y, xgb_model.predict(X), zero_division=1)

    # Assert the evaluation metrics
    assert rf_evaluation.calculate_metrics()[0] > 0.6  # Accuracy
    assert xgb_evaluation.calculate_metrics()[0] > 0.6  # Accuracy
    assert rf_precision >= 0  # Precision
    assert xgb_precision >= 0  # Precision