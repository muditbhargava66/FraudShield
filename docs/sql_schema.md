# SQL Schema

FraudShield uses a SQL database to store and manage transaction and user data. The database schema is designed to efficiently organize the data and support fast querying and retrieval.

## Tables

### Transactions Table

The `transactions` table stores information about each transaction. It has the following columns:

| Column Name       | Data Type    | Description                                                    |
|-------------------|--------------|----------------------------------------------------------------|
| transaction_id    | BIGINT       | Unique identifier for the transaction                          |
| user_id           | BIGINT       | Foreign key referencing the `users` table                       |
| transaction_date  | DATE         | Date of the transaction                                        |
| amount            | DECIMAL(10,2)| Amount of the transaction                                      |
| currency          | VARCHAR(3)   | Currency code of the transaction                               |
| status            | VARCHAR(20)  | Status of the transaction (e.g., approved, declined)           |
| fraud_label       | BOOLEAN      | Indicates whether the transaction is labeled as fraudulent     |

### Users Table

The `users` table stores information about the users involved in the transactions. It has the following columns:

| Column Name | Data Type    | Description                                        |
|-------------|--------------|---------------------------------------------------|
| user_id     | BIGINT       | Unique identifier for the user                     |
| user_name   | VARCHAR(100) | Name of the user                                   |
| email       | VARCHAR(100) | Email address of the user                          |
| phone       | VARCHAR(20)  | Phone number of the user                           |
| created_at  | TIMESTAMP    | Timestamp indicating when the user was created     |

## Indexes

To optimize query performance, the following indexes are created:

- `idx_transactions_user_id`: Index on the `user_id` column of the `transactions` table to enable fast lookups and joins with the `users` table.
- `idx_transactions_transaction_date`: Index on the `transaction_date` column of the `transactions` table to facilitate efficient date-based queries.
- `idx_users_email`: Index on the `email` column of the `users` table to allow quick searches based on email addresses.

## Constraints

The following constraints are enforced to ensure data integrity:

- `transactions.transaction_id`: Primary key constraint to ensure uniqueness of transaction IDs.
- `transactions.user_id`: Foreign key constraint referencing the `users.user_id` column to maintain referential integrity between transactions and users.
- `users.user_id`: Primary key constraint to ensure uniqueness of user IDs.

## Data Retrieval

To retrieve data from the SQL database, FraudShield provides a set of optimized SQL queries. These queries are designed to efficiently fetch the required data for analysis and model training. Some common queries include:

- Retrieving transactions within a specific date range.
- Retrieving transactions associated with a particular user.
- Retrieving user details based on user ID or email address.
- Retrieving aggregated statistics, such as total transaction amount or count, grouped by user or time period.

The SQL queries are implemented using parameterized statements to prevent SQL injection vulnerabilities and improve performance by enabling query caching.

## Database Configuration

FraudShield uses a configuration file to store the database connection details, such as the host, port, username, password, and database name. The configuration file is securely stored and accessed only by authorized components of the pipeline.

The database connection is established using a connection pooling mechanism to optimize resource utilization and minimize the overhead of creating new connections for each query.

## Data Backup and Recovery

To ensure data durability and recoverability, FraudShield implements a regular backup strategy. The database is automatically backed up at specified intervals (e.g., daily) to a secure location. The backups are encrypted and stored in a fault-tolerant storage system.

In case of any data loss or corruption, the database can be restored from the latest backup to minimize data loss and ensure business continuity.

The SQL schema and database configuration in FraudShield are designed to provide a robust and efficient data storage solution for the anomaly detection pipeline. The schema is normalized to reduce redundancy and improve data integrity, while the indexes and queries are optimized for fast data retrieval and analysis.

---