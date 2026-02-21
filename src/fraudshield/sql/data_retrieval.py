"""
FraudShield - Advanced Anomaly Detection Pipeline

This module establishes parameter-safe connection drivers targeting
PostgreSQL architectures for pulling subset transaction windows natively.

File: data_retrieval.py
Author: Mudit Bhargava
License: MIT
"""

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import URL


class DataRetrieval:
    def __init__(self, db_config):
        # Use SQLAlchemy URL builder to safely construct connection string
        # This prevents SQL injection through connection string parameters
        db_url = URL.create(
            drivername="postgresql",
            username=db_config["user"],
            password=db_config["password"],
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
        )
        self.engine = create_engine(db_url)

    def retrieve_transactions(self, start_date, end_date):
        query = text(
            """
            SELECT t.transaction_id, t.user_id, t.merchant_id, t.transaction_date, t.amount, t.currency, t.status, t.fraud
            FROM transactions t
            WHERE t.transaction_date BETWEEN :start_date AND :end_date
        """
        )
        return pd.read_sql(query, self.engine, params={"start_date": start_date, "end_date": end_date})

    def retrieve_users(self):
        query = text(
            """
            SELECT u.user_id, u.user_name, u.email, u.phone, u.created_at
            FROM users u
        """
        )
        return pd.read_sql(query, self.engine)

    def retrieve_fraud_transactions(self):
        query = text(
            """
            SELECT t.transaction_id, t.user_id, t.merchant_id, t.transaction_date, t.amount, t.currency, t.status
            FROM transactions t
            WHERE t.fraud = true
        """
        )
        return pd.read_sql(query, self.engine)
