"""Tests for the KS-test drift gate with FDR correction and effect-size floor."""

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from fraudshield.monitoring.drift_hooks import run_drift_check_with_metrics


def _write_split(tmp_path: Path, train: np.ndarray, test: np.ndarray) -> tuple[str, str]:
    train_path = tmp_path / "train.npy"
    test_path = tmp_path / "test.npy"
    # Append a constant target column, as the real preprocessed arrays have.
    np.save(train_path, np.column_stack([train, np.zeros(len(train))]))
    np.save(test_path, np.column_stack([test, np.zeros(len(test))]))
    return str(train_path), str(test_path)


def test_negligible_shift_below_effect_floor_does_not_trip_gate(tmp_path: Path) -> None:
    """A statistically detectable but practically negligible mean shift at large n
    must not be flagged: KS over-rejects at large samples without an effect-size floor."""
    rng = np.random.default_rng(0)
    train = rng.normal(0.0, 1.0, size=20000)
    test = rng.normal(0.1, 1.0, size=5000)  # KS stat ~0.04: p << 0.05 but below the 0.10 floor
    train_data, test_data = _write_split(tmp_path, train, test)

    report = run_drift_check_with_metrics(
        train_data=train_data,
        test_data=test_data,
        metadata_path=str(tmp_path / "missing.json"),
    )
    assert report["drifted_features"] == 0
    assert report["drift_ratio"] == 0.0


def test_genuine_shift_still_trips_gate(tmp_path: Path) -> None:
    """A large distributional shift must still raise so the DAG blocks retraining."""
    rng = np.random.default_rng(1)
    train = rng.normal(0.0, 1.0, size=4000)
    test = rng.normal(2.0, 1.0, size=1000)
    train_data, test_data = _write_split(tmp_path, train, test)

    with pytest.raises(RuntimeError, match="drift threshold exceeded"):
        run_drift_check_with_metrics(
            train_data=train_data,
            test_data=test_data,
            metadata_path=str(tmp_path / "missing.json"),
        )


def test_fdr_correction_reduces_false_discoveries(tmp_path: Path) -> None:
    """With use_fdr=True, Benjamini-Hochberg keeps only the p-values that survive
    multiple-testing correction: [0.001, 0.04, 0.6] at q=0.05 -> 1 discovery, not 2."""
    arrays = np.zeros((10, 4))  # 3 features + target column
    train_path = tmp_path / "train.npy"
    test_path = tmp_path / "test.npy"
    np.save(train_path, arrays)
    np.save(test_path, arrays)

    controlled = [(0.5, 0.001), (0.5, 0.04), (0.5, 0.6)]
    with patch("scipy.stats.ks_2samp", side_effect=controlled * 2):
        raw = run_drift_check_with_metrics(
            train_data=str(train_path),
            test_data=str(test_path),
            metadata_path=str(tmp_path / "missing.json"),
            max_drift_ratio=1.0,
            use_fdr=False,
        )
        corrected = run_drift_check_with_metrics(
            train_data=str(train_path),
            test_data=str(test_path),
            metadata_path=str(tmp_path / "missing.json"),
            max_drift_ratio=1.0,
            use_fdr=True,
        )

    assert raw["drifted_features"] == 2
    assert corrected["drifted_features"] == 1


def test_effect_floor_can_be_disabled(tmp_path: Path) -> None:
    """min_ks_statistic=0.0 restores the pure significance test."""
    rng = np.random.default_rng(2)
    train = rng.normal(0.0, 1.0, size=20000)
    test = rng.normal(0.1, 1.0, size=5000)
    train_data, test_data = _write_split(tmp_path, train, test)

    with pytest.raises(RuntimeError, match="drift threshold exceeded"):
        run_drift_check_with_metrics(
            train_data=train_data,
            test_data=test_data,
            metadata_path=str(tmp_path / "missing.json"),
            min_ks_statistic=0.0,
            use_fdr=False,
        )
