# src/sql/tests/test_data_retrieval.py

import unittest
import pandas as pd
from unittest.mock import MagicMock
from data_retrieval import DataRetrieval

class TestDataRetrieval(unittest.TestCase):
    def setUp(self):
        self.db_config = {
            'user': 'test_user',
            'password': 'test_password',
            'host': 'test_host',
            'port': '5432',
            'database': 'test_db'
        }
        self.data_retrieval = DataRetrieval(self.db_config)

    def test_retrieve_transactions(self):
        start_date = '2023-01-01'
        end_date = '2023-12-31'
        self.data_retrieval.engine.connect().execute.return_value = MagicMock()
        transactions_df = self.data_retrieval.retrieve_transactions(start_date, end_date)
        self.assertIsInstance(transactions_df, pd.DataFrame)
        self.assertTrue(transactions_df.empty)

    def test_retrieve_users(self):
        self.data_retrieval.engine.connect().execute.return_value = MagicMock()
        users_df = self.data_retrieval.retrieve_users()
        self.assertIsInstance(users_df, pd.DataFrame)
        self.assertTrue(users_df.empty)

    def test_retrieve_fraud_transactions(self):
        self.data_retrieval.engine.connect().execute.return_value = MagicMock()
        fraud_transactions_df = self.data_retrieval.retrieve_fraud_transactions()
        self.assertIsInstance(fraud_transactions_df, pd.DataFrame)
        self.assertTrue(fraud_transactions_df.empty)


if __name__ == '__main__':
    unittest.main()
