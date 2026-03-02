import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Safe default so unit tests don't crash if env not set
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
DB_SCHEMA = os.getenv("DB_SCHEMA", "orders")

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
        - Set search_path

    SQLite:
        - No schemas exist → do nothing
    """
    if _is_sqlite():
        return

    with engine.begin() as conn:
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {DB_SCHEMA}"))
        conn.execute(text(f"SET search_path TO {DB_SCHEMA}"))