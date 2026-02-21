"""
FraudShield - Advanced Anomaly Detection Pipeline

This module provides feature engineering utilities, transforming raw transaction
data into structured temporal, categorical, and behavioral indicators.

File: __init__.py
Author: Mudit Bhargava
License: MIT
"""

from fraudshield.feature_engineering.transaction_features import (
    TransactionFeatureConfig,
    add_transaction_features,
    parse_windows,
)

__all__ = [
    "TransactionFeatureConfig",
    "add_transaction_features",
    "parse_windows",
]
