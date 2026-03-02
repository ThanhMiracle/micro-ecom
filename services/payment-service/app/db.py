import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

# In prod: set DATABASE_URL to Postgres.
# In tests: if DATABASE_URL isn't set, use sqlite memory.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
DB_SCHEMA = os.getenv("DB_SCHEMA", "payment")

engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

Base = declarative_base()


def _is_sqlite() -> bool:
    return engine.dialect.name == "sqlite"


def init_schema() -> None:
    """
    Postgres: create schema + set search_path (each service owns its schema).
    SQLite: no schemas/search_path -> no-op (unit tests).
    """
    if _is_sqlite():
        return

    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}"))
        conn.execute(text(f"SET search_path TO {DB_SCHEMA}"))


def set_search_path() -> None:
    """
    Useful if you want to call it per-connection in some flows.
    SQLite: no-op.
    """
    if _is_sqlite():
        return

    with engine.begin() as conn:
        conn.execute(text(f"SET search_path TO {DB_SCHEMA}"))