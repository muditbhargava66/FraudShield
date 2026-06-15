# SQL Schema

FraudShield uses SQLite by default (configurable via `FRAUDSHIELD_DATABASE_URL`).

## Tables

### Transactions

| Column Name       | Data Type     | Description |
|-------------------|---------------|-------------|
| transaction_id    | BIGINT PK     | Unique transaction identifier |
| user_id           | BIGINT NOT NULL | Foreign key to `users` |
| merchant_id       | BIGINT NOT NULL | Merchant identifier |
| transaction_date  | DATE NOT NULL  | Transaction timestamp |
| amount            | DECIMAL(10,2) | Transaction amount |
| currency          | VARCHAR(3)    | ISO currency code |
| status            | VARCHAR(20)   | approved, declined, reversed, pending |
| is_international  | BOOLEAN DEFAULT 0 | Cross-border transaction flag |
| is_online         | BOOLEAN DEFAULT 1 | Online channel flag |
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

The DDL is in `src/fraudshield/sql/create_tables.sql`. It is applied automatically during ingestion.

## Secure Connection Handling

```python
from sqlalchemy.engine.url import URL

db_url = URL.create(
    drivername='postgresql',
    username=db_config["user"],
    password=db_config["password"],
    host=db_config["host"],
    port=db_config["port"],
    database=db_config["database"]
)
engine = create_engine(db_url)
```

- All queries use parameterized statements via `text()`
- Connection strings built with `URL.create()`, never f-strings
- Test credentials via environment variables

---
