# src/data_ingestion/tests/test_data_ingestion.py

import unittest
from unittest.mock import patch
import pandas as pd
from data_ingestion import DataIngestion

class TestDataIngestion(unittest.TestCase):
    def setUp(self):
        self.data_ingestion = DataIngestion("test_data_path", "test_db_connection_string")

    @patch("pandas.read_csv")
    def test_read_csv_files(self, mock_read_csv):
        mock_read_csv.side_effect = [pd.DataFrame({"A": [1, 2]}), pd.DataFrame({"B": [3, 4]})]
        file_names = ["file1.csv", "file2.csv"]
        result = self.data_ingestion.read_csv_files(file_names)
        expected_dataframe = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        pd.testing.assert_frame_equal(result, expected_dataframe)

    @patch("pandas.DataFrame.to_sql")
    def test_write_to_database(self, mock_to_sql):
        dataframe = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        table_name = "test_table"
        self.data_ingestion.write_to_database(dataframe, table_name)
        mock_to_sql.assert_called_once_with(table_name, self.data_ingestion.engine, if_exists='replace', index=False)

    @patch.object(DataIngestion, "read_csv_files")
    @patch.object(DataIngestion, "write_to_database")
    def test_run_ingestion_pipeline(self, mock_write_to_database, mock_read_csv_files):
        file_names = ["file1.csv", "file2.csv"]
        table_name = "test_table"
        mock_dataframe = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
        mock_read_csv_files.return_value = mock_dataframe
        self.data_ingestion.run_ingestion_pipeline(file_names, table_name)
        mock_read_csv_files.assert_called_once_with(file_names)
        mock_write_to_database.assert_called_once_with(mock_dataframe, table_name)


if __name__ == "__main__":
    unittest.main()
