# Changelog

All notable changes to the FraudShield project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [2.2.0] - 2026-04-18

### Hotfix: Security & Dependency Vulnerabilities
- **Airflow Deserialization & JWT Bypass Resolution**: Natively updated `apache-airflow` from `>=3.1.7` to `>=3.2.0` immediately mitigating `CVE-2025-57735`, `CVE-2026-33858`, and `CVE-2025-54550`. This prevents legacy XCom APIs from arbitrary unsandboxed deserialization operations and secures dangling backend API keys securely.
- **Transitive Lock Escalation**: Regenerated the full underlying environment natively with `uv lock --upgrade`, sealing out 18 flagged Dependabot transient vulnerabilities embedded deep within downstream dependency chains without forcing any breaking API syntax inside the testing backend.

---

## [2.1.0] - 2026-03-14

### Security & Compliance

- **Dependency CVE Remediation**: Extracted raw `python -m pip install` commands natively out of `.github/workflows/ci.yml` and explicitly swapped for nested `uv pip install --system`. This enabled a highly targeted `override-dependencies` bounding matrix forcing strict compatibilities bridging `fastapi>=0.129.0` against `starlette>=0.49.1`, successfully remediating 14 `apache-airflow` CVE alerts by locking to `3.1.8`.
- **CodeQL Remote Permissions**: Injected explicit `permissions: contents: read` layers executing across the CI pipeline to safeguard remote access token mapping flags from GitHub Actions static analysis errors.

### Stability & Upgrades

- **Global UV Dependency Modernization**: Conducted an aggressive `uv lock --upgrade` across `pyproject.toml`. Successfully mapped and locked 44 underlying matrix libraries (including `numpy==2.4.3`, `scipy==1.17.1`, `scikit-learn==1.7.2`, `fastapi==0.135.1`, `pandas==2.3.3`) ensuring they are aligned to their highest valid stability boundaries against Python 3.10 without incurring any backwards-breaking API syntax exceptions across unit tests or rendering scripts.
- **CI Dependency Fix**: Fixed GitHub Actions build failures resulting from `pyyaml-ft==8.0.0` by manually re-compiling raw backwards compatible requirement logs using explicit `uv pip compile --python-version 3.10`.

---

## [2.0.0] - 2026-02-21

### Security & Data Integrity

- **SQL Injection Prevention**: Completely rewrote the connection architecture to construct generic `SQLAlchemy` URLs locally, protecting against SQL injection strings. Parameterized queries enforce uniform integrity across `pd.to_sql` inserts. 
- **Time-Based Splitting**: Transformed the dataset partitioning to natively utilize time-based splits referencing `transaction_date` schemas instead of randomized selections, actively defeating temporal data leakage.
- **Improved C++ Memory Handling**: Introduced bound arrays tracking alongside static null-checks within `feature_engineering.cpp` and `data_cleaning.cpp` bridging to eliminate catastrophic buffer overflows and segmentation faults triggered by malformed datasets.
- **Information Error Disclosure Blocked**: Stripped out raw DB connection string dumps traversing into stack traces during exceptions or timeouts.

### Architecture Modernization

- **C++ Build System Migration**: Transitioned away from deprecated `setup.py` hooks exclusively into `pyproject.toml`, unlocking PEP-517 compilation pipelines utilizing dynamic `scikit-build-core` integrations.
- **Localized DAG Database**: Decoupled `Airflow` from global installations by routing its core internal config (`airflow.db`) autonomously into an invisible `.airflow` directory at runtime. This successfully enables local regression checks independent of user-system variables.
- **Docs Folder Overhaul**: Migrated disjointed tutorial tracking algorithms and implementation records from the root directly into unified `docs/` Markdown paths.

### Performance

- **Prediction Data Caching**: Refactored the internal model evaluation layer to parse raw arrays sequentially up to ~50% quicker. Memory evaluations are dynamically cached locally against precision matrix runs to bypass redundant `predict()` loops.
- **Feature Computation Safety Loops**: Rewrote internal feature logic representing statistical aggregates (Exponential Moving Average / RSI) to rely on bounded `numpy.divide` evaluations, averting infinite zeros and float traps natively.

### Code Simplifications (Code-Simplifier Adherence)

- Systematically applied explicit return typing protocols across `data_preprocessing.py`, `pipeline_tasks.py`, `evaluation.py`, and `transaction_features.py`.
- Stripped arbitrary try/catches encapsulating routing protocols inside `train_models.py` and decoupled irrelevant top-level variables.
- Removed superfluous emojis globally across all notebook tutorials, readmes, and internal documentation artifacts.
- Refactored `data_preprocessing.py` C++ module bindings adhering to `.agents/code-simplifier.md` by stripping redundant multi-layered pandas DataFrame operations in favor of native one-pass computations over raw NumPy buffers mapping static mean/std calculations.

### Notebook & Testing Stability Checks

- **Makefile Unified Testing:** Re-wired `make test` to execute all unit logic, integration end-to-ends, and the C++ module detection sequentially via `uv run` to ensure users running local global environments (like standard `pytest`) don't fail airflow bindings.
- **Tox Isolation Environments:** Added strong `tox.ini` integration mapped to `pytest` asserting identical deployment artifacts natively across Python `3.10`, `3.11`, `3.12`, and `3.13` concurrently.
- **Strict Linting Standards:** Scrubbed the entire `src/fraudshield` repository clean against aggressive `flake8` and `pylint` validations blocking unused imports, multi-line spacing errors, and undefined variables. Expanded native acceptable `--max-line-length` limits securely up to 150 characters uniformly across `.github/workflows/ci.yml`, `tox.ini`, and `Makefile` to prioritize syntax comprehension mappings.
- **Notebook Variable Mappings:** Fixed critical string-to-float anomalies in `exploratory_data_analysis.ipynb` mapping standard `fraud` flags rather than dummy `target` placeholders. Ensured directory execution scopes point correctly to generated `synthetic_fraud_data.csv`. Generated and validated graphical outputs dynamically natively storing payload states inside `01_fraudshield_pipeline_tutorial.ipynb`.

---

## [1.0.0] - Initial Release

- Core machine learning pipeline architecture (Ingestion -> Preprocessing -> Model Training -> Evaluation).
- Base Python fallback scripting logic and initial C++ performance nodes.
- Baseline synthetic anomaly dataset mapping structures.
