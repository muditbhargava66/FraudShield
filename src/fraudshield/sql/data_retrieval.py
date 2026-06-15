"""
FraudShield - Advanced Anomaly Detection Pipeline

This module establishes parameter-safe connection drivers targeting
PostgreSQL architectures for pulling subset transaction windows natively.

File: data_retrieval.py
Author: Mudit Bhargava
License: MIT
"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine.url import URL

from fraudshield.config.settings import DatabaseSettings, get_settings
from fraudshield.runtime.resources import create_sqlalchemy_engine


class DataRetrieval:
    def __init__(self, db_config: Mapping[str, str] | None = None, db_connection_string: str | None = None) -> None:
        if db_connection_string:
            resolved_url: str | URL = db_connection_string
        elif db_config:
            drivername = db_config.get("drivername", "postgresql+psycopg2")
            port_str = db_config.get("port")
            resolved_url = URL.create(
                drivername=drivername,
                username=db_config.get("user"),
                password=db_config.get("password"),
                host=db_config.get("host"),
                port=int(port_str) if port_str else None,
                database=db_config.get("database"),
            )
        else:
            resolved_url = get_settings().database.sqlalchemy_url
        self.engine = create_sqlalchemy_engine(DatabaseSettings(sqlalchemy_url=str(resolved_url)))

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

    def close(self) -> None:
        self.engine.dispose()
