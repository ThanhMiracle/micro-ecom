import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture(scope="session")
def test_engine():
    return create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # IMPORTANT for sqlite :memory:
        future=True,
    )


@pytest.fixture()
def local_app_and_db(monkeypatch, tmp_path, test_engine):
    """
    Load product-service in LOCAL mode. Must set env before import because
    main.py validates UPLOAD_DIR at import time for local storage.
    """
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("FRONTEND_ORIGINS", "http://localhost:3000")

    # Optional S3 envs not needed in local mode
    monkeypatch.delenv("S3_BUCKET", raising=False)
    monkeypatch.delenv("PUBLIC_BASE_URL", raising=False)

    import product_service.main as main
    import product_service.db as dbmod

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
        future=True,
    )

    monkeypatch.setattr(dbmod, "engine", test_engine, raising=True)
    monkeypatch.setattr(dbmod, "SessionLocal", TestingSessionLocal, raising=True)

    # Create tables for tests
    dbmod.Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[main.get_db] = override_get_db

    # Default auth user
    main.app.dependency_overrides[main.require_user] = lambda: {
        "sub": "1",
        "email": "u1@example.com",
        "is_admin": True,
    }

    # Make require_admin deterministic for tests
    def fake_require_admin(claims: dict):
        if not claims.get("is_admin"):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Admin required")

    monkeypatch.setattr(main, "require_admin", fake_require_admin, raising=True)

    return main, dbmod, TestingSessionLocal


@pytest.fixture()
def local_client(local_app_and_db):
    main, _, _ = local_app_and_db
    with TestClient(main.app) as c:
        yield c
    main.app.dependency_overrides = {}