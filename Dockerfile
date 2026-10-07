# FraudShield — multi-stage build: compile the C++ extensions in a builder,
# then ship only the resolved virtualenv in a slim runtime image.
FROM python:3.10-slim AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Compiler toolchain for the pybind11 extensions and any source-only wheels.
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential cmake && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md CMakeLists.txt ./
COPY src/ src/

# Non-editable so the built package and its .so files live inside .venv and can be copied alone.
RUN uv sync --no-dev --no-editable --locked


FROM python:3.10-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# libgomp1 backs the OpenMP loops in scikit-learn/XGBoost, libstdc++6 the compiled extensions.
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 libstdc++6 && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --system fraudshield && useradd --system --gid fraudshield --create-home fraudshield

COPY --from=builder /app/.venv /app/.venv

# Model artifacts, preprocessor, and metadata served by the inference API.
COPY data/ data/

RUN chown -R fraudshield:fraudshield /app
USER fraudshield

# FastAPI inference API; Prometheus metrics are mounted at /metrics on the same port.
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

ENTRYPOINT ["uvicorn", "fraudshield.ml.inference.api:app", "--host", "0.0.0.0", "--port", "8000"]
