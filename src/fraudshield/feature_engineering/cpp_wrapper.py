"""
FraudShield - Advanced Anomaly Detection Pipeline

This module provides Python bindings for the C++ feature engineering module.
It computes complex rolling indicators (Moving Average, EMA, RSI) natively
and safely falls back to pure Python if C++ acceleration is unavailable.

File: cpp_wrapper.py
Author: Mudit Bhargava
License: MIT
"""
import logging

import numpy as np

logger = logging.getLogger(__name__)

# Try to import C++ module
try:
    from fraudshield.feature_engineering import _feature_engineering_cpp

    CPP_AVAILABLE = True
    logger.info("C++ feature engineering module loaded successfully")
except ImportError as e:
    CPP_AVAILABLE = False
    logger.warning(f"C++ feature engineering module not available: {e}. Using Python fallback.")


def calculate_moving_average(data: np.ndarray, window_size: int) -> np.ndarray:
    """
    Calculate moving average with specified window size.

    Args:
        data: Input numpy array
        window_size: Size of the moving window

    Returns:
        Array of moving averages
    """
    if CPP_AVAILABLE:
        try:
            return _feature_engineering_cpp.calculate_moving_average(data.astype(np.float64), window_size)
        except Exception as e:
            logger.warning(f"C++ function failed: {e}. Using Python fallback.")

    # Python fallback using pandas
    import pandas as pd

    return pd.Series(data).rolling(window=window_size).mean().values[window_size - 1:]


def calculate_exponential_moving_average(data: np.ndarray, alpha: float) -> np.ndarray:
    """
    Calculate exponential moving average with alpha parameter.

    Args:
        data: Input numpy array
        alpha: Smoothing factor (0 < alpha <= 1)

    Returns:
        Array of exponential moving averages
    """
    if CPP_AVAILABLE:
        try:
            return _feature_engineering_cpp.calculate_exponential_moving_average(data.astype(np.float64), alpha)
        except Exception as e:
            logger.warning(f"C++ function failed: {e}. Using Python fallback.")

    # Python fallback
    ema = np.zeros_like(data)
    ema[0] = data[0]
    for i in range(1, len(data)):
        ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]
    return ema


def calculate_relative_strength_index(data: np.ndarray, window_size: int) -> np.ndarray:
    """
    Calculate Relative Strength Index (RSI) with specified window size.

    Args:
        data: Input numpy array
        window_size: Size of the window for RSI calculation

    Returns:
        Array of RSI values
    """
    if CPP_AVAILABLE:
        try:
            return _feature_engineering_cpp.calculate_relative_strength_index(data.astype(np.float64), window_size)
        except Exception as e:
            logger.warning(f"C++ function failed: {e}. Using Python fallback.")

    # Python fallback
    if window_size < 2:
        raise ValueError("Window size must be at least 2 for RSI calculation")

    deltas = np.diff(data)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[: window_size - 1])
    avg_loss = np.mean(losses[: window_size - 1])

    rsi = np.zeros(len(data) - window_size + 1)
    rs = avg_gain / avg_loss if avg_loss != 0 else np.inf
    rsi[0] = 100 - (100 / (1 + rs))

    for i in range(window_size, len(data)):
        gain = gains[i - 1] if i - 1 < len(gains) else 0
        loss = losses[i - 1] if i - 1 < len(losses) else 0

        avg_gain = (avg_gain * (window_size - 1) + gain) / window_size
        avg_loss = (avg_loss * (window_size - 1) + loss) / window_size

        rs = avg_gain / avg_loss if avg_loss != 0 else np.inf
        rsi[i - window_size + 1] = 100 - (100 / (1 + rs))

    return rsi


def is_cpp_available() -> bool:
    """Check if C++ module is available"""
    return CPP_AVAILABLE
