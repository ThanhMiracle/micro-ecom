import importlib
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="session")
def test_engine():
    return create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        future=True,
    )


@pytest.fixture()
def app_and_db(monkeypatch, test_engine):
    # Keep tests deterministic
    monkeypatch.setenv("PRODUCT_URL_INTERNAL", "http://product-service:8000")
    monkeypatch.delenv("RABBITMQ_URL", raising=False)

    import order_service.main as main
    import order_service.db as dbmod

    importlib.reload(dbmod)
    importlib.reload(main)

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
        future=True,
    )

    monkeypatch.setattr(dbmod, "engine", test_engine, raising=True)
    monkeypatch.setattr(dbmod, "SessionLocal", TestingSessionLocal, raising=True)

    dbmod.Base.metadata.create_all(bind=test_engine)

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