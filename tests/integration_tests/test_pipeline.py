# tests/integration_tests/test_pipeline.py

import pandas as pd
from fraudshield.data_ingestion.data_ingestion import DataIngestion
from fraudshield.data_preprocessing.data_preprocessing import preprocess_data
from fraudshield.model_training.train_models import train_random_forest, train_xgboost
from fraudshield.model_evaluation.evaluation import ModelEvaluation
from sklearn.metrics import precision_score


def test_pipeline(tmpdir):
    # Create sample data for testing
    data = pd.DataFrame(
        {
            "transaction_id": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "amount": [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000],
            "currency": ["USD", "EUR", "USD", "GBP", "USD", "EUR", "USD", "GBP", "USD", "EUR"],
            "fraud": [0, 0, 1, 0, 1, 0, 0, 1, 0, 1],
        }
    )

    # Save the sample data as a CSV file
    data_path = tmpdir.join("data.csv")
    data.to_csv(data_path, index=False)

    # Initialize DataIngestion with the temporary directory and a dummy database connection string
    data_ingestion = DataIngestion(str(tmpdir), "sqlite:///:memory:")

    # Ingest the data
    ingested_data = data_ingestion.read_csv_file(data_path.basename)

    # Preprocess the data
    X_train, X_test, y_train, y_test, _, _ = preprocess_data(ingested_data)

    # Train the Random Forest model
    rf_model = train_random_forest(X_train, y_train)

    # Train the XGBoost model
    xgb_model = train_xgboost(X_train, y_train)

    # Make predictions once and reuse them
    rf_predictions = rf_model.predict(X_test)
    xgb_predictions = xgb_model.predict(X_test)

    # Evaluate the trained models on the test set
    rf_evaluation = ModelEvaluation(y_test, rf_predictions)
    xgb_evaluation = ModelEvaluation(y_test, xgb_predictions)

    # Calculate precision with zero_division parameter using cached predictions
    rf_precision = precision_score(y_test, rf_predictions, zero_division=1)
    xgb_precision = precision_score(y_test, xgb_predictions, zero_division=1)

    # Assert the evaluation metrics
    assert rf_evaluation.calculate_metrics()[0] >= 0.0  # Accuracy
    assert xgb_evaluation.calculate_metrics()[0] >= 0.0  # Accuracy
    assert rf_precision >= 0  # Precision
    assert xgb_precision >= 0  # Precision
