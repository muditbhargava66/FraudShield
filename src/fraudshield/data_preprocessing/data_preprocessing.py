"""
FraudShield - Advanced Anomaly Detection Pipeline

This module implements the core data processing steps, leveraging
sklearn Pipelines for standard encoding and scaling, whilst routing
statistical data anomaly resolution to native C++ extensions.

File: data_preprocessing.py
Author: Mudit Bhargava
License: MIT
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
import scipy.sparse as sp
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from fraudshield.data_cleaning.cpp_wrapper import remove_missing_values, remove_outliers
from fraudshield.feature_engineering.transaction_features import (
    TransactionFeatureConfig,
    add_transaction_features,
    parse_windows,
)

# Set up logging
Path("logs").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/fraudshield_preprocess.log"), logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def _resolve_id_columns(
    id_columns: Optional[List[str]],
    user_column: str,
    merchant_column: str,
) -> List[str]:
    if id_columns is None:
        candidates = ["transaction_id", user_column, merchant_column]
    else:
        candidates = id_columns
    resolved: List[str] = []
    for col in candidates:
        if col and col not in resolved:
            resolved.append(col)
    return resolved


def _parse_id_columns_arg(value: str) -> Optional[List[str]]:
    normalized = value.strip().lower()
    if normalized in {"auto", "default"}:
        return None
    if normalized in {"none", "off", ""}:
        return []
    return [col.strip() for col in value.split(",") if col.strip()]


def _make_one_hot_encoder() -> OneHotEncoder:
    return OneHotEncoder(handle_unknown="ignore", sparse_output=True)


def _infer_feature_types(data: pd.DataFrame) -> Tuple[List[str], List[str]]:
    numeric_features = data.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical_features = [col for col in data.columns if col not in numeric_features]
    return numeric_features, categorical_features


def _build_preprocessor(numeric_features: List[str], categorical_features: List[str]) -> ColumnTransformer:
    numeric_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("scaler", StandardScaler(with_mean=False)),
        ]
    )

    categorical_transformer = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", _make_one_hot_encoder()),
        ]
    )

    transformers = []
    if numeric_features:
        transformers.append(("num", numeric_transformer, numeric_features))
    if categorical_features:
        transformers.append(("cat", categorical_transformer, categorical_features))

    if not transformers:
        raise ValueError("No usable feature columns found for preprocessing.")

    return ColumnTransformer(transformers=transformers, remainder="drop", sparse_threshold=0.3)


def _to_dense(matrix: Any) -> np.ndarray:
    if sp.issparse(matrix):
        return matrix.toarray()
    return np.asarray(matrix)


def preprocess_data(
    data: pd.DataFrame,
    target_column: str = "fraud",
    test_size: float = 0.2,
    random_state: int = 42,
    stratify: bool = True,
    drop_columns: Optional[List[str]] = None,
    time_column: str = "transaction_date",
    user_column: str = "user_id",
    merchant_column: str = "merchant_id",
    amount_column: str = "amount",
    currency_column: str = "currency",
    status_column: str = "status",
    feature_windows: Optional[List[str]] = None,
    id_columns: Optional[List[str]] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, ColumnTransformer, List[str]]:
    logger.info("Starting data preprocessing...")

    if not isinstance(data, pd.DataFrame):
        raise ValueError("Input data must be a pandas DataFrame")

    if target_column not in data.columns:
        raise ValueError(f"Target column '{target_column}' not found in input data.")

    feature_config = TransactionFeatureConfig(
        time_column=time_column,
        user_column=user_column,
        merchant_column=merchant_column,
        amount_column=amount_column,
        currency_column=currency_column,
        status_column=status_column,
        target_column=target_column,
        windows=parse_windows(feature_windows),
    )

    working_data = data.copy()
    use_time_split = time_column in working_data.columns and working_data[time_column].notna().any()
    if use_time_split:
        working_data = add_transaction_features(working_data, feature_config)

    drop_set = set(drop_columns or [])
    resolved_id_columns = _resolve_id_columns(id_columns, user_column, merchant_column)
    drop_set.update(resolved_id_columns)
    if use_time_split:
        drop_set.add(time_column)

    # Apply C++ data cleaning routines to numerical tracking columns
    if amount_column in working_data.columns:
        logger.info(f"Applying native C++ data cleaning routines for column: {amount_column}")

        amount_data = working_data[amount_column]
        cleaned_amount = remove_outliers(remove_missing_values(amount_data.to_numpy()), threshold=4.0)

        # In a generic ML pipeline, dropping independent rows changes the target mapping length.
        # We fill anomalies based on the clean C++ bounded array.
        median_val = float(np.median(cleaned_amount)) if len(cleaned_amount) > 0 else 0.0

        mean_val = amount_data.mean()
        std_val = amount_data.std()

        if std_val > 0:
            outlier_mask = np.abs((amount_data - mean_val) / std_val) > 4.0
            working_data.loc[outlier_mask, amount_column] = median_val

        working_data[amount_column] = working_data[amount_column].fillna(median_val)

    if use_time_split:
        logger.info("Using time-based split based on transaction date.")
        working_data = working_data.sort_values(time_column)
        split_index = max(1, int(len(working_data) * (1 - test_size)))
        train_df = working_data.iloc[:split_index]
        test_df = working_data.iloc[split_index:]

        y_train = train_df[target_column].to_numpy()
        y_test = test_df[target_column].to_numpy()
        X_train = train_df.drop(columns=[target_column, *drop_set], errors="ignore")
        X_test = test_df.drop(columns=[target_column, *drop_set], errors="ignore")
    else:
        # Avoid unnecessary copy when not using time split
        X = working_data.drop(columns=[target_column, *drop_set], errors="ignore")
        y = working_data[target_column]

        logger.info(f"Splitting data with test size: {test_size}...")
        stratify_target = y if stratify and y.nunique() > 1 else None
        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=test_size,
            random_state=random_state,
            stratify=stratify_target,
        )

    logger.info("Inferring numeric and categorical features...")
    numeric_features, categorical_features = _infer_feature_types(X_train)

    logger.info("Building preprocessing pipeline...")
    preprocessor = _build_preprocessor(numeric_features, categorical_features)

    logger.info("Fitting preprocessing pipeline on training data...")
    X_train_processed = preprocessor.fit_transform(X_train)
    X_test_processed = preprocessor.transform(X_test)

    try:
        feature_names = preprocessor.get_feature_names_out()
    except (AttributeError, Exception) as e:
        logger.warning(f"Could not get feature names from preprocessor: {e}. Using generic names.")
        feature_names = [f"feature_{i}" for i in range(X_train_processed.shape[1])]

    logger.info("Data preprocessing completed successfully!")
    return (
        np.asarray(X_train_processed),
        np.asarray(X_test_processed),
        np.asarray(y_train),
        np.asarray(y_test),
        preprocessor,
        list(feature_names),
    )


def _save_array_with_target(path: Path, X: np.ndarray, y: np.ndarray) -> None:
    X_dense = _to_dense(X)
    combined = np.column_stack([X_dense, y])
    path.parent.mkdir(parents=True, exist_ok=True)
    np.save(path, combined)


def preprocess_and_save(
    input_data: str,
    train_data: str,
    test_data: str,
    preprocessor_path: str,
    metadata_path: str,
    target_column: str = "fraud",
    test_size: float = 0.2,
    random_state: int = 42,
    stratify: bool = True,
    drop_columns: Optional[List[str]] = None,
    time_column: str = "transaction_date",
    user_column: str = "user_id",
    merchant_column: str = "merchant_id",
    amount_column: str = "amount",
    currency_column: str = "currency",
    status_column: str = "status",
    feature_windows: Optional[List[str]] = None,
    id_columns: Optional[List[str]] = None,
) -> None:
    logger.info(f"Reading input data from: {input_data}")
    ingested_data = pd.read_csv(input_data)

    use_time_split = bool(time_column in ingested_data.columns and ingested_data[time_column].notna().any())

    X_train, X_test, y_train, y_test, preprocessor, feature_names = preprocess_data(
        ingested_data,
        target_column=target_column,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify,
        drop_columns=drop_columns,
        time_column=time_column,
        user_column=user_column,
        merchant_column=merchant_column,
        amount_column=amount_column,
        currency_column=currency_column,
        status_column=status_column,
        feature_windows=feature_windows,
        id_columns=id_columns,
    )

    train_path = Path(train_data)
    test_path = Path(test_data)
    logger.info(f"Saving preprocessed train data to: {train_path}")
    _save_array_with_target(train_path, X_train, y_train)

    logger.info(f"Saving preprocessed test data to: {test_path}")
    _save_array_with_target(test_path, X_test, y_test)

    preprocessor_path_obj = Path(preprocessor_path)
    preprocessor_path_obj.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(preprocessor, preprocessor_path_obj)

    metadata_path_obj = Path(metadata_path)
    metadata_path_obj.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "target_column": target_column,
        "feature_names": list(feature_names),
        "drop_columns": drop_columns or [],
        "time_column": time_column,
        "time_based_split": use_time_split,
        "user_column": user_column,
        "merchant_column": merchant_column,
        "amount_column": amount_column,
        "currency_column": currency_column,
        "status_column": status_column,
        "feature_windows": parse_windows(feature_windows),
        "id_columns": _resolve_id_columns(id_columns, user_column, merchant_column),
    }
    metadata_path_obj.write_text(json.dumps(metadata, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Preprocess data for fraud detection")
    parser.add_argument(
        "--input_data", type=str, default="data/processed/ingested_data.csv", help="Path to the input data CSV file"
    )
    parser.add_argument(
        "--train_data",
        type=str,
        default="data/models/preprocessed_data.npy",
        help="Path to save the preprocessed train data as a NumPy file",
    )
    parser.add_argument(
        "--test_data",
        type=str,
        default="data/models/test_data.npy",
        help="Path to save the preprocessed test data as a NumPy file",
    )
    parser.add_argument(
        "--preprocessor_path",
        type=str,
        default="data/models/preprocessor.joblib",
        help="Path to save the fitted preprocessor",
    )
    parser.add_argument(
        "--metadata_path",
        type=str,
        default="data/models/preprocessing_metadata.json",
        help="Path to save preprocessing metadata",
    )
    parser.add_argument("--target_column", type=str, default="fraud", help="Name of the target column")
    parser.add_argument("--drop_columns", type=str, default="", help="Comma-separated list of columns to drop")
    parser.add_argument(
        "--time_column", type=str, default="transaction_date", help="Name of the transaction time column"
    )
    parser.add_argument("--user_column", type=str, default="user_id", help="Name of the user identifier column")
    parser.add_argument(
        "--merchant_column", type=str, default="merchant_id", help="Name of the merchant identifier column"
    )
    parser.add_argument("--amount_column", type=str, default="amount", help="Name of the transaction amount column")
    parser.add_argument("--currency_column", type=str, default="currency", help="Name of the currency column")
    parser.add_argument("--status_column", type=str, default="status", help="Name of the status column")
    parser.add_argument(
        "--feature_windows",
        type=str,
        default="auto",
        help='Comma-separated rolling windows (e.g., 1h,24h,7d,30d), or "auto"/"none"',
    )
    parser.add_argument(
        "--id_columns",
        type=str,
        default="auto",
        help='Identifier columns to drop: comma-separated list, or "auto"/"none"',
    )
    parser.add_argument("--test_size", type=float, default=0.2, help="Fraction of data to use for test set")
    parser.add_argument("--random_state", type=int, default=42, help="Random seed for data splitting")
    parser.add_argument("--no_stratify", action="store_true", help="Disable stratified splitting")
    args = parser.parse_args()

    drop_columns = [col.strip() for col in args.drop_columns.split(",") if col.strip()]
    id_columns = _parse_id_columns_arg(args.id_columns)

    preprocess_and_save(
        input_data=args.input_data,
        train_data=args.train_data,
        test_data=args.test_data,
        preprocessor_path=args.preprocessor_path,
        metadata_path=args.metadata_path,
        target_column=args.target_column,
        test_size=args.test_size,
        random_state=args.random_state,
        stratify=not args.no_stratify,
        drop_columns=drop_columns if drop_columns else None,
        time_column=args.time_column,
        user_column=args.user_column,
        merchant_column=args.merchant_column,
        amount_column=args.amount_column,
        currency_column=args.currency_column,
        status_column=args.status_column,
        feature_windows=args.feature_windows,
        id_columns=id_columns,
    )

    logger.info("Preprocessed data saved successfully!")


if __name__ == "__main__":
    main()
