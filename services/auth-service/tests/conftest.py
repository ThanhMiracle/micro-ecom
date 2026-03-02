# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture(scope="session")
def jwt_secret():
    return "test-jwt-secret"


@pytest.fixture(scope="session")
def test_engine():
    # In-memory sqlite shared across ALL connections for lifetime of engine
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # IMPORTANT for sqlite :memory: stability
        future=True,
    )
    return engine


@pytest.fixture()
def app_and_db(monkeypatch, jwt_secret, test_engine):
    """
    Import auth_service.main AFTER setting env vars because main.py reads them at import time.
    """

    # Set env expected by the app
    monkeypatch.setenv("JWT_SECRET", jwt_secret)
    monkeypatch.setenv("FRONTEND_BASE_URL", "http://localhost:3000")

    # Make sure these won't trigger behavior in startup/tests unless you want them
    monkeypatch.delenv("RABBITMQ_URL", raising=False)
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)

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

    # Recreate tables in the in-memory DB
    dbmod.Base.metadata.create_all(bind=test_engine)

    # Override FastAPI dependency get_db
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[main.get_db] = override_get_db

    return main, dbmod, TestingSessionLocal


@pytest.fixture()
def client(app_and_db):
    main, _, _ = app_and_db
    with TestClient(main.app) as c:
        yield c
    main.app.dependency_overrides = {}