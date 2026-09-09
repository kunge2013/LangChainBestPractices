"""
Shared test fixtures.
"""
from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db
from app.main import app


@pytest.fixture(scope="function")
def db_engine():
    """Create a fresh in-memory SQLite engine per test.

    Uses a shared cache so that connections from different threads
    (e.g. TestClient) can see the same database.
    """
    engine = create_engine(
        "sqlite:///file::memory:?cache=shared&uri=true",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Provide a database session for testing."""
    TestingSessionLocal = sessionmaker(bind=db_engine, autocommit=False, autoflush=False)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provide a FastAPI test client with overridden DB dependency."""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    # Use TestClient without context manager to avoid lifespan creating
    # tables on the production engine
    c = TestClient(app)
    yield c
    app.dependency_overrides.clear()
