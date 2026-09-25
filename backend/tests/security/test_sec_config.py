"""Configuration fail-safe checks."""
import pytest

from app.config import DEV_INSECURE_JWT_SECRET, Settings


def make(monkeypatch, **kw):
    for var in ("ENVIRONMENT", "JWT_SECRET_KEY", "DEBUG"):
        monkeypatch.delenv(var, raising=False)
    return Settings(_env_file=None, DATABASE_URL="postgresql://u:p@localhost/db", **kw)


@pytest.mark.parametrize("env", ["production", "staging", "prod", "Production", "DEVELOPMENT"])
def test_public_dev_secret_refused_for_any_non_dev_environment_name(monkeypatch, env):
    with pytest.raises(ValueError, match="JWT_SECRET_KEY"):
        make(monkeypatch, ENVIRONMENT=env)


def test_missing_environment_does_not_fall_back_to_public_secret(monkeypatch):
    try:
        settings = make(monkeypatch)
    except ValueError:
        return
    assert settings.JWT_SECRET_KEY != DEV_INSECURE_JWT_SECRET
