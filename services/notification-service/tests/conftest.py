import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def svc(monkeypatch):
    """
    Import notification-service AFTER setting env vars because module
    reads them at import time.
    """
    monkeypatch.setenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")

    import notification_service.main as main
    main = importlib.reload(main)   
    return main


@pytest.fixture()
def client(svc):
    with TestClient(svc.app) as c:
        yield c
    svc.app.dependency_overrides = {}