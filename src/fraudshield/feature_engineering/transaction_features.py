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


def _rolling_group_agg(df: pd.DataFrame, group_col: str, value_col: str, window: str, agg: str) -> pd.Series:
    grouped = df.groupby(group_col)[value_col]
    rolled = grouped.rolling(window, closed="left").agg(agg)
    return rolled.reset_index(level=0, drop=True)


def _compute_user_amount_zscore(df: pd.DataFrame, user_col: str, amount_col: str) -> pd.Series:
    grouped = df.groupby(user_col)[amount_col]
    # Use shift(1) to exclude current row from expanding window calculation
    mean = grouped.expanding().mean().groupby(level=0).shift(1)
    std = grouped.expanding().std(ddof=1).groupby(level=0).shift(1)
    mean = mean.reset_index(level=0, drop=True)
    std = std.reset_index(level=0, drop=True)
    # Handle division by zero - replace with NaN when std is 0 or NaN
    z = pd.Series(index=df.index, dtype=float)
    valid_mask = (std > 0) & std.notna()
    z[valid_mask] = (df.loc[valid_mask, amount_col] - mean[valid_mask]) / std[valid_mask]
    z[~valid_mask] = np.nan
    return z


def add_transaction_features(df: pd.DataFrame, config: TransactionFeatureConfig) -> pd.DataFrame:
    if config.time_column not in df.columns or config.amount_column not in df.columns:
        logger.info("Skipping transaction features: required columns missing.")
        return df

    work_df = df.copy()
    work_df[config.time_column] = _ensure_datetime(work_df[config.time_column])

    work_df["__orig_index__"] = np.arange(len(work_df))
    work_df = work_df.sort_values(config.time_column)
    work_df = work_df.set_index(config.time_column)

    windows = parse_windows(config.windows)

    if config.user_column in work_df.columns:
        work_df["user_time_since_last_txn"] = (
            work_df.groupby(config.user_column)
            .apply(lambda group: group.index.to_series().diff().dt.total_seconds())
            .reset_index(level=0, drop=True)
        )
        work_df["user_amount_zscore"] = _compute_user_amount_zscore(
            work_df,
            config.user_column,
            config.amount_column,
        )
        for window in windows:
            work_df[f"user_txn_count_{window}"] = _rolling_group_agg(
                work_df, config.user_column, config.amount_column, window, "count"
            )
            work_df[f"user_amount_sum_{window}"] = _rolling_group_agg(
                work_df, config.user_column, config.amount_column, window, "sum"
            )
            work_df[f"user_amount_mean_{window}"] = _rolling_group_agg(
                work_df, config.user_column, config.amount_column, window, "mean"
            )

    if config.merchant_column in work_df.columns:
        for window in windows:
            work_df[f"merchant_txn_count_{window}"] = _rolling_group_agg(
                work_df, config.merchant_column, config.amount_column, window, "count"
            )
            work_df[f"merchant_amount_mean_{window}"] = _rolling_group_agg(
                work_df, config.merchant_column, config.amount_column, window, "mean"
            )
            if config.target_column in work_df.columns:
                work_df[f"merchant_fraud_rate_{window}"] = _rolling_group_agg(
                    work_df, config.merchant_column, config.target_column, window, "mean"
                )

    if config.currency_column in work_df.columns:
        for window in windows:
            work_df[f"currency_txn_count_{window}"] = _rolling_group_agg(
                work_df, config.currency_column, config.amount_column, window, "count"
            )

    if config.status_column in work_df.columns:
        for window in windows:
            work_df[f"status_txn_count_{window}"] = _rolling_group_agg(
                work_df, config.status_column, config.amount_column, window, "count"
            )

    work_df = work_df.reset_index()
    work_df = work_df.sort_values("__orig_index__")
    work_df = work_df.drop(columns=["__orig_index__"])
    return work_df
