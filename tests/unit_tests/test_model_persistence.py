# tests/unit_tests/test_model_persistence.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import os
import pytest
from src.model_persistence.model_persistence import save_model, load_model
from sklearn.ensemble import RandomForestClassifier

def test_save_and_load_model(tmpdir):
    # Create a sample model for testing
    model = RandomForestClassifier()

    # Save the model to a temporary file
    model_path = tmpdir.join('temp_model.pkl')
    save_model(model, model_path)

    # Assert that the model file exists
    assert os.path.exists(model_path)

    # Load the model from the file
    loaded_model = load_model(model_path)

    # Assert that the loaded model is of the expected type
    assert isinstance(loaded_model, RandomForestClassifier)

def test_load_nonexistent_model(tmpdir):
    # Specify a non-existent model file path
    model_path = tmpdir.join('nonexistent_model.pkl')

    # Call the load_model function with the non-existent file
    with pytest.raises(FileNotFoundError):
        load_model(model_path)