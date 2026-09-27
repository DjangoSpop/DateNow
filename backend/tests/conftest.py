"""
Shared pytest fixtures.

Database selection: ``TEST_DATABASE_URL`` (e.g.
``postgresql://postgres@127.0.0.1:5432/datenow_test``). Defaults to a SQLite
file in a temp directory so the suite runs without PostgreSQL.

The schema is built once per session with ``alembic upgrade head`` (never
``create_all``) and every DB-using test starts from empty tables.

Environment variables are set *before* the app is imported.
"""
import base64
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent

_default_sqlite = Path(tempfile.mkdtemp(prefix="datenow-test-")) / "test.db"
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_default_sqlite}"
TEST_JWT_SECRET = "test-secret-key-for-pytest-only-0123456789abcdef"

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["JWT_SECRET_KEY"] = TEST_JWT_SECRET
os.environ["ENVIRONMENT"] = "testing"
os.environ["AUTH_RATE_LIMIT_PER_MINUTE"] = "0"  # rate-limit tests enable it explicitly
os.environ["SQL_ECHO"] = "false"
os.environ.pop("GEMINI_API_KEY", None)

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from jose import jwt  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app import auth as auth_module  # noqa: E402
from app.config import settings  # noqa: E402
from app.database import Base, engine, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402

API = settings.API_V1_STR

# Fast bcrypt for tests only.
auth_module.pwd_context.update(bcrypt__rounds=4)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def alembic_config(url: str = TEST_DATABASE_URL) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    cfg.attributes["configure_logger"] = False
    return cfg


def _truncate_all() -> None:
    tables = [t.name for t in reversed(Base.metadata.sorted_tables)]
    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text(
                "TRUNCATE TABLE " + ", ".join(f'"{t}"' for t in tables) + " RESTART IDENTITY CASCADE"
            ))
        else:
            for t in tables:
                conn.execute(text(f'DELETE FROM "{t}"'))


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def db_schema():
    """Build the schema via Alembic once per test session."""
    cfg = alembic_config()
    command.downgrade(cfg, "base")  # clean slate if a previous run left state
    command.upgrade(cfg, "head")
    yield
    engine.dispose()


@pytest.fixture()
def clean_db(db_schema):
    _truncate_all()
    yield
    _truncate_all()


@pytest.fixture()
def db(clean_db):
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    auth_module.auth_rate_limiter.reset()
    yield
    auth_module.auth_rate_limiter.reset()


@pytest.fixture()
def client(clean_db):
    def _override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Users / tokens
# ---------------------------------------------------------------------------

DEFAULT_PASSWORD = "correct-horse-battery"


@pytest.fixture()
def make_user(db):
    counter = {"n": 0}

    def _make_user(email=None, password=DEFAULT_PASSWORD, is_active=True, **kwargs) -> User:
        counter["n"] += 1
        user = User(
            email=(email or f"user{counter['n']}@example.com").lower(),
            hashed_password=auth_module.get_password_hash(password),
            is_active=is_active,
            is_verified=False,
            first_name=kwargs.pop("first_name", f"User{counter['n']}"),
            last_name=kwargs.pop("last_name", "Test"),
            **kwargs,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make_user


@pytest.fixture()
def auth_headers():
    def _auth_headers(user_or_id) -> dict:
        user_id = getattr(user_or_id, "id", user_or_id)
        token = auth_module.create_access_token({"sub": user_id})
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers


def _b64(data: dict) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


@pytest.fixture()
def make_token():
    """Build arbitrary (possibly invalid) JWTs for negative tests.

    ``omit`` lists claims to drop; ``alg="none"`` builds an unsigned token.
    """
    _missing = object()

    def _make_token(
        sub=_missing,
        token_type="access",
        expires_in=timedelta(minutes=5),
        secret=TEST_JWT_SECRET,
        alg="HS256",
        omit=(),
        **extra,
    ) -> str:
        now = datetime.now(timezone.utc)
        claims = {
            "sub": "1" if sub is _missing else sub,
            "type": token_type,
            "iat": int(now.timestamp()),
            "exp": int((now + expires_in).timestamp()),
        }
        claims.update(extra)
        for key in omit:
            claims.pop(key, None)
        if alg == "none":
            return f"{_b64({'alg': 'none', 'typ': 'JWT'})}.{_b64(claims)}."
        return jwt.encode(claims, secret, algorithm=alg)

    return _make_token


@pytest.fixture()
def profile_payload():
    def _payload(**overrides) -> dict:
        payload = {
            "first_name": "Ada",
            "last_name": "Lovelace",
            "date_of_birth": "1995-04-12",
            "gender": "female",
            "bio": "Hello",
            "city": "London",
            "country": "UK",
            "height_cm": 170,
            "looking_for_gender": ["male"],
            "age_preference_min": 25,
            "age_preference_max": 35,
            "distance_preference_km": 50,
            "relationship_goal": "serious",
        }
        payload.update(overrides)
        return payload

    return _payload
