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
    PYTHONPATH=/app

WORKDIR /app

# ✅ product-service enforces UPLOAD_DIR at import time in local mode
ENV STORAGE_BACKEND=local
ENV UPLOAD_DIR=/tmp/uploads
# optional, but keeps CORS config deterministic
ENV FRONTEND_ORIGINS=http://localhost:3000

COPY --from=builder-dev /wheels-dev /wheels-dev
COPY product-service/requirements.txt ./requirements.txt

RUN set -eux; \
    pip install --no-index --find-links=/wheels-dev -r ./requirements.txt; \
    rm -rf /wheels-dev

COPY product-service/app ./app
COPY product-service/tests ./tests
COPY shared ./shared

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

COPY product-service/app ./app
COPY shared ./shared

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]