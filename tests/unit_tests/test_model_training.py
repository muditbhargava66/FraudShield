"""Tests for train_and_save model selection, aliases, and validation."""

from pathlib import Path

import numpy as np
import pytest

from fraudshield.model_training.train_models import train_and_save


@pytest.fixture()
def dataset_paths(tmp_path: Path) -> tuple[str, str]:
    rng = np.random.default_rng(7)
    rows = 400
    features = rng.normal(size=(rows, 4))
    labels = (features[:, 0] + 0.5 * features[:, 1] > 0).astype(float)
    data = np.column_stack([features, labels])

    train_path = tmp_path / "preprocessed_data.npy"
    test_path = tmp_path / "test_data.npy"
    np.save(train_path, data[:320])
    np.save(test_path, data[320:])
    return str(train_path), str(test_path)


def _fast_hyperparameters() -> dict:
    return {"xgboost": {"n_estimators": 5}, "random_forest": {"n_estimators": 5}}


def test_unknown_model_name_raises(dataset_paths: tuple[str, str], tmp_path: Path) -> None:
    train_data, test_data = dataset_paths
    with pytest.raises(ValueError, match="Unknown model"):
        train_and_save(
            preprocessed_data=train_data,
            test_data=test_data,
            output_dir=str(tmp_path / "out"),
            model="lightgbm",
            hyperparameters=_fast_hyperparameters(),
        )


def test_xgboost_alias_trains_and_saves(dataset_paths: tuple[str, str], tmp_path: Path) -> None:
    train_data, test_data = dataset_paths
    output_dir = tmp_path / "out"
    metrics = train_and_save(
        preprocessed_data=train_data,
        test_data=test_data,
        output_dir=str(output_dir),
        model="xgboost",
        hyperparameters=_fast_hyperparameters(),
    )
    assert "xgboost" in metrics
    assert (output_dir / "xgboost.pkl").exists()
    assert not (output_dir / "random_forest.pkl").exists()
