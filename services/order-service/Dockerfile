# syntax=docker/dockerfile:1.6

############################
# 1) Builder: build wheels (no apt)
############################
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

COPY order-service/requirements.txt ./requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    set -eux; \
    pip install --upgrade pip setuptools wheel; \
    pip wheel --wheel-dir /wheels --prefer-binary -r ./requirements.txt


############################
# 1b) Builder-dev: wheels for dev/test deps
############################
FROM builder AS builder-dev

COPY order-service/requirements-dev.txt ./requirements-dev.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    set -eux; \
    pip wheel --wheel-dir /wheels-dev --prefer-binary -r ./requirements-dev.txt


############################
# 2) Test stage
############################
FROM python:3.11-slim AS test

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# Needed by your code path (safe defaults for tests)
ENV PRODUCT_URL_INTERNAL=http://product-service:8000

COPY --from=builder-dev /wheels-dev /wheels-dev
COPY order-service/requirements-dev.txt ./requirements-dev.txt

RUN set -eux; \
    pip install --no-index --find-links=/wheels-dev -r ./requirements-dev.txt; \
    rm -rf /wheels-dev

COPY order-service/app ./app
COPY order-service/tests ./tests
COPY shared ./shared

CMD ["pytest", "-q"]


############################
# 3) Runtime: minimal
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
COPY order-service/requirements.txt ./requirements.txt

RUN set -eux; \
    pip install --no-index --find-links=/wheels -r ./requirements.txt; \
    rm -rf /wheels

COPY order-service/app ./app
COPY shared ./shared

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]