"""
FraudShield - Advanced Anomaly Detection Pipeline

This module executes model inference against testing sets, quantifies
predictive capabilities using scikit-learn metrics, and creates
graphical analysis summaries.

File: evaluation.py
Author: Mudit Bhargava
License: MIT
"""

import argparse
import logging
import sys
from pathlib import Path

from typing import Optional, Tuple

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

# Set up logging
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/fraudshield_evaluate.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class ModelEvaluation:
    def __init__(self, y_true: np.ndarray, y_pred: np.ndarray, y_prob: Optional[np.ndarray] = None) -> None:
        self.y_true = y_true
        self.y_pred = y_pred
        self.y_prob = y_prob

    def calculate_metrics(
        self,
    ) -> Tuple[float, float, float, float, Optional[float], Optional[float]]:
        accuracy = float(
            accuracy_score(self.y_true, self.y_pred)
        )
        precision = float(
            precision_score(self.y_true, self.y_pred, zero_division=0)
        )
        recall = float(
            recall_score(self.y_true, self.y_pred, zero_division=0)
        )
        f1 = float(
            f1_score(self.y_true, self.y_pred, zero_division=0)
        )
        auc = (
            float(roc_auc_score(self.y_true, self.y_prob))
            if self.y_prob is not None
            else None
        )
        ap = (
            float(average_precision_score(self.y_true, self.y_prob))
            if self.y_prob is not None
            else None
        )
        return accuracy, precision, recall, f1, auc, ap

    def plot_confusion_matrix(self, normalize: bool = False, save_path: Optional[str] = None) -> None:
        cm = confusion_matrix(self.y_true, self.y_pred)
        if normalize:
            row_sums = cm.sum(axis=1)[:, np.newaxis]
            cm = np.divide(
                cm.astype("float"), row_sums, out=np.zeros_like(cm, dtype=float), where=row_sums != 0
            )

        plt.figure(figsize=(8, 6))
        sns.heatmap(
            cm,
            annot=True,
            cmap="Blues",
            fmt=".2f" if normalize else "d",
            xticklabels=["Neg", "Pos"],
            yticklabels=["Neg", "Pos"],
        )
        plt.xlabel("Predicted Labels")
        plt.ylabel("True Labels")
        plt.title("Confusion Matrix")

        if save_path:
            path_obj = Path(save_path)
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(path_obj, dpi=300, bbox_inches="tight")
        else:
            plt.show()
        plt.close()

    def generate_report(self, output_path: Optional[str] = None) -> pd.DataFrame:
        accuracy, precision, recall, f1, auc, ap = self.calculate_metrics()

        report = pd.DataFrame(
            {
                "Metric": [
                    "Accuracy",
                    "Precision",
                    "Recall",
                    "F1 Score",
                    "ROC AUC",
                    "Average Precision",
                ],
                "Value": [accuracy, precision, recall, f1, auc, ap],
            }
        )

        if output_path:
            report.to_csv(output_path, index=False)
        else:
            print(report)

        return report


def _load_dataset(path: str) -> Tuple[np.ndarray, np.ndarray]:
    data = np.load(path, allow_pickle=False)

    if isinstance(data, np.lib.npyio.NpzFile):
        X = data["X"]
        y = data["y"]
    else:
        if data.ndim != 2 or data.shape[1] < 2:
            raise ValueError("Expected a 2D array with the target in the last column.")
        X = data[:, :-1]
        y = data[:, -1]

    if y.dtype.kind == "f" and set(np.unique(y)).issubset({0.0, 1.0}):
        y = y.astype(int)

    return X, y


def evaluate_and_save(
    model_path: str,
    test_data: str,
    output_path: str,
    confusion_matrix_path: str,
    normalize_cm: bool = False,
) -> ModelEvaluation:
    model = joblib.load(model_path)
    X_test, y_test = _load_dataset(test_data)
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else None

    evaluation = ModelEvaluation(y_test, y_pred, y_prob)
    evaluation.generate_report(output_path)
    evaluation.plot_confusion_matrix(normalize=normalize_cm, save_path=confusion_matrix_path)
    return evaluation


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate trained models")
    parser.add_argument(
        "--model_path", type=str, default="data/models/xgboost.pkl", help="Path to the trained model file"
    )
    parser.add_argument(
        "--test_data", type=str, default="data/models/test_data.npy", help="Path to the test data NumPy file"
    )
    parser.add_argument(
        "--output_path",
        type=str,
        default="data/models/evaluation_report.csv",
        help="Path to save the evaluation report",
    )
    parser.add_argument(
        "--confusion_matrix_path",
        type=str,
        default="data/plots/confusion_matrix.png",
        help="Path to save conf matrix",
    )
    parser.add_argument(
        "--normalize_cm",
        action="store_true",
        help="Normalize conf matrix values",
    )
    args = parser.parse_args()

    evaluate_and_save(
        model_path=args.model_path,
        test_data=args.test_data,
        output_path=args.output_path,
        confusion_matrix_path=args.confusion_matrix_path,
        normalize_cm=args.normalize_cm,
    )


if __name__ == "__main__":
    main()
