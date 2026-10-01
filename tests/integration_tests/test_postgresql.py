# tests/integration_tests/test_postgresql.py

import os

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from fraudshield.data_ingestion.data_ingestion import DataIngestion


def get_pg_test_url() -> str:
    return os.getenv("FRAUDSHIELD_DATABASE_URL", "")


def test_postgresql_ingestion(tmpdir):
    """
    Integration test validating that FraudShield DataIngestion correctly writes
    and schema-maps data inside a live PostgreSQL instance. Skips gracefully if Postgres is offline.
    """
    pg_url = get_pg_test_url()
    if not pg_url:
        pytest.skip("Set FRAUDSHIELD_DATABASE_URL to run the PostgreSQL integration test.")
    
    # Attempt connection to verify database is online
    try:
        engine = create_engine(pg_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        pytest.skip(f"PostgreSQL test database not available at {pg_url}: {exc}")

    # Prepare PostgreSQL clean schema
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS transactions CASCADE;"))
        conn.execute(text("DROP TABLE IF EXISTS users CASCADE;"))
        
        # Load and execute DDL
        schema_path = os.path.join(os.path.dirname(__file__), "../../src/fraudshield/sql/create_tables.sql")
        with open(schema_path, "r") as f:
            ddl_statements = f.read()
        
        # Execute each statement
        for stmt in ddl_statements.split(";"):
            cleaned_stmt = stmt.strip()
            if cleaned_stmt:
                conn.execute(text(cleaned_stmt))

    # Create dummy data
    data = pd.DataFrame({
        "transaction_id": [1001, 1002, 1003],
        "user_id": [11, 12, 13],
        "merchant_id": [201, 202, 203],
        "transaction_date": ["2026-07-01", "2026-07-01", "2026-07-01"],
        "amount": [150.00, 25.50, 999.99],
        "currency": ["USD", "EUR", "USD"],
        "status": ["processed", "processed", "failed"],
        "is_international": [False, True, False],
        "is_online": [True, True, False],
        "fraud": [False, False, True]
    })

    # Save to temp csv
    data_path = tmpdir.join("synthetic_fraud_data.csv")
    data.to_csv(data_path, index=False)

    # Execute Ingestion
    ingestion = DataIngestion(str(tmpdir), pg_url)
    try:
        ingestion.run_ingestion_pipeline("synthetic_fraud_data.csv", "transactions", if_exists="append")
        
        # Verify database contents
        with engine.connect() as conn:
            result = conn.execute(text("SELECT count(*) FROM transactions")).scalar()
            assert result == 3, f"Expected 3 records in transactions, found {result}"
            
            # Fetch a sample to verify values
            row = conn.execute(text("SELECT amount, is_online, fraud FROM transactions WHERE transaction_id = 1003")).fetchone()
            assert row is not None
            assert float(row[0]) == 999.99
            assert not row[1]
            assert row[2]
    finally:
        ingestion.close()
        engine.dispose()
