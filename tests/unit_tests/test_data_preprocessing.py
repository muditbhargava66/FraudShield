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
        'numeric_feature': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        'categorical_feature': ['A', 'B', 'C', 'A', 'B', 'C', 'A', 'B', 'C', 'A'],
        'fraud': [0, 1, 0, 1, 0, 1, 0, 1, 0, 1]
    })
    
    # Call the preprocess_data function
    preprocessed_train_data, preprocessed_test_data = preprocess_data(data)
    
    # Assert that the preprocessed data is a DataFrame
    assert isinstance(preprocessed_train_data, pd.DataFrame)
    assert isinstance(preprocessed_test_data, pd.DataFrame)
    
    # Assert that the preprocessed data has the expected columns
    expected_columns = ['numeric_feature', 'categorical_feature_A', 'categorical_feature_B',
                        'categorical_feature_C', 'moving_average', 'exponential_moving_average', 'fraud']
    assert set(preprocessed_train_data.columns) == set(expected_columns)
    assert set(preprocessed_test_data.columns) == set(expected_columns)
    
    # Assert that the target variable is present in the preprocessed data
    assert 'fraud' in preprocessed_train_data.columns
    assert 'fraud' in preprocessed_test_data.columns