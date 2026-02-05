# syntax=docker/dockerfile:1.6

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install OS deps ONLY if your requirements need compilation
# (uncomment if you see pip building wheels / gcc errors)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#       build-essential \
#     && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY auth-service/requirements.txt /app/requirements.txt

# Faster rebuilds with BuildKit cache + modern pip tooling
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip setuptools wheel && \
    pip install -r /app/requirements.txt

# Copy app code last
COPY auth-service/app /app/app
COPY shared /app/shared

# Run as non-root
RUN useradd -m -u 10001 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Optional: remove if you don't have /health
HEALTHCHECK --interval=10s --timeout=3s --retries=10 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
