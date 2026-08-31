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

Credentials are loaded from environment variables and required for non-local services; Docker Compose consumes values from an untracked `.env` file:

```python
db_config = {
    'user': os.environ['FRAUDSHIELD_DB_USER'],
    'password': os.environ['FRAUDSHIELD_DB_PASSWORD'],
    'host': os.environ['FRAUDSHIELD_DB_HOST'],
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

### Delayed Fraud Labels

The API and streaming feature store never accept a caller-supplied `fraud` or
`known_fraud` value. Confirmed labels arrive after authorization, so using one
as a live feature would both leak future information during training and let an
untrusted caller poison later merchant statistics. Label-derived merchant fraud
rates are excluded from the training and online feature sets until a trusted,
versioned delayed-label store is introduced.

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
