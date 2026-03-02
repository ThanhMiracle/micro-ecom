# syntax=docker/dockerfile:1.6

############################
# 1) Builder: wheels for runtime deps
############################
FROM python:3.11-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

COPY product-service/requirements.txt ./requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    set -eux; \
    pip install --upgrade pip setuptools wheel; \
    pip wheel --wheel-dir /wheels --prefer-binary -r ./requirements.txt


############################
# 1b) Builder-dev: wheels for test deps
############################
FROM builder AS builder-dev

COPY product-service/requirements.txt ./requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    set -eux; \
    pip wheel --wheel-dir /wheels-dev --prefer-binary -r ./requirements.txt


############################
# 2) Test stage (LOCAL mode)
############################
FROM python:3.11-slim AS test
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    # product-service enforces these at import time in local mode
    STORAGE_BACKEND=local \
    UPLOAD_DIR=/tmp/uploads \
    FRONTEND_ORIGINS=http://localhost:3000

WORKDIR /app

COPY --from=builder-dev /wheels-dev /wheels-dev
COPY product-service/requirements.txt ./requirements.txt

RUN set -eux; \
    pip install --no-index --find-links=/wheels-dev -r ./requirements.txt; \
    rm -rf /wheels-dev

# Copy as proper Python package
COPY product-service/app ./product_service
COPY product-service/tests ./tests
COPY shared ./shared

# Ensure package marker exists
RUN test -f /app/product_service/__init__.py || touch /app/product_service/__init__.py

CMD ["pytest", "-q"]


############################
# 3) Runtime stage
############################
FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app
RUN useradd -m -u 10001 appuser

COPY --from=builder /wheels /wheels
COPY product-service/requirements.txt ./requirements.txt

RUN set -eux; \
    pip install --no-index --find-links=/wheels -r ./requirements.txt; \
    rm -rf /wheels

# Same layout as test stage
COPY product-service/app ./product_service
COPY shared ./shared

RUN test -f /app/product_service/__init__.py || touch /app/product_service/__init__.py

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()" || exit 1

CMD ["uvicorn", "product_service.main:app", "--host", "0.0.0.0", "--port", "8000"]