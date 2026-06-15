# Security and Data Quality

## Security

### SQL Injection Prevention

Connection strings use SQLAlchemy's `URL.create()`:

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

### Parameterized Queries

All database queries use `text()` with parameter binding:

```python
query = text('SELECT * FROM transactions WHERE transaction_date BETWEEN :start AND :end')
df = pd.read_sql(query, engine, params={'start': start_date, 'end': end_date})
```

### Credential Management

Credentials loaded from environment variables, never hardcoded:

```python
db_config = {
    'user': os.getenv('TEST_DB_USER', 'test_user'),
    'password': os.getenv('TEST_DB_PASSWORD', 'test_password'),
    'host': os.getenv('TEST_DB_HOST', 'localhost'),
}
```

### Linting and Type Safety

- **ruff**: Linting and formatting (replaces flake8, pylint, black)
- **mypy**: Static type checking with `check_untyped_defs = true`
- Run both with `make lint && make typecheck`

## Data Leakage Prevention

### Z-Score Calculation

Excludes the current transaction using `shift(1)` and sample std (`ddof=1`):

```python
def _compute_user_amount_zscore(df, user_col, amount_col, pos_col="__pos__"):
    z = np.full(len(df), np.nan)
    grouped = df.groupby(user_col)[[amount_col, pos_col]]
    for _, group in grouped:
        amounts = group[amount_col]
        positions = group[pos_col].values.astype(int)
        mean = amounts.expanding().mean().shift(1)
        std = amounts.expanding().std(ddof=1).shift(1)
        valid = (std > 0) & std.notna()
        z[positions[valid.values]] = (
            (amounts.values - mean.values) / std.values
        )[valid.values]
    return z
```

### Rolling Window Aggregations

All rolling windows use `closed="left"` and position-based result mapping:

```python
def _rolling_group_agg(df, group_col, value_col, window, agg, pos_col="__pos__"):
    result = np.empty(len(df), dtype=float)
    grouped = df.groupby(group_col)[[value_col, pos_col]]
    for _, group in grouped:
        rolled = group[value_col].rolling(window, closed="left").agg(agg)
        positions = group[pos_col].values.astype(int)
        result[positions] = rolled.values
    return result
```

### Time-Based Splitting

When temporal features exist, data is split chronologically:

```python
working_data = working_data.sort_values(time_column)
split_index = max(1, int(len(working_data) * (1 - test_size)))
train_df = working_data.iloc[:split_index]
test_df = working_data.iloc[split_index:]
```

### Duplicate Index Handling

The feature engine uses integer position columns (`__pos__`) to map groupby results back to the correct rows. This prevents alignment errors when the DatetimeIndex has duplicate timestamps (common with 5000+ transactions over a 60-day window).

## C++ Module Safety

### Bounds Checking

All array accesses validate indices before use. NULL pointer checks on all C API entry points.

### Buffer Overflow Prevention

Data cleaning tracks size changes after NaN removal and pads remaining slots:

```cpp
size_t cleaned_size = data_vec.size();
for (size_t i = 0; i < cleaned_size; ++i) data[i] = data_vec[i];
for (size_t i = cleaned_size; i < total; ++i) data[i] = std::numeric_limits<double>::quiet_NaN();
```

### Sample Standard Deviation

C++ modules use sample std (`n-1`) for unbiased estimates:

```cpp
return std::sqrt(sq_sum / (data.size() - 1));
```

---
