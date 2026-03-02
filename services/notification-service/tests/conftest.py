import importlib
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def svc(monkeypatch):
    """
    Import notification-service AFTER setting RABBITMQ_URL because module
    reads it at import time.
    """
    monkeypatch.setenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

    # Adjust this import path to your real package name.
    # Example if your file is: notification_service/main.py
    import notification_service.main as main
    importlib.reload(main)

    return main


@pytest.fixture()
def client(svc):
    with TestClient(svc.app) as c:
        yield c