# SQL Schema

FraudShield uses SQLite by default (configurable via `FRAUDSHIELD_DATABASE_URL`).

## Tables

### Transactions

| Column Name       | Data Type     | Description |
|-------------------|---------------|-------------|
| transaction_id    | BIGINT PK     | Unique transaction identifier |
| user_id           | BIGINT NOT NULL | Foreign key to `users` |
| merchant_id       | BIGINT NOT NULL | Merchant identifier |
| transaction_date  | TIMESTAMP NOT NULL | Transaction timestamp |
| amount            | DECIMAL(10,2) NOT NULL | Transaction amount |
| currency          | VARCHAR(3) NOT NULL | ISO currency code |
| status            | VARCHAR(20) NOT NULL | approved, declined, reversed, pending |
| is_international  | BOOLEAN NOT NULL DEFAULT FALSE | Cross-border transaction flag |
| is_online         | BOOLEAN NOT NULL DEFAULT TRUE | Online channel flag |
| fraud             | BOOLEAN NOT NULL | Fraud label |

### Users

| Column Name | Data Type     | Description |
|-------------|---------------|-------------|
| user_id     | BIGINT PK     | Unique user identifier |
| user_name   | VARCHAR(100)  | User display name |
| email       | VARCHAR(100)  | Email address |
| phone       | VARCHAR(20)   | Phone number |
| created_at  | TIMESTAMP     | Account creation time |

## Indexes

- `idx_transactions_user_id` — on `transactions.user_id`
- `idx_transactions_merchant_id` — on `transactions.merchant_id`
- `idx_transactions_transaction_date` — on `transactions.transaction_date`
- `idx_users_email` — on `users.email`

## Schema File

The DDL is in `src/fraudshield/sql/create_tables.sql`. SQLite ingestion creates the
`transactions` table automatically via pandas `to_sql`; apply the DDL explicitly for
PostgreSQL (the `tests/integration_tests/test_postgresql.py` integration test does
this) when you also need the `users` table and named indexes.

## Secure Connection Handling

The default connection comes from the `FRAUDSHIELD_DATABASE_URL` environment
variable (SQLite at `data/processed/fraud_data.db` if unset). `DataRetrieval`
additionally accepts a `db_config` mapping and builds URLs safely:

```python
from sqlalchemy.engine.url import URL

db_url = URL.create(
    drivername=db_config.get("drivername", "postgresql+psycopg2"),
    username=db_config.get("user"),
    password=db_config.get("password"),
    host=db_config.get("host"),
    port=int(db_config["port"]) if db_config.get("port") else None,
    database=db_config.get("database"),
)
engine = create_engine(db_url)
```

- All queries use parameterized statements via `text()`
- Connection strings built with `URL.create()`, never f-strings
- Credentials supplied via environment variables, never committed

---
