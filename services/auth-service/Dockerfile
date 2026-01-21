# syntax=docker/dockerfile:1.6

FROM python:3.11-slim AS runtime

# Sensible defaults for containers
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# (Optional but common) system deps for building wheels; remove if you know you don't need them.
# If your requirements are pure-python, you can delete this whole RUN.
RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better layer caching
COPY auth-service/requirements.txt /app/requirements.txt

# Use BuildKit cache for pip to speed up rebuilds
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /app/requirements.txt

# Copy code last (so code changes don't invalidate dependency layer)
COPY auth-service/app /app/app
COPY shared /app/shared

EXPOSE 8000

# If you run behind a reverse proxy, these flags help with real client IPs:
# --proxy-headers --forwarded-allow-ips="*"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
