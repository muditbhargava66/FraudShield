# Changelog

All notable changes to FraudShield are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.3.0] - 2026-06-15

### Added
- Native Data Drift Validation task (KS test) inserted into the Airflow DAG to catch distributional shifts.
- Shared runtime settings and resource factories for SQL, Kafka, Neo4j, Airflow, and model artifacts.
- Inference service that loads trained model, preprocessor, and preprocessing metadata together.
- Stateful streaming aggregates for rolling counts, sums, means, fraud rates, and user-level running statistics.
- Idempotent Neo4j graph persistence with `MERGE`-based writes.
- Startup smoke tests for the API, Airflow DAG import, and inference artifact loading.
- FastAPI inference API with `/predict` and `/health` endpoints.
- Real-time orchestrator combining Kafka streaming, ML inference, Neo4j graph risk, and hybrid risk scoring.
- Centralized runtime logging with rotating file handlers.
- Ruff configuration in `pyproject.toml` and a `ruff` environment in `tox.ini`.
- mypy type checking in `pyproject.toml`, `tox.ini`, CI pipeline, and `Makefile`.
- `MANIFEST.in` for proper source distribution packaging.
- `SECURITY.md` with vulnerability reporting guidelines and supported versions.
- `CODE_OF_CONDUCT.md` using the Contributor Covenant v2.1.
- Synthetic data generator improvements: 5,000 transactions, 15 fraudster users, 8 high-risk merchants, multi-factor fraud patterns.
- `is_international` and `is_online` columns to the transactions schema and synthetic data.
- `pytest.ini` markers for `slow`, `integration`, and `smoke` test categories.

### Changed
- Moved `apache-airflow` from hard dependency to optional extra (`pip install fraudshield[airflow]`).
- Moved `pytest` from core dependencies to `[dev]` optional extra.
- Replaced Flake8, Pylint, and Black with Ruff for linting and formatting.
- Fixed PyPI classifier from `Build Tools` to `Scientific/Engineering :: Artificial Intelligence`.
- Changed development status from `Production/Stable` to `Beta`.
- Airflow DAG task wiring defers variable resolution to execution time via zero-arg callables.
- Model deployment task validates inference artifacts instead of being a placeholder.
- C++ data preprocessing now uses cleaned array min/max for outlier bounds instead of recomputing from scratch.
- C++ feature engineering module documented as experimental (not used in default pipeline).
- CI lint job uses Ruff and mypy instead of Flake8/Pylint with `|| true` silencing.
- CI deploy job uses twine upload instead of a comment placeholder.
- Rewrote all 8 docs files (`quick_start.md`, `setup_instructions.md`, `model_architecture.md`, `security_and_quality.md`, `cpp_modules.md`, `data_dictionary.md`, `migration_guide.md`, `sql_schema.md`).
- Updated `README.md` model evaluation metrics with actual results from 5,000-sample dataset.
- Re-executed all 3 notebooks (`01_fraudshield_pipeline_tutorial.ipynb`, `exploratory_data_analysis.ipynb`, `model_experimentation.ipynb`) with fresh outputs, fixed kernel specs (Python 3), and added cell IDs for nbformat compliance.
- EDA notebook: added explicit `fillna(0.0)` for cross-version pandas compatibility, displays mid-dataset rows where features are populated, added NaN behavior explanation.
- Model experimentation notebook: added `warnings.filterwarnings` to suppress sklearn `InconsistentVersionWarning` when loading preprocessor pickled in a different environment, added retrain note for inference demo.

### Fixed
- API model loading so the FastAPI surface initializes correctly against saved model files.
- Small-dataset preprocessing so stratified splits degrade gracefully instead of raising `ValueError`.
- Package version aligned across Python package, API version, and project metadata.
- Optional dependency handling so tests skip automatically when Airflow or SQLAlchemy are unavailable.
- mypy type errors across 10 source files (Dict return types, optional import guards, None checks).
- **Critical**: `transaction_features.py` duplicate-index bug — `groupby().apply().reset_index()` failed with `ValueError: cannot reindex on an axis with duplicate labels` when DatetimeIndex had repeated timestamps. Rewrote `_rolling_group_agg` and `_compute_user_amount_zscore` to use integer position columns (`__pos__`) instead of index alignment.

### Security
- Pinned 10 vulnerable transitive dependencies via `[tool.uv] override-dependencies`.
- Upgraded `apache-airflow` to `>=3.2.2`, `fastapi` to `>=0.136.0`, `pytest` to `>=9.0.3`.

---

## [2.2.0] - 2026-04-18

### Security
- Updated `apache-airflow` from `>=3.1.7` to `>=3.2.0` to address CVE-2025-57735, CVE-2026-33858, and CVE-2025-54550.
- Regenerated lock file with `uv lock --upgrade` to update transitive dependencies.

---

## [2.1.0] - 2026-03-14

### Changed
- Rebuilt notebooks around the current runtime/config architecture.
- Simplified `.gitignore` to focus on generated artifacts and local secrets.
- Hardened `CMakeLists.txt` with explicit C++ standard, reusable extension helper, and consistent compiler warnings.

### Fixed
- Removed import-time `logging.basicConfig(...)` calls that caused handler duplication.
- Standardized CLI and service entrypoints so logs land in predictable per-component files under `logs/`.

---

## [2.0.0] - 2026-02-21

### Added
- Initial batch pipeline for ingestion, preprocessing, training, and evaluation.
- C++ acceleration hooks for data cleaning and feature engineering via pybind11.
- Tox-based multi-version test execution and local build automation.
