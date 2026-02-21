# Migration Guide: Upgrading to Secure FraudShield

This guide helps you migrate from the previous version of FraudShield to the updated version with security and data quality improvements.

## Overview

The updated FraudShield includes critical fixes for:
- SQL injection vulnerabilities
- Data leakage in feature engineering
- Buffer overflows in C++ modules
- Performance optimizations
- Enhanced error handling

## Breaking Changes

### 1. Database Connection API

**Old Code**:
```python
from fraudshield.sql.data_retrieval import DataRetrieval

db_config = {
    'user': 'myuser',
    'password': 'mypass',
    'host': 'localhost',
    'port': '5432',
    'database': 'frauddb'
}

retrieval = DataRetrieval(db_config)
```

**New Code** (No changes required - internal implementation updated):
```python
from fraudshield.sql.data_retrieval import DataRetrieval

# Same API, but now uses secure URL builder internally
db_config = {
    'user': 'myuser',
    'password': 'mypass',
    'host': 'localhost',
    'port': '5432',
    'database': 'frauddb'
}

retrieval = DataRetrieval(db_config)
```

**Action Required**: None - backward compatible

### 2. Feature Engineering

**Old Code**:
```python
from fraudshield.feature_engineering.transaction_features import add_transaction_features

# This had data leakage issues
features_df = add_transaction_features(df, config)
```

**New Code** (No API changes, but behavior improved):
```python
from fraudshield.feature_engineering.transaction_features import add_transaction_features

# Same API, but now prevents data leakage
features_df = add_transaction_features(df, config)
```

**Action Required**: 
- Re-train all models with the corrected features
- Expect different feature values (no longer includes current transaction)
- Model performance may change (should be more realistic)

### 3. Model Training

**Old Code**:
```python
from fraudshield.model_training.train_models import train_and_save

metrics = train_and_save(
    preprocessed_data='data/models/preprocessed_data.npy',
    test_data='data/models/test_data.npy',
    output_dir='data/models',
    model='both'
)
```

**New Code** (Same API):
```python
from fraudshield.model_training.train_models import train_and_save

# Same API, but now with better label encoding validation
metrics = train_and_save(
    preprocessed_data='data/models/preprocessed_data.npy',
    test_data='data/models/test_data.npy',
    output_dir='data/models',
    model='both'
)
```

**Action Required**: None - backward compatible

### 4. C++ Modules

**Old Code**:
```cpp
// Compilation
g++ -O3 -o data_cleaning data_cleaning.cpp
```

**New Code** (Same compilation):
```cpp
// Same compilation, but now with bounds checking
g++ -O3 -o data_cleaning data_cleaning.cpp
```

**Action Required**: 
- Recompile C++ modules to get safety improvements
- Test with edge cases (empty data, window_size=1, etc.)

## Migration Steps

### Step 1: Backup Current System

```bash
# Backup your current models
cp -r data/models data/models.backup

# Backup your database
pg_dump frauddb > frauddb_backup.sql

# Backup configuration
cp -r conf conf.backup
```

### Step 2: Update Dependencies

```bash
# Update Python packages
uv sync

# Or with pip
pip install -r requirements.txt --upgrade
```

### Step 3: Update Environment Variables

Create a `.env` file or export environment variables:

```bash
# Database credentials
export DB_USER=your_username
export DB_PASSWORD=your_password
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=frauddb

# Test database credentials
export TEST_DB_USER=test_user
export TEST_DB_PASSWORD=test_password
export TEST_DB_HOST=localhost
export TEST_DB_PORT=5432
export TEST_DB_NAME=test_db
```

### Step 4: Recompile C++ Modules

```bash
cd src/fraudshield/data_cleaning
g++ -O3 -std=c++11 -o data_cleaning data_cleaning.cpp

cd ../feature_engineering
g++ -O3 -std=c++11 -o feature_engineering feature_engineering.cpp
```

### Step 5: Re-preprocess Data

The feature engineering has changed, so you need to re-preprocess:

```bash
python -m fraudshield.data_preprocessing.data_preprocessing \
    --input_data data/processed/ingested_data.csv \
    --train_data data/models/preprocessed_data.npy \
    --test_data data/models/test_data.npy \
    --preprocessor_path data/models/preprocessor.joblib \
    --metadata_path data/models/preprocessing_metadata.json
```

### Step 6: Re-train Models

Since features have changed, re-train your models:

```bash
python -m fraudshield.model_training.train_models \
    --preprocessed_data data/models/preprocessed_data.npy \
    --test_data data/models/test_data.npy \
    --output_dir data/models \
    --model both
```

### Step 7: Update Airflow DAGs

If using Airflow, restart the scheduler to pick up the changes:

```bash
# Stop Airflow
airflow scheduler stop
airflow webserver stop

# Start Airflow
airflow scheduler &
airflow webserver --port 8080 &
```

### Step 8: Run Tests

Verify everything works:

```bash
# Run unit tests
pytest tests/unit_tests/ -v

# Run integration tests
pytest tests/integration_tests/ -v

# Run C++ tests (if available)
cd tests/cpp
./run_tests.sh
```

## Validation Checklist

After migration, verify:

- [ ] Database connections work without errors
- [ ] Feature engineering produces expected output
- [ ] No data leakage in features (check with temporal validation)
- [ ] Models train successfully
- [ ] Model performance is reasonable (may differ from before)
- [ ] C++ modules don't crash on edge cases
- [ ] Airflow DAGs run without errors
- [ ] Tests pass
- [ ] Logs show no security warnings

## Expected Changes in Model Performance

### Why Performance May Change

1. **Data Leakage Fix**: Features no longer include current transaction
   - Training accuracy may decrease slightly
   - Test accuracy should be more realistic
   - Generalization should improve

2. **Statistical Corrections**: Sample std instead of population std
   - Z-scores will be slightly different
   - Outlier detection may change

3. **Time-Based Splitting**: When temporal features are present
   - More realistic evaluation
   - May show lower performance if temporal drift exists

### Benchmarking

Compare old vs new models:

```python
import pandas as pd

# Load old metrics
old_metrics = pd.read_json('data/models.backup/training_metrics.json')

# Load new metrics
new_metrics = pd.read_json('data/models/training_metrics.json')

# Compare
comparison = pd.DataFrame({
    'Old': old_metrics['random_forest'],
    'New': new_metrics['random_forest']
})

print(comparison)
```

Expected changes:
- Training accuracy: May decrease 1-3%
- Test accuracy: Should be similar or slightly better
- Precision/Recall: May shift based on class balance
- ROC AUC: Should remain stable or improve

## Rollback Procedure

If you need to rollback:

```bash
# Stop services
airflow scheduler stop
airflow webserver stop

# Restore backups
rm -rf data/models
mv data/models.backup data/models

# Restore database
psql frauddb < frauddb_backup.sql

# Restore configuration
rm -rf conf
mv conf.backup conf

# Checkout previous version
git checkout <previous-version-tag>

# Restart services
airflow scheduler &
airflow webserver --port 8080 &
```

## Troubleshooting

### Issue: Import Error for SQLAlchemy URL

**Error**: `ImportError: cannot import name 'URL' from 'sqlalchemy.engine.url'`

**Solution**: Update SQLAlchemy:
```bash
pip install sqlalchemy>=1.4.0 --upgrade
```

### Issue: Feature Values Changed

**Error**: Features have different values than before

**Solution**: This is expected! The old implementation had data leakage. Re-train models with new features.

### Issue: C++ Module Crashes

**Error**: Segmentation fault in C++ modules

**Solution**: 
1. Recompile with debug symbols: `g++ -g -O0 data_cleaning.cpp`
2. Run with valgrind: `valgrind ./data_cleaning`
3. Check for edge cases (empty data, window_size=1)

### Issue: Airflow Variables Not Updating

**Error**: DAG uses old variable values

**Solution**: The new implementation fetches variables at runtime. Clear Airflow cache:
```bash
airflow db reset
airflow db init
```

### Issue: Test Database Connection Fails

**Error**: `Connection refused` or authentication errors

**Solution**: Set environment variables:
```bash
export TEST_DB_USER=test_user
export TEST_DB_PASSWORD=test_password
export TEST_DB_HOST=localhost
```

## Performance Optimization Tips

### 1. Database Connection Pooling

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    db_url,
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20
)
```

### 2. Batch Processing

For large datasets, process in batches:

```python
chunk_size = 10000
for chunk in pd.read_csv('large_file.csv', chunksize=chunk_size):
    process_chunk(chunk)
```

### 3. Parallel Feature Engineering

Use multiple cores for feature engineering:

```python
from joblib import Parallel, delayed

results = Parallel(n_jobs=-1)(
    delayed(add_transaction_features)(chunk, config)
    for chunk in chunks
)
```

## Security Best Practices

### 1. Credential Management

Never hardcode credentials:

```python
# ❌ DON'T
db_config = {'user': 'admin', 'password': 'password123'}

#  DO
import os
db_config = {
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}
```

### 2. SQL Query Validation

Always use parameterized queries:

```python
# ❌ DON'T
query = f"SELECT * FROM transactions WHERE user_id = {user_id}"

#  DO
from sqlalchemy import text
query = text("SELECT * FROM transactions WHERE user_id = :user_id")
result = engine.execute(query, user_id=user_id)
```

### 3. Input Validation

Validate all user inputs:

```python
def validate_window_size(window_size):
    if not isinstance(window_size, int):
        raise ValueError("window_size must be an integer")
    if window_size < 2:
        raise ValueError("window_size must be at least 2")
    return window_size
```

## Support

If you encounter issues during migration:

1. Check the logs in `logs/` directory
2. Review the documentation in `docs/`
3. Run the test suite to identify specific failures
4. Check the GitHub issues for similar problems
5. Contact support with detailed error messages

## Additional Resources

- [Security and Quality Documentation](security_and_quality.md)
- [Setup Instructions](setup_instructions.md)
- [Data Dictionary](data_dictionary.md)
- [C++ Modules Documentation](cpp_modules.md)
- [Updated Best Practices Notebook](../notebooks/updated_best_practices.ipynb)
- [Fixes Summary](../FIXES_SUMMARY.md)

## Conclusion

The migration to the updated FraudShield brings significant improvements in security, data quality, and reliability. While some changes require re-training models, the benefits far outweigh the migration effort:

-  Eliminated critical security vulnerabilities
-  Fixed data leakage for more accurate models
-  Improved code safety and error handling
-  Better performance through optimization
-  Enhanced maintainability and debugging

Take your time with the migration, validate each step, and don't hesitate to reach out for support if needed.
