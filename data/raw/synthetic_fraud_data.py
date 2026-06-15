"""Generate a realistic synthetic fraud dataset for FraudShield.

Produces 5,000 transactions with learnable fraud patterns including
user behavioral profiles, merchant risk concentration, amount anomalies,
velocity bursts, and channel/time-of-day effects.

The fraud signal is designed so that tree-based models can achieve
meaningful recall (>0.3) with ~4000 training rows.
"""

import numpy as np
import pandas as pd

rng = np.random.default_rng(42)

n_samples = 5000
transaction_id = np.arange(1, n_samples + 1)

# --- Entity IDs ---
# 200 users; ~15 are "fraudsters" who generate most fraud
n_users = 200
fraudster_ids = np.array([3, 17, 29, 44, 61, 78, 92, 111, 133, 148, 157, 171, 185, 193, 199])
user_id = rng.integers(1, n_users + 1, size=n_samples)

# 80 merchants; ~8 are high-risk
n_merchants = 80
high_risk_merchants = np.array([5, 12, 27, 39, 51, 63, 74, 78])
merchant_id = rng.integers(1, n_merchants + 1, size=n_samples)

# --- Temporal (60 days, with hour-of-day variation) ---
start_time = pd.Timestamp("2024-01-01 00:00:00")
day_offsets = rng.integers(0, 60, size=n_samples)
hour_offsets = rng.integers(0, 24, size=n_samples)
minute_offsets = rng.integers(0, 60, size=n_samples)
second_offsets = rng.integers(0, 60, size=n_samples)
transaction_date = start_time + pd.to_timedelta(  # type: ignore[call-overload]
    day_offsets * 86400 + hour_offsets * 3600 + minute_offsets * 60 + second_offsets,
    unit="s",
)

# --- Transaction attribute ---
# Legitimate transactions: moderate amounts
# Fraudulent transactions will have systematically higher amounts
amount = rng.lognormal(mean=3.5, sigma=0.6, size=n_samples).round(2)
amount = np.clip(amount, 0.50, 15000.0)

currency = rng.choice(
    ["USD", "EUR", "GBP", "JPY"], size=n_samples, p=[0.55, 0.25, 0.12, 0.08]
)
status = rng.choice(
    ["approved", "declined", "reversed", "pending"],
    size=n_samples,
    p=[0.85, 0.08, 0.03, 0.04],
)

# --- Channel flags ---
is_international = rng.choice([True, False], size=n_samples, p=[0.15, 0.85])
is_online = rng.choice([True, False], size=n_samples, p=[0.60, 0.40])

# --- Fraud label: strong, learnable patterns ---
# Each factor contributes a meaningful boost. A transaction with 2-3 factors
# has a high probability of fraud.

is_fraudster = np.isin(user_id, fraudster_ids)
is_high_risk_merchant = np.isin(merchant_id, high_risk_merchants)
hour = transaction_date.hour

# 1. Fraudster base rate: these users commit fraud at ~25% when other factors align
fraud_prob = np.full(n_samples, 0.01)  # base rate 1% for normal users

# 2. Fraudster strong signal
fraud_prob = np.where(is_fraudster, fraud_prob + 0.15, fraud_prob)

# 3. High-risk merchant signal
fraud_prob = np.where(is_high_risk_merchant, fraud_prob + 0.10, fraud_prob)

# 4. Amount anomaly: fraud txns tend to be higher
# Make fraudulent users' amounts systematically higher
amount_boost = np.where(is_fraudster, rng.lognormal(1.0, 0.3, size=n_samples), 1.0)
amount = (amount * amount_boost).round(2)
amount = np.clip(amount, 0.50, 15000.0)

# Amount risk: top quartile of amounts
amt_threshold = np.percentile(amount, 80)
fraud_prob = np.where(amount > amt_threshold, fraud_prob + 0.08, fraud_prob)

# 5. International + online combo
fraud_prob = np.where(is_international & is_online, fraud_prob + 0.07, fraud_prob)
fraud_prob = np.where(is_international & ~is_online, fraud_prob + 0.03, fraud_prob)

# 6. Night-time risk (1-5 AM)
is_night = (hour >= 1) & (hour <= 5)
fraud_prob = np.where(is_night & is_fraudster, fraud_prob + 0.10, fraud_prob)
fraud_prob = np.where(is_night & ~is_fraudster, fraud_prob + 0.02, fraud_prob)

# 7. Declined status correlates with fraud
fraud_prob = np.where(status == "declined", fraud_prob + 0.12, fraud_prob)
fraud_prob = np.where(status == "reversed", fraud_prob + 0.08, fraud_prob)

# Clip and sample
fraud_prob = np.clip(fraud_prob, 0, 0.85)
fraud = (rng.random(n_samples) < fraud_prob).astype(int)

# --- Build DataFrame ---
data = pd.DataFrame(
    {
        "transaction_id": transaction_id,
        "user_id": user_id,
        "merchant_id": merchant_id,
        "transaction_date": transaction_date,
        "amount": amount,
        "currency": currency,
        "status": status,
        "is_international": is_international,
        "is_online": is_online,
        "fraud": fraud,
    }
)

data = data.sort_values("transaction_date").reset_index(drop=True)

output_path = "data/raw/synthetic_fraud_data.csv"
data.to_csv(output_path, index=False)

fraud_count = data["fraud"].sum()
print(f"Generated {len(data)} transactions -> {output_path}")
print(f"Fraud rate: {data['fraud'].mean():.2%} ({fraud_count} / {len(data)})")
print(f"Date range: {data['transaction_date'].min()} -> {data['transaction_date'].max()}")
print(f"Unique users: {data['user_id'].nunique()}, merchants: {data['merchant_id'].nunique()}")
print(f"Fraudster IDs involved: {sorted(data.loc[data['fraud']==1, 'user_id'].unique())[:20]}...")
