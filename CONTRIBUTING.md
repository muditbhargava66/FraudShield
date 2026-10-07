# Contributing to FraudShield

Thanks for helping improve FraudShield. This guide covers the repo layout, local setup, and what we expect in PRs.

## Repo Layout

- Python package: `src/fraudshield/`
- Python tests: `tests/`
- C++ extension equivalence tests: `tests/unit_tests/test_cpp_extensions.py`
- GoogleTest sources: `tests/cpp/` (not wired into any CMake target; nothing compiles or runs them)
- Airflow DAGs: `src/fraudshield/data_pipeline/airflow_dags/`
- Sample data + generator: `data/raw/synthetic_fraud_data.py`, `data/raw/synthetic_fraud_data.csv`

## Local Setup

Option A (recommended): `uv`

```bash
uv sync
uv run pytest -q
```

Option B: `pip`

```bash
python -m pip install -e .
pytest -q
```

## Running Checks

- Unit + integration tests: `pytest tests/ -q` (124 passed, 1 skipped; the skip is the live-PostgreSQL integration test)
- C++ extension vs. Python fallback equivalence: `make test-cpp`
- Lint (Python): `ruff check src tests scripts`, or `make lint`
- Type check: `mypy src/`, or `make typecheck`
- Format: `ruff format src tests scripts`, or `make format`
- Component verification harness (43 checks): `make verify`
- Dependency audit: `make audit`
- Packaging sanity: `python -m build`

The lint scope is `src tests scripts` in the Makefile, `tox.ini`, and CI alike. CI runs on `ubuntu-24.04` with Python 3.10 only; `tox` covers 3.10-3.13.

## Adding Features (Feature Engineering)

If you touch transaction feature engineering (`src/fraudshield/feature_engineering/transaction_features.py`):

- Avoid leakage: rolling features should only use past events (`closed="left"` windows).
- Add or adjust tests in `tests/unit_tests/test_transaction_features.py`.
- Keep new features robust to missing optional columns (currency/status/etc.).

## Config & Secrets

Do not commit secrets.

- `conf/database.ini` is a template and should not contain real credentials.
- Prefer environment variables or a local override file (example: `conf/database.local.ini`).

## Pull Request Checklist

- Tests are added or updated and passing locally (or in CI).
- Imports use `fraudshield.*` (no `src.*` imports).
- New files are placed in the right package or `tests/` folder.
- Docs updated if behavior or CLI changes (`README.md`, `docs/`).

## Contact

Open an issue or a PR on GitHub. For private questions, contact `muditbhargava666@gmail.com`.

