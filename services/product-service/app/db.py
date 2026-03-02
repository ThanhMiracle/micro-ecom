import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# In production: set DATABASE_URL to Postgres.
# In tests: fallback to sqlite in-memory.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
DB_SCHEMA = os.getenv("DB_SCHEMA", "product")

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


def _is_sqlite() -> bool:
    return engine.dialect.name == "sqlite"


def init_schema() -> None:
    """
    Postgres:
        - Create schema if not exists
        - Set search_path so tables live inside service schema

    SQLite:
        - No schema support -> no-op
    """
    if _is_sqlite():
        return

    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}"))
        conn.execute(text(f"SET search_path TO {DB_SCHEMA}"))


def set_search_path() -> None:
    """
    Optional helper if you ever need to reset search_path.
    SQLite: no-op.
    """
    if _is_sqlite():
        return

    with engine.begin() as conn:
        conn.execute(text(f"SET search_path TO {DB_SCHEMA}"))