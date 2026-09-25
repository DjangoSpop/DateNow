"""
Test configuration.

Runs against a real PostgreSQL database (TEST_DATABASE_URL, default datenow_test). The schema is built
once per session with Alembic (downgrade base -> upgrade head); tables are truncated before each test.
"""
import os
from pathlib import Path

# Environment must be set before any `app.*` import (settings/engine are created at import time).
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://datenow:datenow@localhost:5432/datenow_test"
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["ENVIRONMENT"] = "testing"
os.environ.setdefault("JWT_SECRET_KEY", "test-only-jwt-secret-key-0123456789abcdef")
os.environ["GEMINI_API_KEY"] = ""  # never call the real AI provider from tests
os.environ["DEBUG"] = "false"

import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402

BACKEND_DIR = Path(__file__).resolve().parent.parent


def alembic_config() -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["url"] = TEST_DATABASE_URL
    cfg.attributes["configure_logger"] = False
    return cfg


@pytest.fixture(scope="session", autouse=True)
def migrated_database():
    cfg = alembic_config()
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def clean_state(migrated_database):
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))

    # In-memory live-session state is keyed by user id, which RESTART IDENTITY reuses.
    from app.conversation_session import session_manager
    from app.websocket_manager import manager

    session_manager.sessions.clear()
    session_manager.user_to_session.clear()
    manager.active_connections.clear()
    manager.session_participants.clear()
    manager.user_sessions.clear()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
