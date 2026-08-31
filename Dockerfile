# FraudShield v3.0.0 — multi-stage build
FROM python:3.10-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install system deps required for numpy/scipy compilation and CMake
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential cmake && \
    rm -rf /var/lib/apt/lists/*

# Install uv for dependency resolution
RUN pip install --no-cache-dir uv

RUN groupadd --system fraudshield && useradd --system --gid fraudshield --create-home fraudshield

# Copy build manifests and source tree for dependency resolution
COPY pyproject.toml uv.lock README.md CMakeLists.txt ./
COPY src/ src/

# Create virtual environment and install dependencies (builds C++ extensions)
RUN uv sync --no-dev --frozen

# Copy data artifacts needed at runtime
COPY data/ data/

RUN chown -R fraudshield:fraudshield /app
USER fraudshield

# Expose FastAPI (8000) and Prometheus metrics (9090)
EXPOSE 8000 9090

# Default entrypoint: FastAPI inference server
ENTRYPOINT ["uv", "run", "uvicorn", "fraudshield.ml.inference.api:app", "--host", "0.0.0.0", "--port", "8000"]
