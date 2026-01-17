FROM python:3.11-slim

WORKDIR /app

COPY order-service/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY order-service/app ./app
COPY shared ./shared

ENV PYTHONPATH=/app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
