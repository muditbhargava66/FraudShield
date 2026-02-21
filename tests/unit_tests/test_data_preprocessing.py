# tests/unit_tests/test_data_preprocessing.py

import pandas as pd
from fraudshield.data_preprocessing.data_preprocessing import preprocess_data


def test_preprocess_data():
    # Create a sample DataFrame for testing
    data = pd.DataFrame(
        {
            "numeric_feature": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
            "categorical_feature": ["A", "B", "C", "A", "B", "C", "A", "B", "C", "A"],
            "fraud": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
        }
    )

    # Call the preprocess_data function
    X_train, X_test, y_train, y_test, preprocessor, feature_names = preprocess_data(data)

    # Assert output shapes and lengths
    assert X_train.shape[0] + X_test.shape[0] == len(data)
    assert len(y_train) + len(y_test) == len(data)

    # Feature names should match number of columns in transformed data
    assert len(feature_names) == X_train.shape[1]
    assert preprocessor is not None

    # Ensure target values are preserved
    assert set(y_train).issubset({0, 1})
    assert set(y_test).issubset({0, 1})
