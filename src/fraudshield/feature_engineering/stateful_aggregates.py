"""
Stateful streaming feature calculations backed by deque-based windows.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Deque, Dict, Iterable, Optional

import pandas as pd

from fraudshield.feature_engineering.transaction_features import parse_windows


def _to_timestamp(value: Any) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


@dataclass
class WindowStats:
    window_seconds: float
    events: Deque[tuple[float, float, Optional[int]]] = field(default_factory=deque)
    amount_sum: float = 0.0
    labeled_count: int = 0
    fraud_sum: float = 0.0

    def _prune(self, timestamp_seconds: float) -> None:
        while self.events and (timestamp_seconds - self.events[0][0]) > self.window_seconds:
            _, amount, known_fraud = self.events.popleft()
            self.amount_sum -= amount
            if known_fraud is not None:
                self.labeled_count -= 1
                self.fraud_sum -= float(known_fraud)

    def snapshot(self, timestamp_seconds: float) -> dict[str, float]:
        self._prune(timestamp_seconds)
        count = len(self.events)
        mean = self.amount_sum / count if count else 0.0
        fraud_rate = self.fraud_sum / self.labeled_count if self.labeled_count else 0.0
        return {"count": float(count), "sum": self.amount_sum, "mean": mean, "fraud_rate": fraud_rate}

    def record(self, timestamp_seconds: float, amount: float, known_fraud: Optional[int]) -> None:
        self._prune(timestamp_seconds)
        self.events.append((timestamp_seconds, amount, known_fraud))
        self.amount_sum += amount
        if known_fraud is not None:
            self.labeled_count += 1
            self.fraud_sum += float(known_fraud)


@dataclass
class RunningStats:
    count: int = 0
    mean: float = 0.0
    m2: float = 0.0
    last_timestamp: Optional[pd.Timestamp] = None

    def describe(self, amount: float, timestamp: pd.Timestamp) -> dict[str, float]:
        delta = None
        if self.last_timestamp is not None:
            delta = (timestamp - self.last_timestamp).total_seconds()
        if self.count < 2:
            zscore = 0.0
        else:
            variance = self.m2 / (self.count - 1)
            std = variance**0.5
            zscore = (amount - self.mean) / std if std > 0 else 0.0
        return {
            "time_since_last_txn": float(delta) if delta is not None else 0.0,
            "amount_zscore": float(zscore),
        }

    def record(self, amount: float, timestamp: pd.Timestamp) -> None:
        self.last_timestamp = timestamp
        self.count += 1
        delta = amount - self.mean
        self.mean += delta / self.count
        delta2 = amount - self.mean
        self.m2 += delta * delta2


class StatefulFeatureStore:
    """
    Computes rolling transaction features in O(1) amortized time per event.
    """

    def __init__(self, windows: Optional[Iterable[str]] = None) -> None:
        self.windows = parse_windows(windows)
        self.window_seconds = {window: pd.to_timedelta(window).total_seconds() for window in self.windows}
        self.user_windows: Dict[str, Dict[str, WindowStats]] = defaultdict(self._window_map)
        self.merchant_windows: Dict[str, Dict[str, WindowStats]] = defaultdict(self._window_map)
        self.currency_windows: Dict[str, Dict[str, WindowStats]] = defaultdict(self._window_map)
        self.status_windows: Dict[str, Dict[str, WindowStats]] = defaultdict(self._window_map)
        self.user_stats: Dict[str, RunningStats] = defaultdict(RunningStats)

    def _window_map(self) -> Dict[str, WindowStats]:
        return {window: WindowStats(seconds) for window, seconds in self.window_seconds.items()}

    def build_features(self, payload: Dict[str, Any]) -> Dict[str, float]:
        timestamp = _to_timestamp(payload.get("transaction_date") or payload.get("transaction_time") or pd.Timestamp.utcnow())
        timestamp_seconds = timestamp.timestamp()
        amount = float(payload.get("amount", 0.0) or 0.0)
        known_fraud = payload.get("fraud")
        if known_fraud is None:
            known_fraud = payload.get("known_fraud")
        if known_fraud is not None:
            known_fraud = int(known_fraud)

        features: Dict[str, float] = {}
        user_id = payload.get("user_id") or payload.get("account_id")
        merchant_id = payload.get("merchant_id")
        currency = payload.get("currency")
        status = payload.get("status")

        if user_id:
            running = self.user_stats[user_id]
            description = running.describe(amount, timestamp)
            features["user_time_since_last_txn"] = description["time_since_last_txn"]
            features["user_amount_zscore"] = description["amount_zscore"]

        for window in self.windows:
            if user_id:
                snapshot = self.user_windows[user_id][window].snapshot(timestamp_seconds)
                features[f"user_txn_count_{window}"] = snapshot["count"]
                features[f"user_amount_sum_{window}"] = snapshot["sum"]
                features[f"user_amount_mean_{window}"] = snapshot["mean"]
            if merchant_id:
                snapshot = self.merchant_windows[merchant_id][window].snapshot(timestamp_seconds)
                features[f"merchant_txn_count_{window}"] = snapshot["count"]
                features[f"merchant_amount_mean_{window}"] = snapshot["mean"]
                features[f"merchant_fraud_rate_{window}"] = snapshot["fraud_rate"]
            if currency:
                snapshot = self.currency_windows[currency][window].snapshot(timestamp_seconds)
                features[f"currency_txn_count_{window}"] = snapshot["count"]
            if status:
                snapshot = self.status_windows[status][window].snapshot(timestamp_seconds)
                features[f"status_txn_count_{window}"] = snapshot["count"]

        self.record(payload, timestamp=timestamp, amount=amount, known_fraud=known_fraud)
        return features

    def record(
        self,
        payload: Dict[str, Any],
        *,
        timestamp: Optional[pd.Timestamp] = None,
        amount: Optional[float] = None,
        known_fraud: Optional[int] = None,
    ) -> None:
        timestamp = timestamp or _to_timestamp(payload.get("transaction_date") or payload.get("transaction_time") or pd.Timestamp.utcnow())
        timestamp_seconds = timestamp.timestamp()
        amount = float(amount if amount is not None else payload.get("amount", 0.0) or 0.0)
        user_id = payload.get("user_id") or payload.get("account_id")
        merchant_id = payload.get("merchant_id")
        currency = payload.get("currency")
        status = payload.get("status")

        if user_id:
            self.user_stats[user_id].record(amount, timestamp)
            for window in self.windows:
                self.user_windows[user_id][window].record(timestamp_seconds, amount, known_fraud)
        if merchant_id:
            for window in self.windows:
                self.merchant_windows[merchant_id][window].record(timestamp_seconds, amount, known_fraud)
        if currency:
            for window in self.windows:
                self.currency_windows[currency][window].record(timestamp_seconds, amount, known_fraud)
        if status:
            for window in self.windows:
                self.status_windows[status][window].record(timestamp_seconds, amount, known_fraud)
