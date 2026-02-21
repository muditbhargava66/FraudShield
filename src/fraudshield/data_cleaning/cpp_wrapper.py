"""
FraudShield - Advanced Anomaly Detection Pipeline

This module provides Python bindings for the C++ data cleaning module.
It seamlessly falls back to pure Python if the compiled extensions are
missing or incompatible.

File: cpp_wrapper.py
Author: Mudit Bhargava
License: MIT
"""
import logging

import numpy as np

logger = logging.getLogger(__name__)

# Try to import C++ module
try:
    from fraudshield.data_cleaning import _data_cleaning_cpp

    CPP_AVAILABLE = True
    logger.info("C++ data cleaning module loaded successfully")
except ImportError as e:
    CPP_AVAILABLE = False
    logger.warning(f"C++ data cleaning module not available: {e}. Using Python fallback.")


def remove_missing_values(data: np.ndarray) -> np.ndarray:
    """
    Remove missing (NaN) values from array.

    Args:
        data: Input numpy array

    Returns:
        Array with NaN values removed
    """
    if CPP_AVAILABLE:
        try:
            return _data_cleaning_cpp.remove_missing_values(data.astype(np.float64))
        except Exception as e:
            logger.warning(f"C++ function failed: {e}. Using Python fallback.")

    # Python fallback
    return data[~np.isnan(data)]


def remove_outliers(data: np.ndarray, threshold: float = 3.0) -> np.ndarray:
    """
    Remove outliers using z-score threshold.

    Args:
        data: Input numpy array
        threshold: Z-score threshold for outlier detection (default: 3.0)

    Returns:
        Array with outliers removed
    """
    if CPP_AVAILABLE:
        try:
            return _data_cleaning_cpp.remove_outliers(data.astype(np.float64), threshold)
        except Exception as e:
            logger.warning(f"C++ function failed: {e}. Using Python fallback.")

    # Python fallback
    if len(data) == 0:
        return data

    mean = np.mean(data)
    std = np.std(data, ddof=1)

    if std == 0:
        return data

    z_scores = np.abs((data - mean) / std)
    return data[z_scores <= threshold]


def is_cpp_available() -> bool:
    """Check if C++ module is available"""
    return CPP_AVAILABLE
