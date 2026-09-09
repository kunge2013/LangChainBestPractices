"""
Database session and engine configuration.
Supports both SQLite (for testing) and MySQL/PostgreSQL (for production).
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import BigInteger, Integer, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.types import TypeDecorator

from app.config import settings


class BigInt(TypeDecorator):
    """BigInteger that auto-increments on SQLite (uses Integer variant)."""
    impl = BigInteger
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(Integer())
        return dialect.type_descriptor(BigInteger())


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""
    pass


def _make_engine():
    engine = create_engine(
        settings.database_url,
        echo=False,
        connect_args={"check_same_thread": False}
        if settings.is_sqlite
        else {},
    )
    # Enable foreign key enforcement for SQLite
    if settings.is_sqlite:
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _):  # noqa: ANN001
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()
    return engine


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency – yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context-manager version of ``get_db`` for use in services."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
