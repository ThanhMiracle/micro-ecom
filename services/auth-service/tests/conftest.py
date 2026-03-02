import os
import importlib
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="session")
def jwt_secret():
    return "test-jwt-secret"


@pytest.fixture(scope="session")
def test_engine():
    # In-memory sqlite shared across connections for the lifetime of the engine
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )
    return engine


@pytest.fixture()
def app_and_db(monkeypatch, jwt_secret, test_engine):
    """
    Imports auth_service.main AFTER setting env var JWT_SECRET
    because main.py reads JWT_SECRET at import time.
    """
    monkeypatch.setenv("JWT_SECRET", jwt_secret)
    monkeypatch.delenv("RABBITMQ_URL", raising=False)
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://localhost:3000")

    # Import after env setup
    import auth_service.main as main
    import auth_service.db as dbmod

    # Patch the service's engine + SessionLocal to use our test engine
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
        future=True,
    )

    monkeypatch.setattr(dbmod, "engine", test_engine, raising=True)
    monkeypatch.setattr(dbmod, "SessionLocal", TestingSessionLocal, raising=True)

    # Create tables using the service Base
    dbmod.Base.metadata.create_all(bind=test_engine)

    # Override FastAPI dependency get_db
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[main.get_db] = override_get_db

    # Give back module refs so tests can monkeypatch functions inside main
    return main, dbmod, TestingSessionLocal


@pytest.fixture()
def client(app_and_db):
    main, _, _ = app_and_db
    with TestClient(main.app) as c:
        yield c
    main.app.dependency_overrides = {}