# syntax=docker/dockerfile:1.6

############################
# 1) Builder Stage (wheels)
############################
FROM python:3.11-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

COPY auth-service/requirements.txt ./requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    set -eux; \
    pip install --upgrade pip setuptools wheel; \
    pip wheel --wheel-dir /wheels --prefer-binary -r ./requirements.txt


############################
# 1b) Builder stage for dev/test wheels
############################
FROM builder AS builder-dev

COPY auth-service/requirements.txt ./requirements.txt

RUN --mount=type=cache,target=/root/.cache/pip \
    set -eux; \
    pip wheel --wheel-dir /wheels-dev --prefer-binary -r ./requirements.txt


############################
# 2) Test Stage
############################
FROM python:3.11-slim AS test

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY --from=builder-dev /wheels-dev /wheels-dev
COPY auth-service/requirements.txt ./requirements.txt

RUN set -eux; \
    pip install --no-index --find-links=/wheels-dev -r ./requirements.txt; \
    rm -rf /wheels-dev

# Copy service code as a proper package: /app/auth_service
COPY auth-service/app ./auth_service
COPY auth-service/tests ./tests
COPY shared ./shared

# Ensure package marker exists
RUN test -f /app/auth_service/__init__.py || touch /app/auth_service/__init__.py

CMD ["pytest", "-q"]


############################
# 3) Runtime Stage
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
COPY auth-service/requirements.txt ./requirements.txt

RUN set -eux; \
    pip install --no-index --find-links=/wheels -r ./requirements.txt; \
    rm -rf /wheels

# Copy runtime code the SAME way as tests: /app/auth_service
COPY auth-service/app ./auth_service
COPY shared ./shared

# Ensure package marker exists
RUN test -f /app/auth_service/__init__.py || touch /app/auth_service/__init__.py

RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()" || exit 1

# Run the real module path
CMD ["uvicorn", "auth_service.main:app", "--host", "0.0.0.0", "--port", "8000"]