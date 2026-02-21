import unittest
import pandas as pd
from unittest.mock import patch
from fraudshield.sql.data_retrieval import DataRetrieval


class TestDataRetrieval(unittest.TestCase):
    def setUp(self):
        # Use environment variables or mock credentials instead of hardcoded values
        import os

        self.db_config = {
            "user": os.getenv("TEST_DB_USER", "test_user"),
            "password": os.getenv("TEST_DB_PASSWORD", "test_password"),
            "host": os.getenv("TEST_DB_HOST", "localhost"),
            "port": os.getenv("TEST_DB_PORT", "5432"),
            "database": os.getenv("TEST_DB_NAME", "test_db"),
        }
        self.data_retrieval = DataRetrieval(self.db_config)

    def test_retrieve_transactions(self):
        start_date = "2023-01-01"
        end_date = "2023-12-31"
        with patch("pandas.read_sql", return_value=pd.DataFrame()) as mock_read:
            transactions_df = self.data_retrieval.retrieve_transactions(start_date, end_date)
            mock_read.assert_called_once()
            self.assertIsInstance(transactions_df, pd.DataFrame)
            self.assertTrue(transactions_df.empty)

    def test_retrieve_users(self):
        with patch("pandas.read_sql", return_value=pd.DataFrame()) as mock_read:
            users_df = self.data_retrieval.retrieve_users()
            mock_read.assert_called_once()
            self.assertIsInstance(users_df, pd.DataFrame)
            self.assertTrue(users_df.empty)

    def test_retrieve_fraud_transactions(self):
        with patch("pandas.read_sql", return_value=pd.DataFrame()) as mock_read:
            fraud_transactions_df = self.data_retrieval.retrieve_fraud_transactions()
            mock_read.assert_called_once()
            self.assertIsInstance(fraud_transactions_df, pd.DataFrame)
            self.assertTrue(fraud_transactions_df.empty)


if __name__ == "__main__":
    unittest.main()
