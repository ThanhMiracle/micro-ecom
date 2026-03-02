import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Allow tests to run without DATABASE_URL by providing a safe default.
# In production you should set DATABASE_URL explicitly.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
DB_SCHEMA = os.getenv("DB_SCHEMA", "auth")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

class Base(DeclarativeBase):
    pass


def _supports_schemas() -> bool:
    # SQLite doesn't support CREATE SCHEMA or SET search_path
    return engine.dialect.name not in ("sqlite",)


def init_schema() -> None:
    """
    Initialize DB schema/search_path for DBs that support schemas (Postgres).
    SQLite: no-op (unit tests usually run on SQLite).
    """
    if not _supports_schemas():
        return

    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}"))
        conn.execute(text(f"SET search_path TO {DB_SCHEMA}"))


def set_search_path() -> None:
    """
    Set search_path for Postgres connections.
    SQLite: no-op.
    """
    if not _supports_schemas():
        return

    with engine.begin() as conn:
        conn.execute(text(f"SET search_path TO {DB_SCHEMA}"))