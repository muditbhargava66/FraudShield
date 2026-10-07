.PHONY: help install build-cpp test test-python test-cpp test-realtime verify audit clean lint typecheck format

help:
	@echo "FraudShield - Makefile Commands"
	@echo "================================"
	@echo "install       - Sync dependencies from uv.lock (all extras)"
	@echo "build-cpp     - Rebuild the pybind11 C++ extensions"
	@echo "test          - Run the full pytest suite (unit, integration, smoke)"
	@echo "test-python   - Run the full pytest suite"
	@echo "test-cpp      - Run the C++ extension vs fallback equivalence tests"
	@echo "test-realtime - Run the real-time architecture tests"
	@echo "verify        - Run the component verification harness"
	@echo "audit         - Run pip-audit against the locked all-extras export"
	@echo "clean         - Remove build artifacts and cache files"
	@echo "lint          - Run ruff linting (src, tests, scripts)"
	@echo "typecheck     - Run mypy type checking"
	@echo "format        - Format code with ruff"

install:
	@echo "Syncing dependencies from uv.lock..."
	uv sync --all-extras --locked

build-cpp:
	@echo "Rebuilding C++ extensions..."
	uv sync --all-extras --locked --reinstall-package fraudshield
	@echo "C++ modules built successfully!"

test: test-python
	@echo "All tests completed!"

test-python:
	@echo "Running Python tests..."
	uv run --all-extras pytest tests/ -q

test-cpp:
	@echo "Running C++ extension tests..."
	uv run --all-extras pytest tests/unit_tests/test_cpp_extensions.py -q

test-realtime:
	@echo "Running Real-Time Architecture tests..."
	uv run --all-extras pytest tests/unit_tests/test_realtime_architecture.py -v

verify:
	@echo "Running component verification harness..."
	uv run --all-extras python scripts/verify_v3_components.py

audit:
	@echo "Auditing locked dependencies..."
	uv export --all-extras --no-dev --no-emit-project --no-hashes --locked --output-file /tmp/fraudshield-audit-requirements.txt
	uvx pip-audit --no-deps --disable-pip -r /tmp/fraudshield-audit-requirements.txt --strict

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/*.egg-info
	find src tests -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find src tests -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find src tests -type f -name "*.pyc" -delete
	find src tests -type f -name "*.so" -delete
	find src tests -type f -name "*.o" -delete
	@echo "Clean complete!"

lint:
	@echo "Running ruff linting..."
	uv run --all-extras ruff check src tests scripts

typecheck:
	@echo "Running mypy type checking..."
	uv run --all-extras mypy src/

format:
	@echo "Formatting code with ruff..."
	uv run --all-extras ruff format src tests scripts
	@echo "Format complete!"
