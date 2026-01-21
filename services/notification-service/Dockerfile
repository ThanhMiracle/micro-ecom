# syntax=docker/dockerfile:1.6

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# (Optional) Only keep this if your deps need compiling (e.g., cryptography, numpy, pandas, psycopg2, etc.)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#       build-essential \
#     && rm -rf /var/lib/apt/lists/*

# Copy deps first for better layer caching
COPY notification-service/requirements.txt /app/requirements.txt

# Speed up rebuilds with BuildKit pip cache
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r /app/requirements.txt

# Copy code last
COPY notification-service/app /app/app
COPY shared /app/shared

EXPOSE 8000

# Consider adding: --proxy-headers --forwarded-allow-ips="*"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
