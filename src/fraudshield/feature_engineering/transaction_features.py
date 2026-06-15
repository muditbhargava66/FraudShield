"""
FraudShield - Advanced Anomaly Detection Pipeline

This module manages the extraction of complex statistical transaction
features based on shifting temporal windows and entity behavior tracking.

File: transaction_features.py
Author: Mudit Bhargava
License: MIT
"""

import logging
from dataclasses import dataclass, field
from typing import Iterable, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


DEFAULT_WINDOWS = ["1h", "24h", "7d", "30d"]


@dataclass
class TransactionFeatureConfig:
    time_column: str = "transaction_date"
    user_column: str = "user_id"
    merchant_column: str = "merchant_id"
    amount_column: str = "amount"
    currency_column: str = "currency"
    status_column: str = "status"
    target_column: str = "fraud"
    windows: List[str] = field(default_factory=lambda: list(DEFAULT_WINDOWS))


def parse_windows(windows: Optional[Iterable[str]]) -> List[str]:
    if windows is None:
        return list(DEFAULT_WINDOWS)
    if isinstance(windows, str):
        normalized = windows.strip().lower()
        if normalized in {"auto", "default"}:
            return list(DEFAULT_WINDOWS)
        if normalized in {"none", "off", ""}:
            return []
        windows_list = [w.strip() for w in windows.split(",") if w.strip()]
    else:
        windows_list = list(windows)
        if not windows_list:
            return []

    parsed: List[str] = []
    for window in windows_list:
        try:
            pd.to_timedelta(window)
        except Exception as exc:
            raise ValueError(f"Invalid window '{window}'. Use values like 1h, 24h, 7d.") from exc
        parsed.append(window)
    return parsed


def _ensure_datetime(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", utc=True)


def _rolling_group_agg(
    df: pd.DataFrame,
    group_col: str,
    value_col: str,
    window: str,
    agg: str,
    pos_col: str = "__pos__",
) -> np.ndarray:
    """Rolling window aggregation per group, returning values in DataFrame row order.

    Uses an integer position column to avoid duplicate-index alignment errors
    that occur when the DatetimeIndex has repeated timestamps.
    """
    result = np.empty(len(df), dtype=float)
    grouped = df.groupby(group_col)[[value_col, pos_col]]
    for _, group in grouped:
        rolled = group[value_col].rolling(window, closed="left").agg(agg)
        positions = group[pos_col].values.astype(int)
        result[positions] = rolled.values
    return result


def _compute_user_amount_zscore(
    df: pd.DataFrame,
    user_col: str,
    amount_col: str,
    pos_col: str = "__pos__",
) -> np.ndarray:
    """Per-user expanding z-score with shift(1) to prevent data leakage."""
    z = np.full(len(df), np.nan)
    grouped = df.groupby(user_col)[[amount_col, pos_col]]
    for _, group in grouped:
        amounts = group[amount_col]
        positions = group[pos_col].values.astype(int)
        mean = amounts.expanding().mean().shift(1)
        std = amounts.expanding().std(ddof=1).shift(1)
        valid = (std > 0) & std.notna()
        z[positions[valid.values]] = ((amounts.values - mean.values) / std.values)[valid.values]
    return z


def add_transaction_features(df: pd.DataFrame, config: TransactionFeatureConfig) -> pd.DataFrame:
    if config.time_column not in df.columns or config.amount_column not in df.columns:
        logger.info("Skipping transaction features: required columns missing.")
        return df

    work_df = df.copy()
    work_df[config.time_column] = _ensure_datetime(work_df[config.time_column])

    # Sort by time; track original positions for final reordering.
    sort_order = work_df[config.time_column].argsort().values
    inverse_sort = np.empty(len(sort_order), dtype=int)
    inverse_sort[sort_order] = np.arange(len(sort_order))

    work_df = work_df.iloc[sort_order].reset_index(drop=True)

    # Time-since-last-txn: compute on time-sorted data before setting DatetimeIndex
    if config.user_column in work_df.columns:
        _time_diffs = work_df.groupby(config.user_column)[config.time_column].diff()
        work_df["user_time_since_last_txn"] = _time_diffs.dt.total_seconds().values

    # Integer position column for mapping results back after groupby
    work_df["__pos__"] = np.arange(len(work_df))

    # Set DatetimeIndex for rolling windows
    work_df = work_df.set_index(config.time_column)

    windows = parse_windows(config.windows)

    if config.user_column in work_df.columns:
        work_df["user_amount_zscore"] = _compute_user_amount_zscore(
            work_df,
            config.user_column,
            config.amount_column,
        )
        for window in windows:
            work_df[f"user_txn_count_{window}"] = _rolling_group_agg(work_df, config.user_column, config.amount_column, window, "count")
            work_df[f"user_amount_sum_{window}"] = _rolling_group_agg(work_df, config.user_column, config.amount_column, window, "sum")
            work_df[f"user_amount_mean_{window}"] = _rolling_group_agg(work_df, config.user_column, config.amount_column, window, "mean")

    if config.merchant_column in work_df.columns:
        for window in windows:
            work_df[f"merchant_txn_count_{window}"] = _rolling_group_agg(work_df, config.merchant_column, config.amount_column, window, "count")
            work_df[f"merchant_amount_mean_{window}"] = _rolling_group_agg(work_df, config.merchant_column, config.amount_column, window, "mean")
            if config.target_column in work_df.columns:
                work_df[f"merchant_fraud_rate_{window}"] = _rolling_group_agg(work_df, config.merchant_column, config.target_column, window, "mean")

    if config.currency_column in work_df.columns:
        for window in windows:
            work_df[f"currency_txn_count_{window}"] = _rolling_group_agg(work_df, config.currency_column, config.amount_column, window, "count")

    if config.status_column in work_df.columns:
        for window in windows:
            work_df[f"status_txn_count_{window}"] = _rolling_group_agg(work_df, config.status_column, config.amount_column, window, "count")

    # Restore original row order and clean up helper columns
    work_df = work_df.reset_index()
    work_df = work_df.iloc[inverse_sort].reset_index(drop=True)
    if "__pos__" in work_df.columns:
        work_df = work_df.drop(columns=["__pos__"])

    # Fill NaNs generated by empty left-closed windows or missing previous transactions
    fill_cols = [c for c in work_df.columns if any(sub in c for sub in ["_count_", "_sum_", "_mean_", "_rate_", "zscore"])]
    if "user_time_since_last_txn" in work_df.columns:
        fill_cols.append("user_time_since_last_txn")
        
    if fill_cols:
        work_df[fill_cols] = work_df[fill_cols].fillna(0.0)

    return work_df
