"""
Shared pytest fixtures.

The `client` fixture provides a TestClient backed by an in-memory SQLite DB.
FastAPI's dependency_overrides swaps the production get_db for the test one,
so route handlers see the isolated test database.
"""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_db
from app.main import app


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    """A fresh in-memory SQLite session for one test."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    """A TestClient wired up to the in-memory session above."""

    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()