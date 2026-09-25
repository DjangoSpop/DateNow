import pytest
from pydantic import ValidationError

from app.config import DEV_INSECURE_JWT_SECRET, Settings

DB = "postgresql://u:p@localhost/db"
STRONG = "a-strong-production-secret-with-more-than-32-chars"


def make(**kw):
    return Settings(_env_file=None, DATABASE_URL=DB, **kw)


def test_defaults(monkeypatch):
    for var in ("DEBUG", "GEMINI_API_KEY", "JWT_SECRET_KEY", "ENVIRONMENT"):
        monkeypatch.delenv(var, raising=False)
    s = make()
    assert s.DEBUG is False
    assert s.GEMINI_API_KEY is None
    assert s.JWT_SECRET_KEY == DEV_INSECURE_JWT_SECRET  # dev fallback only


@pytest.mark.parametrize("secret", [None, "", "short", "your-super-secret-jwt-key-change-this-in-production",
                                    DEV_INSECURE_JWT_SECRET])
@pytest.mark.parametrize("env", ["production", "staging"])
def test_refuses_weak_secret_outside_dev(monkeypatch, secret, env):
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    kwargs = {"ENVIRONMENT": env}
    if secret is not None:
        kwargs["JWT_SECRET_KEY"] = secret
    with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
        make(**kwargs)


def test_strong_secret_in_production():
    assert make(ENVIRONMENT="production", JWT_SECRET_KEY=STRONG).JWT_SECRET_KEY == STRONG


def test_ai_modules_import_without_key():
    import app.ai_moderator
    import app.ai_service

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        app.ai_service.ai_service.model  # noqa: B018
