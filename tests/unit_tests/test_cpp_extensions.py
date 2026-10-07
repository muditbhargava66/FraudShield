"""
Unit tests for the optional C++ extensions and their pure-Python fallbacks.

The compiled modules are an optimization, not a different behavior: every case
asserts the extension and the fallback agree, so results are identical whether
or not the C++ build is available.
"""

import numpy as np
import pytest

from fraudshield.data_cleaning import cpp_wrapper as data_cleaning
from fraudshield.feature_engineering import cpp_wrapper as feature_engineering

requires_cleaning_cpp = pytest.mark.skipif(not data_cleaning.is_cpp_available(), reason="C++ data cleaning extension is not built")
requires_feature_cpp = pytest.mark.skipif(not feature_engineering.is_cpp_available(), reason="C++ feature engineering extension is not built")


def _both_implementations(module, function_name, *args):
    """Run the same inputs through the compiled extension and the NumPy fallback."""
    extension = np.asarray(getattr(module, function_name)(*args))
    module.CPP_AVAILABLE = False
    try:
        fallback = np.asarray(getattr(module, function_name)(*args))
    finally:
        module.CPP_AVAILABLE = True
    return extension, fallback


def _reference_ema(data: np.ndarray, alpha: float) -> np.ndarray:
    out = np.empty(data.size, dtype=np.float64)
    if out.size:
        out[0] = data[0]
    for i in range(1, data.size):
        out[i] = alpha * data[i] + (1 - alpha) * out[i - 1]
    return out


class TestDataCleaningExtension:
    def test_remove_missing_values_drops_only_nan(self):
        data = np.array([1.0, np.nan, 3.0, np.nan, 5.0])
        extension, fallback = _both_implementations(data_cleaning, "remove_missing_values", data)

        expected = np.array([1.0, 3.0, 5.0])
        np.testing.assert_allclose(extension, expected)
        np.testing.assert_allclose(fallback, expected)

    def test_remove_missing_values_handles_empty_and_all_nan(self):
        for data in (np.array([]), np.array([np.nan, np.nan])):
            extension, fallback = _both_implementations(data_cleaning, "remove_missing_values", data)
            assert extension.size == 0
            assert fallback.size == 0

    @pytest.mark.parametrize("threshold", [1.5, 3.0, 4.0])
    def test_remove_outliers_matches_fallback(self, threshold):
        rng = np.random.default_rng(7)
        data = np.concatenate([rng.normal(100.0, 15.0, 500), [900.0, -800.0]])
        extension, fallback = _both_implementations(data_cleaning, "remove_outliers", data, threshold)

        assert extension.size == fallback.size
        np.testing.assert_allclose(extension, fallback, rtol=0, atol=1e-12)
        assert extension.size < data.size, "the two injected extremes must be removed"
        assert np.abs(extension).max() < 900.0

    def test_remove_outliers_drops_non_finite_values(self):
        data = np.array([1.0, np.nan, 2.0, np.inf, 3.0])
        extension, fallback = _both_implementations(data_cleaning, "remove_outliers", data, 3.0)

        np.testing.assert_allclose(extension, fallback, rtol=0, atol=1e-12)
        assert np.all(np.isfinite(extension))

    def test_remove_outliers_keeps_degenerate_input(self):
        for data in (np.array([]), np.array([7.0]), np.full(5, 3.0)):
            extension, fallback = _both_implementations(data_cleaning, "remove_outliers", data, 3.0)
            np.testing.assert_allclose(extension, fallback, rtol=0, atol=1e-12)
            assert extension.size == data.size


class TestFeatureEngineeringExtension:
    @pytest.mark.parametrize("window", [2, 3, 14, 50])
    def test_moving_average_matches_fallback_and_definition(self, window):
        rng = np.random.default_rng(11)
        data = rng.normal(50.0, 5.0, 300)
        extension, fallback = _both_implementations(feature_engineering, "calculate_moving_average", data, window)

        expected = np.convolve(data, np.ones(window) / window, mode="valid")
        assert extension.size == expected.size
        np.testing.assert_allclose(extension, expected, rtol=1e-12)
        np.testing.assert_allclose(fallback, expected, rtol=1e-12)

    @pytest.mark.parametrize("window", [0, -2])
    def test_moving_average_rejects_non_positive_window(self, window):
        with pytest.raises(ValueError):
            feature_engineering.calculate_moving_average(np.array([1.0, 2.0, 3.0]), window)

    def test_moving_average_returns_empty_when_window_exceeds_series(self):
        extension, fallback = _both_implementations(feature_engineering, "calculate_moving_average", np.array([1.0, 2.0]), 9)
        assert extension.size == 0
        assert fallback.size == 0

    @pytest.mark.parametrize("alpha", [0.1, 0.5, 1.0])
    def test_exponential_moving_average_matches_recursive_definition(self, alpha):
        rng = np.random.default_rng(3)
        data = rng.normal(0.0, 1.0, 200)
        extension, fallback = _both_implementations(feature_engineering, "calculate_exponential_moving_average", data, alpha)

        expected = _reference_ema(data, alpha)
        np.testing.assert_allclose(extension, expected, rtol=1e-12)
        np.testing.assert_allclose(fallback, expected, rtol=1e-12)

    def test_exponential_moving_average_handles_empty_input(self):
        """Regression: an empty series used to write ema[0] out of bounds and segfault the interpreter."""
        extension, fallback = _both_implementations(feature_engineering, "calculate_exponential_moving_average", np.array([]), 0.5)
        assert extension.size == 0
        assert fallback.size == 0

    @requires_feature_cpp
    def test_raw_extension_survives_empty_input(self):
        from fraudshield.feature_engineering import _feature_engineering_cpp

        assert np.asarray(_feature_engineering_cpp.calculate_exponential_moving_average(np.array([]), 0.5)).size == 0

    @pytest.mark.parametrize("alpha", [1.5, -0.1])
    def test_exponential_moving_average_rejects_alpha_out_of_range(self, alpha):
        with pytest.raises(ValueError):
            feature_engineering.calculate_exponential_moving_average(np.array([1.0, 2.0, 3.0]), alpha)

    @pytest.mark.parametrize("window", [2, 3, 14])
    def test_relative_strength_index_matches_fallback(self, window):
        rng = np.random.default_rng(5)
        data = np.cumsum(rng.normal(0.0, 1.0, 200)) + 100.0
        extension, fallback = _both_implementations(feature_engineering, "calculate_relative_strength_index", data, window)

        assert extension.size == data.size - window + 1
        np.testing.assert_allclose(extension, fallback, rtol=1e-9, atol=1e-9)
        assert np.all((extension >= 0.0) & (extension <= 100.0))

    def test_relative_strength_index_extremes(self):
        rising = np.arange(1.0, 30.0)
        falling = np.arange(30.0, 1.0, -1.0)

        np.testing.assert_allclose(feature_engineering.calculate_relative_strength_index(rising, 5), 100.0)
        np.testing.assert_allclose(feature_engineering.calculate_relative_strength_index(falling, 5), 0.0)

    def test_relative_strength_index_rejects_window_below_two(self):
        with pytest.raises(ValueError):
            feature_engineering.calculate_relative_strength_index(np.array([1.0, 2.0, 3.0]), 1)

    def test_relative_strength_index_rejects_window_exceeding_series(self):
        with pytest.raises(ValueError):
            feature_engineering.calculate_relative_strength_index(np.array([1.0, 2.0]), 9)
