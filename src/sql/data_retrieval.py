# src/sql/data_retrieval.py

import pandas as pd
from sqlalchemy import create_engine

class DataRetrieval:
    def __init__(self, db_config):
        self.engine = create_engine(f'postgresql://{db_config["user"]}:{db_config["password"]}@{db_config["host"]}:{db_config["port"]}/{db_config["database"]}')

    def retrieve_transactions(self, start_date, end_date):
        query = f'''
            SELECT t.transaction_id, t.user_id, t.transaction_date, t.amount, t.currency, t.status, t.fraud_label
            FROM transactions t
            WHERE t.transaction_date BETWEEN '{start_date}' AND '{end_date}'
        '''
        return pd.read_sql(query, self.engine)

    def retrieve_users(self):
        query = '''
            SELECT u.user_id, u.user_name, u.email, u.phone, u.created_at
            FROM users u
        '''
        return pd.read_sql(query, self.engine)

    def retrieve_fraud_transactions(self):
        query = '''
            SELECT t.transaction_id, t.user_id, t.transaction_date, t.amount, t.currency, t.status
            FROM transactions t
            WHERE t.fraud_label = true
        '''
        return pd.read_sql(query, self.engine)
