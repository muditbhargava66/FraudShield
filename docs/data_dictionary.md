# Data Dictionary

This document provides a comprehensive description of the data fields and their characteristics used in the FraudShield anomaly detection pipeline.

## Transactions Table

| Field Name        | Data Type | Description                                           |
|-------------------|-----------|-------------------------------------------------------|
| transaction_id    | BIGINT    | Unique identifier for each transaction                |
| user_id           | BIGINT    | Identifier of the user associated with the transaction |
| transaction_date  | DATE      | Date when the transaction occurred                    |
| amount            | DECIMAL   | Transaction amount in the specified currency          |
| currency          | VARCHAR   | Currency code (e.g., USD, EUR) of the transaction     |
| status            | VARCHAR   | Status of the transaction (e.g., approved, declined)  |
| fraud_label       | BOOLEAN   | Indicates whether the transaction is fraudulent or not |

## Users Table

| Field Name | Data Type | Description                                        |
|------------|-----------|---------------------------------------------------|
| user_id    | BIGINT    | Unique identifier for each user                    |
| user_name  | VARCHAR   | Name of the user                                   |
| email      | VARCHAR   | Email address of the user                          |
| phone      | VARCHAR   | Phone number of the user                           |
| created_at | TIMESTAMP | Timestamp indicating when the user account was created |

## Engineered Features

The following features are engineered from the raw transaction and user data to capture patterns and anomalies indicative of fraudulent behavior:

| Feature Name              | Data Type | Description                                                          |
|---------------------------|-----------|----------------------------------------------------------------------|
| transaction_amount_avg    | FLOAT     | Average transaction amount for the user in the past 30 days          |
| transaction_frequency     | INTEGER   | Number of transactions made by the user in the past 30 days          |
| transaction_amount_zscore | FLOAT     | Z-score of the transaction amount relative to the user's history     |
| transaction_time_diff     | INTEGER   | Time difference (in seconds) between the current and last transaction |
| user_age                  | INTEGER   | Age of the user account (in days) at the time of the transaction     |
| user_transaction_ratio    | FLOAT     | Ratio of the user's transactions to the total transactions           |

These engineered features, along with the raw transaction and user data, are used to train the machine learning models for fraud detection.

Note: The exact set of engineered features may vary depending on the specific requirements and characteristics of the dataset.

---