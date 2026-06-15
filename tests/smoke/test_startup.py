import json

import joblib
import numpy as np
import pandas as pd
import pytest
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from fraudshield.config.settings import get_settings
from fraudshield.runtime.resources import load_inference_artifacts


def test_api_app_import():
    pytest.importorskip("fastapi")

    from fraudshield.ml.inference.api import create_app

    app = create_app()
    assert app.title == "FraudShield Inference API"


def test_airflow_dag_import():
    pytest.importorskip("airflow")

    from fraudshield.data_pipeline.airflow_dags import fraud_detection_dag

    assert fraud_detection_dag.dag.dag_id == "fraud_detection_pipeline"


def test_load_inference_artifacts(tmp_path, monkeypatch):
    train_df = pd.DataFrame(
        {
            "amount": [10.0, 20.0, 30.0, 40.0],
            "currency": ["USD", "EUR", "USD", "EUR"],
        }
    )
    y = np.array([0, 1, 0, 1])

    preprocessor = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                        ("scaler", StandardScaler()),
                    ]
                ),
                ["amount"],
            ),
            (
                "cat",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("onehot", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                ["currency"],
            ),
        ]
    )
    transformed = preprocessor.fit_transform(train_df)
    model = LogisticRegression().fit(transformed, y)

    model_dir = tmp_path / "models"
    model_dir.mkdir()
    model_path = model_dir / "xgboost.pkl"
    preprocessor_path = model_dir / "preprocessor.joblib"
    metadata_path = model_dir / "preprocessing_metadata.json"

    joblib.dump(model, model_path)
    joblib.dump(preprocessor, preprocessor_path)
    metadata_path.write_text(
        json.dumps(
            {
                "input_feature_columns": ["amount", "currency"],
                "feature_names": ["num__amount", "cat__currency_EUR", "cat__currency_USD"],
                "feature_windows": [],
            }
        )
    )

    monkeypatch.setenv("FRAUDSHIELD_MODEL_DIR", str(model_dir))
    monkeypatch.setenv("FRAUDSHIELD_PREPROCESSOR_PATH", str(preprocessor_path))
    monkeypatch.setenv("FRAUDSHIELD_PREPROCESSING_METADATA_PATH", str(metadata_path))
    get_settings.cache_clear()

    artifacts = load_inference_artifacts()

    assert artifacts.input_feature_columns == ["amount", "currency"]
    assert artifacts.transformed_feature_names[0] == "num__amount"
