import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

n_samples = 1000
transaction_id = np.arange(1, n_samples + 1)
user_id = rng.integers(1, 101, size=n_samples)
merchant_id = rng.integers(1, 51, size=n_samples)

start_time = pd.Timestamp("2024-01-01 00:00:00")
time_offsets = pd.to_timedelta(rng.integers(0, 60 * 60 * 24 * 30, size=n_samples), unit="s")
transaction_date = start_time + time_offsets

amount = rng.lognormal(mean=3.5, sigma=0.6, size=n_samples).round(2)
currency = rng.choice(["USD", "EUR", "GBP"], size=n_samples, p=[0.6, 0.25, 0.15])
status = rng.choice(["approved", "declined", "reversed"], size=n_samples, p=[0.9, 0.08, 0.02])

# Heuristic fraud probability based on amount and status
base_prob = 0.02
amount_risk = (amount > np.percentile(amount, 90)).astype(float) * 0.08
status_risk = np.where(status == "declined", 0.05, np.where(status == "reversed", 0.08, 0.0))
fraud_prob = np.clip(base_prob + amount_risk + status_risk, 0, 0.5)
fraud = (rng.random(n_samples) < fraud_prob).astype(int)

data = pd.DataFrame(
    {
        "transaction_id": transaction_id,
        "user_id": user_id,
        "merchant_id": merchant_id,
        "transaction_date": transaction_date,
        "amount": amount,
        "currency": currency,
        "status": status,
        "fraud": fraud,
    }
)

data = data.sort_values("transaction_date")
data.to_csv("data/raw/synthetic_fraud_data.csv", index=False)
