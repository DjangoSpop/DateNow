"""Configuration hardening and import-time behaviour."""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings

BACKEND_DIR = Path(__file__).resolve().parents[2]
STRONG = "k" * 48


def _settings(**overrides):
    base = {"DATABASE_URL": "sqlite://", "JWT_SECRET_KEY": STRONG, "ENVIRONMENT": "development"}
    base.update(overrides)
    return Settings(_env_file=None, **base)


def test_env_example_parses_and_is_rejected_in_production(monkeypatch):
    for var in ("JWT_SECRET_KEY", "DATABASE_URL", "ENVIRONMENT", "AUTH_RATE_LIMIT_PER_MINUTE", "SQL_ECHO"):
        monkeypatch.delenv(var, raising=False)
    s = Settings(_env_file=str(BACKEND_DIR / ".env.example"))
    assert s.GEMINI_API_KEY is None
    assert s.BACKEND_CORS_ORIGINS == ["http://localhost:3000", "http://localhost:8000"]
    with pytest.raises(ValidationError):
        Settings(_env_file=str(BACKEND_DIR / ".env.example"), ENVIRONMENT="production")


def test_gemini_key_optional():
    s = _settings()
    assert s.GEMINI_API_KEY is None and s.ai_enabled is False
    assert _settings(GEMINI_API_KEY="").GEMINI_API_KEY is None


def test_defaults():
    s = _settings()
    assert s.REDIS_URL == "redis://localhost:6379"
    assert s.DEBUG is False and s.SQL_ECHO is False


def test_jwt_secret_required(monkeypatch):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, DATABASE_URL="sqlite://")


@pytest.mark.parametrize("secret", [
    "your-secret-key-change-in-production",
    "your-super-secret-jwt-key-change-this-in-production",
    "short-secret",
    "CHANGE_ME_generate_a_long_random_secret",  # the .env.example placeholder
    "a-perfectly-long-placeholder-secret-value-0123456789",
    "x" * 31,
])
def test_production_rejects_weak_secrets(secret):
    with pytest.raises(ValidationError):
        _settings(ENVIRONMENT="production", JWT_SECRET_KEY=secret)


def test_production_accepts_strong_secret():
    assert _settings(ENVIRONMENT="production", JWT_SECRET_KEY=STRONG).is_production


def test_weak_secret_allowed_outside_production():
    assert _settings(JWT_SECRET_KEY="dev").JWT_SECRET_KEY == "dev"


@pytest.mark.parametrize("alg", ["HS512", "RS256", "none"])
def test_only_hs256_allowed(alg):
    with pytest.raises(ValidationError):
        _settings(JWT_ALGORITHM=alg)


def test_cors_wildcard_rejected():
    with pytest.raises(ValidationError):
        _settings(BACKEND_CORS_ORIGINS=["*"])
    with pytest.raises(ValidationError):
        _settings(BACKEND_CORS_ORIGINS="http://a.com, *")


def test_cors_comma_string_parsed():
    assert _settings(BACKEND_CORS_ORIGINS="http://a.com, http://b.com").BACKEND_CORS_ORIGINS == [
        "http://a.com", "http://b.com"
    ]


def _run(code: str, **env_overrides) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "GEMINI_API_KEY"}
    env.update({"DATABASE_URL": "sqlite://", "JWT_SECRET_KEY": STRONG, "ENVIRONMENT": "development"})
    env.update(env_overrides)
    return subprocess.run([sys.executable, "-c", code], cwd=BACKEND_DIR, env=env,
                          capture_output=True, text=True, timeout=120)


def test_app_imports_without_gemini_key():
    r = _run(
        "import app.main, app.routes.matches, app.routes.websocket, app.ai_moderator\n"
        "from sqlalchemy.orm import configure_mappers; configure_mappers()\n"
        "import asyncio\n"
        "from app.ai_service import ai_service\n"
        "assert ai_service.model is None\n"
        "assert asyncio.run(ai_service.analyze_psychological_profile({}, None)) is None\n"
        "print('ok')"
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip().endswith("ok")


def test_docs_disabled_in_production():
    r = _run(
        "from fastapi.testclient import TestClient\n"
        "from app.main import app\n"
        "c = TestClient(app)\n"
        "print(c.get('/docs').status_code, c.get('/openapi.json').status_code, c.get('/health').status_code)",
        ENVIRONMENT="production",
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["404", "404", "200"]


def test_docs_enabled_in_development():
    r = _run(
        "from fastapi.testclient import TestClient\n"
        "from app.main import app\n"
        "print(TestClient(app).get('/openapi.json').status_code)"
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "200"


def test_production_refuses_to_start_with_placeholder_secret():
    r = _run("import app.main", ENVIRONMENT="production",
             JWT_SECRET_KEY="your-secret-key-change-in-production")
    assert r.returncode != 0
    assert "JWT_SECRET_KEY" in r.stderr


def test_startup_does_not_create_tables():
    """main.py must not call create_all: an empty DB stays empty after startup."""
    r = _run(
        "from fastapi.testclient import TestClient\n"
        "from sqlalchemy import inspect\n"
        "from app.main import app\n"
        "from app.database import engine\n"
        "with TestClient(app):\n"
        "    pass\n"
        "print(sorted(inspect(engine).get_table_names()))",
        DATABASE_URL="sqlite:///" + str(BACKEND_DIR / ".pytest-empty.db"),
    )
    try:
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == "[]"
    finally:
        (BACKEND_DIR / ".pytest-empty.db").unlink(missing_ok=True)
