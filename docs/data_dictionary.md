# Data Dictionary

This document provides a comprehensive description of the data fields and their characteristics used in the FraudShield anomaly detection pipeline.

## Transactions Table

| Field Name        | Data Type | Description                                            |
|-------------------|-----------|--------------------------------------------------------|
| transaction_id    | BIGINT    | Unique identifier for each transaction                 |
| user_id           | BIGINT    | Identifier of the user associated with the transaction |
| merchant_id       | BIGINT    | Identifier of the merchant for the transaction         |
| transaction_date  | DATE      | Date when the transaction occurred                     |
| amount            | DECIMAL   | Transaction amount in the specified currency           |
| currency          | VARCHAR   | Currency code (e.g., USD, EUR) of the transaction      |
| status            | VARCHAR   | Status of the transaction (e.g., approved, declined)   |
| fraud             | BOOLEAN   | Indicates whether the transaction is fraudulent or not |

## Users Table

| Field Name | Data Type | Description                                            |
|------------|-----------|--------------------------------------------------------|
| user_id    | BIGINT    | Unique identifier for each user                        |
| user_name  | VARCHAR   | Name of the user                                       |
| email      | VARCHAR   | Email address of the user                              | 
| phone      | VARCHAR   | Phone number of the user                               |
| created_at | TIMESTAMP | Timestamp indicating when the user account was created |

## Engineered Features

The following features are engineered from the raw transaction and user data to capture patterns and anomalies indicative of fraudulent behavior:

| Feature Name              | Data Type | Description                                                          |
|---------------------------|-----------|----------------------------------------------------------------------|
| user_txn_count_{window}        | INTEGER   | Count of user transactions in the rolling time window (excludes current transaction) |
| user_amount_sum_{window}       | FLOAT     | Sum of user transaction amounts in the rolling time window (excludes current) |
| user_amount_mean_{window}      | FLOAT     | Mean of user transaction amounts in the rolling time window (excludes current) |
| user_time_since_last_txn       | FLOAT     | Seconds since the user's last transaction                            |
| user_amount_zscore             | FLOAT     | Z-score of amount against the user's historical mean/std (excludes current, uses sample std) |
| merchant_txn_count_{window}    | INTEGER   | Count of merchant transactions in the rolling time window (excludes current) |
| merchant_amount_mean_{window}  | FLOAT     | Mean merchant amount in the rolling time window (excludes current)   |
| merchant_fraud_rate_{window}   | FLOAT     | Rolling fraud rate for the merchant using past transactions only (excludes current) |
| currency_txn_count_{window}    | INTEGER   | Count of currency transactions in the rolling time window (excludes current) |
| status_txn_count_{window}      | INTEGER   | Count of status occurrences in the rolling time window (excludes current) |

These engineered features, along with the raw transaction and user data, are used to train the machine learning models for fraud detection.

Default rolling windows are `1h`, `24h`, `7d`, and `30d`, and can be configured via the preprocessing CLI.

**Important Notes on Data Leakage Prevention:**
- All rolling aggregations use `closed="left"` to exclude the current transaction
- Z-score calculations use expanding windows with `shift(1)` to exclude current values
- Sample standard deviation (ddof=1) is used instead of population standard deviation
- Division by zero is handled explicitly - returns NaN when std=0
- Time-based splitting is enforced when temporal features are present to prevent temporal leakage

Note: The exact set of engineered features may vary depending on the specific requirements and characteristics of the dataset.

---
