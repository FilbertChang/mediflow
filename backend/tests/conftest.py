"""
Shared pytest fixtures for the MediFlow backend test suite.

Tests run fully offline: the database is in-memory SQLite (no PostgreSQL),
and every LLM / vector-store call is mocked in the individual test modules
(no Ollama). The rate limiter is disabled for deterministic runs.
"""
import os
import sys

# `app` must be importable, and the environment must be set BEFORE the app is
# imported — app.database builds its engine from DATABASE_URL at import time.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-production"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.auth import create_access_token, hash_password
from app.limiter import limiter
from app.models.models import User

limiter.enabled = False

# StaticPool + a single in-memory connection so every session in a test shares
# the same database, including requests served on the TestClient worker thread.
_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


@pytest.fixture()
def db_session():
    """A fresh, isolated database for each test."""
    Base.metadata.create_all(bind=_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=_engine)


@pytest.fixture()
def client(db_session):
    """TestClient with the DB dependency pointed at the test session."""
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _seed_user(db_session, username, role):
    user = User(
        username=username,
        hashed_password=hash_password("Password123"),
        full_name=username.capitalize(),
        role=role,
        is_active=1,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture()
def admin_user(db_session):
    return _seed_user(db_session, "admin", "admin")


@pytest.fixture()
def doctor_user(db_session):
    return _seed_user(db_session, "doctor", "doctor")


@pytest.fixture()
def nurse_user(db_session):
    return _seed_user(db_session, "nurse", "nurse")


@pytest.fixture()
def auth_header():
    """Returns a helper that builds a Bearer header for a given username."""
    def _make(username):
        return {"Authorization": f"Bearer {create_access_token({'sub': username})}"}
    return _make
