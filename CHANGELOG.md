# Changelog

All notable changes to FraudShield are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and the project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Centralized runtime logging with rotating file handlers, shared environment-driven settings, and deterministic entrypoint bootstrap.
- A reproducible notebook generator at `scripts/build_notebooks.py` for rebuilding the tutorial, EDA, and experimentation notebooks from structured source.
- Logging smoke coverage and notebook structure checks in the test suite.
- Ruff configuration in `pyproject.toml` and a dedicated `ruff` environment in `tox.ini`.

## [2.2.0] - 2026-04-18

### Hotfix: Security & Dependency Vulnerabilities
- **Airflow Deserialization & JWT Bypass Resolution**: Natively updated `apache-airflow` from `>=3.1.7` to `>=3.2.0` immediately mitigating `CVE-2025-57735`, `CVE-2026-33858`, and `CVE-2025-54550`. This prevents legacy XCom APIs from arbitrary unsandboxed deserialization operations and secures dangling backend API keys securely.
- **Transitive Lock Escalation**: Regenerated the full underlying environment natively with `uv lock --upgrade`, sealing out 18 flagged Dependabot transient vulnerabilities embedded deep within downstream dependency chains without forcing any breaking API syntax inside the testing backend.

---

## [2.1.0] - 2026-03-14

### Changed
- Rebuilt all three notebooks around the current runtime/config architecture so they demonstrate aligned ingestion, preprocessing, training, evaluation, and inference flows.
- Simplified `.gitignore` to focus on generated artifacts, local secrets, notebook/editor state, and build outputs.
- Hardened `CMakeLists.txt` with an explicit C++ standard, reusable extension helper, and consistent compiler warnings.

### Fixed
- Removed import-time `logging.basicConfig(...)` calls that caused handler duplication and order-dependent behavior.
- Standardized CLI and service entrypoints so logs now land in a predictable per-component file under `logs/`.

## [3.0.0] - 2026-03-18

### Added
- Shared runtime settings and resource factories for SQL, Kafka, Neo4j, Airflow, and model artifacts.
- An inference service that reloads the trained model, preprocessor, and preprocessing metadata together.
- Stateful streaming aggregates for rolling counts, sums, means, fraud rates, and user-level running statistics.
- Idempotent Neo4j graph persistence with `MERGE`-based writes.
- Startup smoke tests for the API, Airflow DAG import, realtime bootstrap, and inference artifact loading.

### Changed
- Airflow DAG loading and task wiring to better match the declared Airflow dependency set and defer variable resolution to execution time.
- Realtime orchestration to use shared settings, reusable resources, and aligned inference artifacts instead of mock-only paths.
- SQL configuration so ingestion, retrieval, and runtime services resolve database URLs from one source of truth.

### Fixed
- API model loading so the FastAPI surface can initialize correctly against saved model files.
- Small-dataset preprocessing so stratified splits gracefully degrade instead of raising `ValueError`.
- Package metadata drift by aligning the Python package version with the API version.
- Optional dependency handling in tests so module imports do not fail before mocks and skips can apply.

## [2.0.0] - 2026-02-21

### Added
- Initial batch pipeline for ingestion, preprocessing, training, and evaluation.
- Native C++ acceleration hooks for data cleaning and feature engineering.
- Tox-based multi-version test execution and local build automation.
