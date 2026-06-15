.PHONY: help install build-cpp test test-python test-cpp clean lint typecheck format

help:
	@echo "FraudShield - Makefile Commands"
	@echo "================================"
	@echo "install       - Install Python dependencies"
	@echo "build-cpp     - Build C++ extensions with pybind11"
	@echo "test          - Run all tests (Python + C++)"
	@echo "test-python   - Run Python unit and integration tests"
	@echo "test-cpp      - Run C++ module tests"
	@echo "clean         - Remove build artifacts and cache files"
	@echo "lint          - Run ruff linting"
	@echo "typecheck     - Run mypy type checking"
	@echo "format        - Format code with ruff"

install:
	@echo "Installing dependencies..."
	uv pip install -r requirements.txt
	uv pip install -e .

build-cpp:
	@echo "Building C++ extensions..."
	uv pip install -e .
	@echo "C++ modules built successfully!"

test: test-python test-cpp
	@echo "All tests completed!"

test-python:
	@echo "Running Python tests..."
	uv run pytest tests/unit_tests/ -v
	uv run pytest tests/integration_tests/ -v

test-realtime:
	@echo "Running Real-Time Architecture tests..."
	uv run pytest tests/unit_tests/test_realtime_architecture.py -v

test-cpp:
	@echo "Testing C++ module integration..."
	uv run python -c "from fraudshield.feature_engineering import cpp_wrapper; print('Feature engineering:', cpp_wrapper.is_cpp_available())"
	uv run python -c "from fraudshield.data_cleaning import cpp_wrapper; print('Data cleaning:', cpp_wrapper.is_cpp_available())"

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
	uv run ruff check src tests

typecheck:
	@echo "Running mypy type checking..."
	uv run mypy src/

format:
	@echo "Formatting code with ruff..."
	uv run ruff format src tests
	@echo "Format complete!"
