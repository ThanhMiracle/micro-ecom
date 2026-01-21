# syntax=docker/dockerfile:1.6

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# (Optional) Only enable if requirements include native builds (cryptography/numpy/psycopg2/etc.)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#       build-essential \
#     && rm -rf /var/lib/apt/lists/*

# Copy deps first for better layer caching
COPY order-service/requirements.txt /app/requirements.txt

# Faster rebuilds with BuildKit pip cache
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /app/requirements.txt

# Copy code last
COPY order-service/app /app/app
COPY shared /app/shared

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
