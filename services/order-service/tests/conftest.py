import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture(scope="session")
def test_engine():
    # Shared in-memory SQLite DB across all connections (no flaky missing tables)
    return create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # IMPORTANT for sqlite :memory:
        future=True,
    )


@pytest.fixture()
def app_and_db(monkeypatch, test_engine):
    # Keep tests deterministic
    monkeypatch.setenv("PRODUCT_URL_INTERNAL", "http://product-service:8000")
    monkeypatch.delenv("RABBITMQ_URL", raising=False)

    # Import AFTER env setup
    import order_service.main as main
    import order_service.db as dbmod

    # Create a Session bound to the test engine
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
        future=True,
    )

    # Patch DB module to use test engine/session
    monkeypatch.setattr(dbmod, "engine", test_engine, raising=True)
    monkeypatch.setattr(dbmod, "SessionLocal", TestingSessionLocal, raising=True)

    # Create tables for tests
    dbmod.Base.metadata.create_all(bind=test_engine)

    # Override FastAPI dependencies
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[main.get_db] = override_get_db
    main.app.dependency_overrides[main.require_user] = lambda: {
        "sub": "1",
        "email": "u1@example.com",
    }

    return main, dbmod, TestingSessionLocal


@pytest.fixture()
def client(app_and_db):
    main, _, _ = app_and_db
    with TestClient(main.app) as c:
        yield c
    main.app.dependency_overrides = {}