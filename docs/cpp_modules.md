# C++ Modules

FraudShield includes optional C++ modules for data cleaning and feature engineering, built via `scikit-build-core` + `pybind11`.

## Data Cleaning Module

Handles missing values, outliers, and normalization:

1. **Missing Value Handling**: Removes NaN via `std::remove_if`, pads remaining slots with NaN
2. **Outlier Detection**: Z-score method with configurable threshold, uses sample std (`n-1`)
3. **Data Normalization**: Scales numeric features to common range

Safety features:
- Bounds checking on all array accesses
- Explicit size tracking after data removal
- NULL pointer validation on C API entry points

## Feature Engineering Module

Computes time-series indicators:

1. **Moving Average**: Sliding window with bounds checking (`i + window_size - 1 < data.size()`)
2. **Exponential Moving Average (EMA)**: Configurable alpha, validated `[0.0, 1.0]`
3. **RSI** (experimental): Momentum indicator, requires `window_size >= 2`, handles division by zero
4. **Aggregation Features**: Means, sums, and statistics across records

Safety features:
- Comprehensive bounds checking
- Window size validation before computation
- Output buffer size validation

## Architecture

```text
┌─────────────────────────────────────────────┐
│              Python Application             │
├─────────────────────────────────────────────┤
│           Python Wrapper Modules            │
│  cpp_wrapper.py (feature_engineering)       │
│  cpp_wrapper.py (data_cleaning)             │
├─────────────────────────────────────────────┤
│        pybind11 Bindings (if available)     │
│  _feature_engineering_cpp.so                │
│  _data_cleaning_cpp.so                      │
├─────────────────────────────────────────────┤
│           C++ Implementation                │
│  feature_engineering.cpp                    │
│  data_cleaning.cpp                          │
└─────────────────────────────────────────────┘
```

## Fallback Mechanism

1. **Import time**: Attempts to load `_cpp.so` module
2. **Runtime**: Falls back to pure Python if compilation failed
3. **Logging**: Emits warning on fallback

## Building

```bash
# Recommended: editable install triggers CMake + pybind11
uv pip install -e .

# Verify
uv run python -c "from fraudshield.feature_engineering import cpp_wrapper; print(cpp_wrapper.is_cpp_available())"
```

### Prerequisites

- C++ compiler: GCC 7+ or Clang 5+ (Linux/macOS), MSVC 2017+ (Windows)
- Python: `pybind11`, `numpy`, `scikit-build-core`

## Performance

| Operation | Pure Python | C++ Module | Speedup |
|-----------|-------------|------------|---------|
| Moving Average (10K) | ~15ms | ~2ms | ~7x |
| EMA (10K) | ~20ms | ~3ms | ~6x |
| RSI (10K) | ~25ms | ~4ms | ~6x |
| Remove Outliers (10K) | ~10ms | ~1ms | ~10x |

C++ is optional. Python fallbacks are fully functional and tested.

---
