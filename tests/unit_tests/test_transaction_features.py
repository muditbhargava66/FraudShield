import pandas as pd

from fraudshield.feature_engineering.stateful_aggregates import StatefulFeatureStore
from fraudshield.feature_engineering.transaction_features import (
    TransactionFeatureConfig,
    add_transaction_features,
)


def test_transaction_feature_generation_closed_left():
    df = pd.DataFrame(
        {
            "transaction_id": [1, 2, 3, 4],
            "user_id": [1, 1, 1, 2],
            "merchant_id": [10, 10, 11, 10],
            "transaction_date": [
                "2024-01-01 00:00:00",
                "2024-01-01 00:30:00",
                "2024-01-01 02:00:00",
                "2024-01-01 00:10:00",
            ],
            "amount": [100.0, 150.0, 200.0, 50.0],
            "currency": ["USD", "USD", "USD", "EUR"],
            "status": ["approved", "approved", "declined", "approved"],
            "fraud": [0, 1, 0, 0],
        }
    )

    config = TransactionFeatureConfig(windows=["1h"])
    result = add_transaction_features(df, config)

    result = result.set_index("transaction_id")

    # First transaction for user 1 has no history — fillna(0.0) converts NaN to 0
    assert result.loc[1, "user_txn_count_1h"] == 0.0

    # Second transaction sees the first within 1h
    assert result.loc[2, "user_txn_count_1h"] == 1

    # Third transaction is outside the 1h window from the second — fillna(0.0)
    assert result.loc[3, "user_txn_count_1h"] == 0.0

    # User 1 time since last transaction at id=2 is 30 minutes
    assert result.loc[2, "user_time_since_last_txn"] == 1800.0

    # Merchant fraud rate uses past transactions only (merchant 10)
    assert result.loc[2, "merchant_fraud_rate_1h"] == 0.0


def test_stateful_feature_store_tracks_history_without_recomputing():
    store = StatefulFeatureStore(windows=["1h"])

    first = store.build_features(
        {
            "transaction_id": "t1",
            "user_id": "u1",
            "merchant_id": "m1",
            "currency": "USD",
            "status": "approved",
            "amount": 100.0,
            "transaction_date": "2024-01-01T00:00:00Z",
        }
    )
    second = store.build_features(
        {
            "transaction_id": "t2",
            "user_id": "u1",
            "merchant_id": "m1",
            "currency": "USD",
            "status": "approved",
            "amount": 200.0,
            "transaction_date": "2024-01-01T00:30:00Z",
        }
    )

    assert first["user_txn_count_1h"] == 0.0
    assert second["user_txn_count_1h"] == 1.0
    assert second["user_amount_sum_1h"] == 100.0
    assert second["user_time_since_last_txn"] == 1800.0
