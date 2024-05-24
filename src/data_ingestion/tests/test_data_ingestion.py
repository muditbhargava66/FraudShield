# src/data_ingestion/tests/test_data_ingestion.py

import unittest
from unittest.mock import patch, MagicMock
import pandas as pd
from sqlalchemy import create_engine
from src.data_ingestion.data_ingestion import DataIngestion

class TestDataIngestion(unittest.TestCase):
    def setUp(self):
        self.data_ingestion = DataIngestion("test_data_path", "sqlite:///:memory:")

    @patch("pandas.read_csv")
    def test_read_csv_file(self, mock_read_csv):
        mock_read_csv.return_value = pd.DataFrame({"A": [1, 2]})
        file_name = "file1.csv"
        result = self.data_ingestion.read_csv_file(file_name)
        expected_dataframe = pd.DataFrame({"A": [1, 2]})
        pd.testing.assert_frame_equal(result, expected_dataframe)
        mock_read_csv.assert_called_once_with("test_data_path/file1.csv")

    @patch("sqlalchemy.Table")
    @patch("sqlalchemy.MetaData")
    @patch("sqlalchemy.create_engine")
    def test_write_to_database(self, mock_create_engine, mock_metadata, mock_table):
        dataframe = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        table_name = "test_table"

        mock_engine_instance = mock_create_engine.return_value
        mock_metadata_instance = mock_metadata.return_value
        mock_table_instance = mock_table.return_value

        mock_metadata_instance.tables = {}
        mock_metadata_instance.reflect.return_value = None
        mock_table_instance.delete.return_value = MagicMock()

        connection = mock_engine_instance.connect.return_value.__enter__.return_value
        connection.execute = MagicMock()

        self.data_ingestion.write_to_database(dataframe, table_name)

        mock_metadata_instance.create_all.assert_called_once_with(mock_engine_instance)
        connection.execute.assert_called()
        pd.testing.assert_frame_equal(dataframe, dataframe)

    @patch.object(DataIngestion, "read_csv_file")
    @patch.object(DataIngestion, "write_to_database")
    def test_run_ingestion_pipeline(self, mock_write_to_database, mock_read_csv_file):
        file_name = "file1.csv"
        table_name = "test_table"
        mock_dataframe = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        mock_read_csv_file.return_value = mock_dataframe
        self.data_ingestion.run_ingestion_pipeline(file_name, table_name)
        mock_read_csv_file.assert_called_once_with(file_name)
        mock_write_to_database.assert_called_once_with(mock_dataframe, table_name)

    @patch("pandas.DataFrame.to_csv")
    @patch.object(DataIngestion, "read_csv_file")
    def test_save_ingested_data(self, mock_read_csv_file, mock_to_csv):
        file_name = "file1.csv"
        output_file = "output.csv"
        mock_dataframe = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        mock_read_csv_file.return_value = mock_dataframe
        self.data_ingestion.save_ingested_data(file_name, output_file)
        mock_read_csv_file.assert_called_once_with(file_name)
        mock_to_csv.assert_called_once_with(output_file, index=False)


if __name__ == "__main__":
    unittest.main()
