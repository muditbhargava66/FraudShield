# tests/unit_tests/test_data_ingestion.py

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import os
import pandas as pd
import pytest
from src.data_ingestion.data_ingestion import DataIngestion

def test_read_csv_valid_file(tmpdir):
    # Create a temporary CSV file for testing
    data = {'column1': [1, 2, 3], 'column2': [4, 5, 6]}
    temp_file = tmpdir.join('temp_data.csv')
    pd.DataFrame(data).to_csv(temp_file, index=False)

    # Initialize DataIngestion with the temporary directory and a dummy database connection string
    data_ingestion = DataIngestion(str(tmpdir), 'sqlite:///:memory:')

    # Call the read_csv_file method
    result = data_ingestion.read_csv_file(temp_file.basename)

    # Assert that the ingested data is a DataFrame
    assert isinstance(result, pd.DataFrame)

    # Assert that the ingested data has the expected shape
    assert result.shape == (3, 2)

    # Assert that the ingested data has the expected column names
    assert list(result.columns) == ['column1', 'column2']

def test_read_csv_file_not_found():
    # Initialize DataIngestion with a non-existent directory and a dummy database connection string
    data_ingestion = DataIngestion('nonexistent_directory', 'sqlite:///:memory:')

    # Call the read_csv_file method with a non-existent file
    with pytest.raises(FileNotFoundError):
        data_ingestion.read_csv_file('nonexistent_file.csv')

def test_read_csv_empty_file(tmpdir):
    # Create an empty temporary CSV file for testing
    temp_file = tmpdir.join('empty_data.csv')
    pd.DataFrame().to_csv(temp_file, index=False)

    # Initialize DataIngestion with the temporary directory and a dummy database connection string
    data_ingestion = DataIngestion(str(tmpdir), 'sqlite:///:memory:')

    # Call the read_csv_file method with the empty file
    with pytest.raises(ValueError, match='Empty data file'):
        data_ingestion.read_csv_file(temp_file.basename)