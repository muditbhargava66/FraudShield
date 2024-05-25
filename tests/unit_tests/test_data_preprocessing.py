# tests/unit_tests/test_data_preprocessing.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import numpy as np
import pandas as pd
from src.data_preprocessing.data_preprocessing import preprocess_data

def test_preprocess_data():
    # Create a sample DataFrame for testing
    data = pd.DataFrame({
        'numeric_feature': [1, 2, 3, 4, 5],
        'categorical_feature': ['A', 'B', 'C', 'A', 'B'],
        'target': [0, 1, 0, 1, 0]
    })

    # Call the preprocess_data function
    preprocessed_data = preprocess_data(data)

    # Assert that the preprocessed data is a DataFrame
    assert isinstance(preprocessed_data, pd.DataFrame)

    # Assert that the preprocessed data has the expected shape
    assert preprocessed_data.shape == (5, 12)

    # Assert that the numeric feature is scaled
    numeric_columns = preprocessed_data.columns[preprocessed_data.columns.str.startswith('numeric_feature')]
    assert np.allclose(preprocessed_data[numeric_columns].mean(), 0, atol=1e-6)
    assert np.allclose(preprocessed_data[numeric_columns].std(), 1, atol=1e-6)

    # Assert that the categorical feature is one-hot encoded
    assert set(preprocessed_data.columns) == {
        'numeric_feature', 'categorical_feature_A', 'categorical_feature_B', 'categorical_feature_C',
        'moving_average', 'exponential_moving_average', 'target'
    }