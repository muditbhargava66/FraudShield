# Migration Guide: v2.2.0 → v2.3.0

## Overview of Changes

- **Tooling**: Replaced flake8/pylint/black with ruff + mypy
- **Data**: New synthetic data generator (5,000 transactions, multi-factor fraud)
- **Schema**: Added `is_international` and `is_online` columns
- **Features**: Fixed duplicate-index bug in rolling window computation
- **Config**: Added `[tool.mypy]` and `[tool.ruff]` to `pyproject.toml`

## Breaking Changes

### 1. Database Schema

Two new columns added to the `transactions` table:

```sql
is_international BOOLEAN NOT NULL DEFAULT 0,
is_online        BOOLEAN NOT NULL DEFAULT 1,
```

**Action**: Delete old SQLite DB and re-ingest:

```bash
rm data/processed/fraud_data.db data/processed/ingested_data.csv
uv run python data/raw/synthetic_fraud_data.py
uv run fraudshield_ingest
```

### 2. Feature Engineering

The `_rolling_group_agg` and `_compute_user_amount_zscore` functions now use integer position columns (`__pos__`) instead of DatetimeIndex alignment. This fixes a `ValueError: cannot reindex on an axis with duplicate labels` error that occurred with larger datasets.

The API is unchanged — `add_transaction_features(df, config)` works the same way.

**Action**: Re-preprocess and retrain models:

```bash
uv run fraudshield_preprocess
uv run fraudshield_train --model both
```

### 3. Linting Toolchain

| Old | New |
|-----|-----|
| `flake8 src tests` | `ruff check src tests` |
| `pylint src/` | `mypy src/` |
| `black src tests` | `ruff format src tests` |

**Action**: Update CI configs and IDE settings:

```bash
# Run new linters
uv run ruff check src tests
uv run mypy src/
uv run ruff format --check src tests
```

### 4. Synthetic Data

The old generator produced 1,000 samples with simplistic fraud patterns. The new generator produces 5,000 samples with:

- 15 designated fraudster users
- 8 high-risk merchants
- Multi-factor fraud: amount, user behavior, merchant, channel, time-of-day
- ~7% fraud rate

**Action**: Regenerate data and retrain. Model metrics will differ from v2.2.0.

## Migration Steps

```bash
# 1. Pull latest
git checkout version-2.3.0
git pull

# 2. Reinstall (picks up new ruff/mypy configs)
uv pip install -e ".[dev]"

# 3. Regenerate data
uv run python data/raw/synthetic_fraud_data.py

# 4. Run full pipeline
uv run fraudshield_ingest
uv run fraudshield_preprocess
uv run fraudshield_train --model both
uv run fraudshield_evaluate --model_path data/models/xgboost.pkl

# 5. Verify quality
uv run pytest tests/ -v
uv run ruff check src tests
uv run mypy src/
```

## Expected Model Performance

With the v2.3.0 synthetic data:

| Model | ROC-AUC | Precision@0.3 | Recall@0.3 |
|-------|---------|---------------|------------|
| Random Forest | ~0.76 | ~0.24 | ~0.40 |
| XGBoost | ~0.72 | ~0.25 | ~0.12 |

At default threshold (0.5), recall is low because fraud detection typically requires a lower decision threshold. Use the threshold sweep in `notebooks/model_experimentation.ipynb` to find the right operating point.

## Rollback

```bash
git checkout version-2.2.0
uv pip install -e .
uv run fraudshield_ingest
uv run fraudshield_preprocess
uv run fraudshield_train --model both
```

---
