# C++ Modules

FraudShield utilizes optimized C++ modules for efficient data cleaning and feature engineering. These modules are designed to handle large datasets and perform computationally intensive tasks with high performance.

## Data Cleaning Module

The data cleaning module is responsible for handling missing values, outliers, and inconsistencies in the raw transaction data. It performs the following tasks:

1. **Missing Value Handling**: 
   - The module identifies missing values (NaN) in the dataset
   - Removes NaN values using `std::remove_if` with `std::isnan`
   - Properly handles buffer sizes after removal to prevent overflow
   - Fills remaining positions with NaN after copying cleaned data

2. **Outlier Detection and Removal**: 
   - Detects outliers using Z-score method with configurable threshold
   - Uses **sample standard deviation** (n-1) instead of population standard deviation for statistical correctness
   - Formula: `std::sqrt(sq_sum / (data.size() - 1))`
   - Removes outliers beyond the threshold and fills remaining positions with NaN

3. **Data Normalization**: 
   - Normalizes numeric features to a common scale
   - Ensures fair comparison across features

**Safety and Correctness Improvements:**
- Proper bounds checking to prevent buffer overflows
- Explicit size tracking when data size changes after cleaning
- Sample standard deviation for unbiased statistical estimates
- Clear separation between cleaned data and padding with NaN

The data cleaning module is implemented using C++ to leverage its performance advantages and low-level control over memory management. The module utilizes efficient data structures and algorithms to minimize runtime and memory overhead.

## Feature Engineering Module

The feature engineering module is responsible for extracting relevant features from the cleaned transaction data. It performs the following tasks:

1. **Moving Average Calculation**:
   - Calculates sliding window averages over time series data
   - **Bounds checking**: Validates that `i + window_size - 1 < data.size()` before access
   - Prevents index out of bounds errors that could cause crashes
   - Uses efficient incremental sum updates

2. **Exponential Moving Average (EMA)**:
   - Calculates weighted moving averages with configurable alpha parameter
   - Validates alpha is between 0.0 and 1.0
   - Provides smooth trend indicators

3. **Relative Strength Index (RSI)**:
   - Calculates momentum indicator for price movements
   - **Edge case handling**: Requires window_size >= 2 (throws error for window_size=1)
   - Prevents creation of empty gain/loss vectors
   - Handles division by zero when average loss is 0

4. **Aggregation Features**: 
   - Calculates aggregated features across multiple records
   - Computes means, sums, and other statistics

**Safety and Correctness Improvements:**
- Comprehensive bounds checking on all array accesses
- Validation of window sizes and parameters before computation
- NULL pointer checks in C API functions
- Output buffer size validation before copying results
- Explicit handling of edge cases (window_size=1, empty data, etc.)
- Type-safe size_t usage for array indexing

The feature engineering module is implemented using C++ to ensure fast computation and efficient memory utilization. It leverages parallel processing techniques, such as OpenMP or Intel TBB, to accelerate feature extraction on multi-core systems.

## Integration and Usage

The C++ modules are integrated into the FraudShield pipeline through Python bindings. The Python code interacts with the C++ modules using a well-defined API, passing the necessary data and receiving the cleaned and engineered features in return.

To use the C++ modules in the FraudShield pipeline, follow these steps:

1. Compile the C++ modules using a compatible C++ compiler (e.g., GCC or Clang) with the required flags and optimizations.

2. Create Python bindings for the C++ modules using tools like pybind11 or Boost.Python to enable seamless interaction between Python and C++.

3. Import the Python bindings in the relevant scripts and call the appropriate functions to perform data cleaning and feature engineering.

4. Pass the cleaned and engineered features to the machine learning models for training and prediction.

The C++ modules in FraudShield are thoroughly tested using unit tests and integration tests to ensure their correctness and reliability. They are optimized for performance and can handle large-scale datasets efficiently.

By leveraging the power of C++ for data cleaning and feature engineering, FraudShield achieves significant performance improvements and enables faster processing of large volumes of transaction data.

## Architecture & Integration Details

```text
┌─────────────────────────────────────────────────────────┐
│                   Python Application                    │
├─────────────────────────────────────────────────────────┤
│              Python Wrapper Modules                     │
│  - cpp_wrapper.py (feature_engineering)                 │
│  - cpp_wrapper.py (data_cleaning)                       │
├─────────────────────────────────────────────────────────┤
│         pybind11 Bindings (if available)                │
│  - _feature_engineering_cpp.so                          │
│  - _data_cleaning_cpp.so                                │
├─────────────────────────────────────────────────────────┤
│              C++ Implementation                         │
│  - feature_engineering.cpp                              │
│  - data_cleaning.cpp                                    │
└─────────────────────────────────────────────────────────┘
```

The Python wrappers provide a unified interface that automatically uses C++ when available and gracefully defaults to Python execution:

### Fallback Mechanism

The integration includes an automatic fallback to pure Python:
1. **Import Time**: Attempts to import the newly built `_cpp.so` module.
2. **Runtime**: If compilation or environment loads fail, uses the pure Python implementation script.
3. **Logging**: Generates a standard pipeline warning on startup contexting the downgrade.

### Building C++ Modules Manually

Prerequisites:
1. **C++ Compiler**: GCC 7+ or Clang 5+ (Linux/macOS), MSVC 2017+ or MinGW (Windows).
2. **Python Dependencies**: `pip install pybind11 numpy scikit-build-core`

#### Recommended Workflow (`pyproject.toml`)
FraudShield uses `scikit-build-core` to securely build its C++ extensions through PEP 517 compliance.

```bash
# Install in development mode, triggering CMake and pybind11
uv pip install -e .
```

#### Legacy Makefile Target
```bash
# Triggers the underlying pip compilation sequence
make build-cpp

# Verifies integrations
make test-cpp
```

### Python Binding Code Simplifications
The internal bindings wrapped within `data_preprocessing.py` strictly adhere to `.agents/code-simplifier.md`. Rather than duplicating pandas DataFrames to track intermediate moving averages and distributions post-C++ execution, computations securely cast the resulting memory buffers directly into `np.median` and bounded standardization logics (`abs(val - mean) / std`) explicitly within memory.

### Performance Comparison

| Operation | Pure Python | C++ Module | Speedup |
|-----------|-------------|------------|---------|
| Moving Average (10K points) | ~15ms | ~2ms | 7.5x |
| Exponential MA (10K points) | ~20ms | ~3ms | 6.7x |
| RSI (10K points) | ~25ms | ~4ms | 6.3x |
| Remove Outliers (10K points) | ~10ms | ~1ms | 10.0x |

---