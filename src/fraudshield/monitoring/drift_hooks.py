"""
Drift detection hooks for batch and streaming pipelines.

Provides:
- ``run_drift_check_with_metrics``: Wraps the existing KS-test drift logic
  from ``pipeline_tasks.py`` and emits Prometheus metrics.
- ``streaming_drift_monitor``: Lightweight periodic drift check for streaming
  feature distributions using mean/std comparison.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


def run_drift_check_with_metrics(
    train_data: str = "data/models/preprocessed_data.npy",
    test_data: str = "data/models/test_data.npy",
    metadata_path: str = "data/models/preprocessing_metadata.json",
    drift_threshold: float = 0.05,
    max_drift_ratio: float = 0.3,
    min_ks_statistic: float = 0.10,
    use_fdr: bool = True,
) -> Dict[str, Any]:
    """
    Run a KS-test drift check and emit Prometheus metrics.

    A feature counts as drifted only when its p-value (Benjamini-Hochberg
    adjusted when ``use_fdr`` is True) is below ``drift_threshold`` and its KS
    statistic reaches ``min_ks_statistic``. The effect-size floor matters
    because the KS test over-rejects at large sample sizes: a negligible mean
    shift becomes "significant" without being practically meaningful.

    Returns a summary dict with ``drift_ratio``, ``drifted_features``,
    ``total_features``, and ``drifted_feature_names``.
    """
    import json

    from scipy import stats

    from fraudshield.monitoring.metrics import get_metrics

    logger.info("Starting drift check with metrics emission")

    train_arr = np.load(train_data)
    test_arr = np.load(test_data)

    # Exclude the target column (last column)
    x_train = train_arr[:, :-1]
    x_test = test_arr[:, :-1]

    # Load feature names for reporting
    feature_names: Optional[List[str]] = None
    try:
        with open(metadata_path) as f:
            metadata = json.load(f)
            feature_names = metadata.get("feature_names")
    except Exception as exc:
        logger.warning("Could not load metadata for feature names: %s", exc)

    num_features = x_train.shape[1]
    drifted_names: List[str] = []

    p_values: List[float] = []
    statistics: List[float] = []
    for i in range(num_features):
        statistic, p_value = stats.ks_2samp(x_train[:, i], x_test[:, i])
        statistics.append(float(statistic))
        p_values.append(float(p_value))

    if use_fdr and p_values:
        adjusted = np.asarray(stats.false_discovery_control(p_values, method="bh"))
    else:
        adjusted = np.asarray(p_values)

    for i in range(num_features):
        feat_name = feature_names[i] if feature_names and i < len(feature_names) else f"feature_{i}"
        if adjusted[i] < drift_threshold and statistics[i] >= min_ks_statistic:
            logger.warning(
                "Drift detected in %s: p_value=%.4e (adjusted=%.4e), ks_statistic=%.4f",
                feat_name,
                p_values[i],
                adjusted[i],
                statistics[i],
            )
            drifted_names.append(feat_name)

    drifted_count = len(drifted_names)
    drift_ratio = drifted_count / num_features if num_features > 0 else 0.0

    logger.info(
        "Drift check completed: %d/%d (%.1f%%) features drifted.",
        drifted_count,
        num_features,
        drift_ratio * 100,
    )

    # Emit Prometheus metrics
    metrics = get_metrics()
    metrics.record_drift_check(
        drift_ratio_value=drift_ratio,
        drifted_feature_count=drifted_count,
        total_features=num_features,
    )

    if drift_ratio > max_drift_ratio:
        raise RuntimeError(f"Data drift threshold exceeded! {drift_ratio * 100:.1f}% > {max_drift_ratio * 100:.1f}% limit.")

    return {
        "drift_ratio": drift_ratio,
        "drifted_features": drifted_count,
        "total_features": num_features,
        "drifted_feature_names": drifted_names,
    }


def streaming_drift_monitor(
    feature_values: Dict[str, List[float]],
    baseline_stats: Dict[str, Dict[str, float]],
    z_threshold: float = 3.0,
) -> Dict[str, bool]:
    """
    Lightweight drift check for streaming features.

    Compares the mean of recent feature values against the baseline mean/std.
    Flags features where the z-score exceeds ``z_threshold``.

    Args:
        feature_values: Dict mapping feature name to list of recent values.
        baseline_stats: Dict mapping feature name to ``{"mean": ..., "std": ...}``.
        z_threshold: Number of standard deviations before flagging drift.

    Returns:
        Dict mapping feature name to ``True`` (drifted) or ``False`` (stable).
    """
    results: Dict[str, bool] = {}

    for feat_name, values in feature_values.items():
        baseline = baseline_stats.get(feat_name)
        if baseline is None or not values:
            results[feat_name] = False
            continue

        baseline_mean = baseline.get("mean", 0.0)
        baseline_std = baseline.get("std", 1.0)

        if baseline_std < 1e-10:
            # Avoid division by zero for constant features
            results[feat_name] = bool(abs(float(np.mean(values)) - baseline_mean) > 0.01)
            continue

        current_mean = float(np.mean(values))
        z_score = abs(current_mean - baseline_mean) / baseline_std
        drifted = z_score > z_threshold

        if drifted:
            logger.warning(
                "Streaming drift in %s: z_score=%.2f (threshold=%.2f)",
                feat_name,
                z_score,
                z_threshold,
            )

        results[feat_name] = drifted

    # Emit aggregate drift metric
    drifted_count = sum(1 for v in results.values() if v)
    total_count = len(results) if results else 1
    from fraudshield.monitoring.metrics import get_metrics

    metrics = get_metrics()
    metrics.record_drift_check(
        drift_ratio_value=drifted_count / total_count,
        drifted_feature_count=drifted_count,
        total_features=total_count,
    )

    return results
