"""
FraudShield - Advanced Anomaly Detection Pipeline

This module drives the primary ML fitting routines, encompassing Random Forest
and XGBoost initializations, scaling pos-weights dynamically, and tracking
outcomes across time-series testing limits natively.

File: train_models.py
Author: Mudit Bhargava
License: MIT
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

# Set up logging
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/fraudshield_train.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def _load_dataset(path: str) -> Tuple[np.ndarray, np.ndarray]:
    data = np.load(path, allow_pickle=False)
    if isinstance(data, np.lib.npyio.NpzFile):
        X = data["X"]
        y = data["y"]
        return X, y
    array = data
    if array.ndim != 2 or array.shape[1] < 2:
        raise ValueError("Expected a 2D array with the target in the last column.")
    return array[:, :-1], array[:, -1]


def _compute_scale_pos_weight(y: np.ndarray) -> float:
    positives = np.sum(y == 1)
    negatives = np.sum(y == 0)
    if positives == 0 or negatives == 0:
        return 1.0
    return negatives / positives


def _maybe_encode_labels(y: np.ndarray, output_dir: Path) -> Tuple[np.ndarray, Optional[LabelEncoder]]:
    if y.dtype.kind in {"O", "U", "S"}:
        label_encoder = LabelEncoder()
        y_encoded = label_encoder.fit_transform(y)
        joblib.dump(label_encoder, output_dir / "label_encoder.joblib")
        return y_encoded, label_encoder
    if y.dtype.kind in {"f"}:
        unique_values = set(np.unique(y))
        if unique_values.issubset({0.0, 1.0}):
            return y.astype(int), None
    return y, None


def _parse_hyperparameters(hyperparameters: Union[str, Dict, None]) -> Dict[str, Any]:
    if not hyperparameters:
        return {}
    if isinstance(hyperparameters, dict):
        return hyperparameters
    if isinstance(hyperparameters, str):
        try:
            return json.loads(hyperparameters)
        except json.JSONDecodeError:
            logger.warning("Failed to parse hyperparameters JSON. Using defaults.")
            return {}
    return {}


def train_random_forest(
    X_train: np.ndarray, y_train: np.ndarray, random_state: int = 42, params: Optional[Dict[str, Any]] = None
) -> RandomForestClassifier:
    model_params = {
        "n_estimators": 300,
        "random_state": random_state,
        "n_jobs": -1,
        "class_weight": "balanced_subsample",
    }
    if params:
        model_params.update(params)
    rf_model = RandomForestClassifier(**model_params)
    rf_model.fit(X_train, y_train)
    return rf_model


def train_xgboost(
    X_train: np.ndarray, y_train: np.ndarray, random_state: int = 42, params: Optional[Dict[str, Any]] = None
) -> XGBClassifier:
    scale_pos_weight = _compute_scale_pos_weight(y_train)
    model_params = {
        "n_estimators": 300,
        "random_state": random_state,
        "n_jobs": -1,
        "eval_metric": "aucpr",
        "tree_method": "hist",
        "scale_pos_weight": scale_pos_weight,
    }
    if params:
        model_params.update(params)
    xgb_model = XGBClassifier(**model_params)
    xgb_model.fit(X_train, y_train)
    return xgb_model


def evaluate_model(model: Any, X_test: np.ndarray, y_test: np.ndarray) -> Dict[str, float]:
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else None

    metrics = {
        "accuracy": accuracy_score(y_test, y_pred),
        "precision": precision_score(y_test, y_pred, zero_division=0),
        "recall": recall_score(y_test, y_pred, zero_division=0),
        "f1_score": f1_score(y_test, y_pred, zero_division=0),
    }

    if y_prob is not None:
        metrics["roc_auc"] = roc_auc_score(y_test, y_prob)
        metrics["average_precision"] = average_precision_score(y_test, y_prob)
    return metrics


def save_model(model: Any, model_path: Path) -> None:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    logger.info(f"Model saved to: {model_path}")


def train_and_save(
    preprocessed_data: str,
    test_data: str,
    output_dir: str,
    model: str = "both",
    test_size: float = 0.2,
    random_state: int = 42,
    stratify: bool = True,
    hyperparameters: Union[str, Dict, None] = None,
) -> Dict[str, Dict[str, float]]:
    output_dir_path = Path(output_dir)
    output_dir_path.mkdir(parents=True, exist_ok=True)

    X_train, y_train = _load_dataset(preprocessed_data)
    y_train, label_encoder = _maybe_encode_labels(y_train, output_dir_path)

    if test_data and Path(test_data).exists():
        X_test, y_test = _load_dataset(test_data)
        # Apply label encoding if needed (check if y_test needs encoding)
        if label_encoder is not None:
            y_test = label_encoder.transform(y_test)
        elif y_test.dtype.kind in {"O", "U", "S"}:
            # Test data has string labels but no encoder was created (shouldn't happen)
            raise ValueError("Test data has string labels but no label encoder was created from training data")
    else:
        stratify_target = y_train if stratify and len(np.unique(y_train)) > 1 else None
        X_train, X_test, y_train, y_test = train_test_split(
            X_train,
            y_train,
            test_size=test_size,
            random_state=random_state,
            stratify=stratify_target,
        )

    metrics: Dict[str, Dict[str, float]] = {}
    parsed_hyperparameters = _parse_hyperparameters(hyperparameters)
    rf_params = parsed_hyperparameters.get("random_forest") or parsed_hyperparameters.get("rf")
    xgb_params = parsed_hyperparameters.get("xgboost") or parsed_hyperparameters.get("xgb")

    if model in {"rf", "both"}:
        rf_model = train_random_forest(X_train, y_train, random_state=random_state, params=rf_params)
        rf_metrics = evaluate_model(rf_model, X_test, y_test)
        metrics["random_forest"] = rf_metrics
        logger.info("Random Forest Metrics:")
        logger.info(rf_metrics)
        save_model(rf_model, output_dir_path / "random_forest.pkl")

    if model in {"xgb", "both"}:
        xgb_model = train_xgboost(X_train, y_train, random_state=random_state, params=xgb_params)
        xgb_metrics = evaluate_model(xgb_model, X_test, y_test)
        metrics["xgboost"] = xgb_metrics
        logger.info("XGBoost Metrics:")
        logger.info(xgb_metrics)
        save_model(xgb_model, output_dir_path / "xgboost.pkl")

    metrics_path = output_dir_path / "training_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2))
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Train fraud detection models")
    parser.add_argument(
        "--preprocessed_data",
        type=str,
        default="data/models/preprocessed_data.npy",
        help="Path to the preprocessed training data NumPy file",
    )
    parser.add_argument(
        "--test_data",
        type=str,
        default="data/models/test_data.npy",
        help="Optional path to the preprocessed test data NumPy file",
    )
    parser.add_argument("--output_dir", type=str, default="data/models", help="Directory to save the trained models")
    parser.add_argument("--model", type=str, default="both", choices=["rf", "xgb", "both"], help="Which model to train")
    parser.add_argument("--hyperparameters", type=str, default="", help="Optional JSON string of model hyperparameters")
    parser.add_argument(
        "--test_size", type=float, default=0.2, help="Test size for splitting if no test_data is provided"
    )
    parser.add_argument("--random_state", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument(
        "--no_stratify", action="store_true", help="Disable stratified splitting when creating a validation set"
    )
    args = parser.parse_args()

    try:
        train_and_save(
            preprocessed_data=args.preprocessed_data,
            test_data=args.test_data,
            output_dir=args.output_dir,
            model=args.model,
            test_size=args.test_size,
            random_state=args.random_state,
            stratify=not args.no_stratify,
            hyperparameters=args.hyperparameters,
        )

    except FileNotFoundError as e:
        logger.error(f"Preprocessed data file not found: {str(e)}")
    except Exception as e:
        logger.error(f"Error during model training: {str(e)}")


if __name__ == "__main__":
    main()
