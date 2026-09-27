"""
Application configuration settings
"""
from typing import List, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Secrets that must never be used outside local development.
_PLACEHOLDER_SECRETS = {
    "secret",
    "changeme",
    "change-me",
    "test",
    "your-secret-key",
    "your-secret-key-change-in-production",
    "your-super-secret-jwt-key-change-this-in-production",
    "change-this-to-a-long-random-string",
}
# Substrings that mark a secret as an obvious placeholder (case-insensitive).
_PLACEHOLDER_MARKERS = ("changeme", "change_me", "change-me", "change-this", "change_this",
                        "your-secret", "your_secret", "your-super-secret", "placeholder")
_MIN_PRODUCTION_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """Application settings"""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "DateNow"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    # Log every SQL statement (independent of DEBUG so debug mode never leaks queries)
    SQL_ECHO: bool = False

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT Settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"  # only HS256 is accepted (see validator)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI Configuration (optional: AI features are disabled when no key is set)
    GEMINI_API_KEY: Optional[str] = None
    AI_MODEL: str = "gemini-pro"
    AI_TEMPERATURE: float = 0.7
    AI_MAX_TOKENS: int = 2048

    # Auth rate limiting (in-process sliding window, per client IP and per email).
    # 0 disables it.
    AUTH_RATE_LIMIT_PER_MINUTE: int = 10

    # CORS (JSON array in env, e.g. ["http://localhost:3000"])
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    # WebSocket Settings
    WS_MESSAGE_QUEUE_SIZE: int = 100
    WS_HEARTBEAT_INTERVAL: int = 30

    # AI Conversation Settings
    AI_SESSION_TIMEOUT_MINUTES: int = 60
    AI_QUESTIONS_PER_SESSION: int = 10
    COMPATIBILITY_THRESHOLD: float = 0.7

    # Matching Settings
    MAX_DAILY_MATCHES: int = 10
    MATCH_RADIUS_KM: int = 50

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @field_validator("GEMINI_API_KEY", mode="before")
    @classmethod
    def empty_key_is_none(cls, v):
        if isinstance(v, str) and not v.strip():
            return None
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def secret_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("JWT_SECRET_KEY must not be empty")
        return v

    @field_validator("JWT_ALGORITHM")
    @classmethod
    def only_hs256(cls, v: str) -> str:
        if v != "HS256":
            raise ValueError("JWT_ALGORITHM must be HS256")
        return v

    @field_validator("BACKEND_CORS_ORIGINS")
    @classmethod
    def no_wildcard_origin(cls, v: List[str]) -> List[str]:
        # CORS is configured with allow_credentials=True; a wildcard origin
        # would let any site make credentialed requests.
        if any(o.strip() == "*" for o in v):
            raise ValueError("'*' is not allowed in BACKEND_CORS_ORIGINS (credentials are allowed)")
        return v

    @model_validator(mode="after")
    def production_secret_strength(self):
        if self.is_production:
            secret = self.JWT_SECRET_KEY
            if (
                secret.strip().lower() in _PLACEHOLDER_SECRETS
                or any(m in secret.lower() for m in _PLACEHOLDER_MARKERS)
                or len(secret) < _MIN_PRODUCTION_SECRET_LENGTH
            ):
                raise ValueError(
                    "JWT_SECRET_KEY is a placeholder or shorter than "
                    f"{_MIN_PRODUCTION_SECRET_LENGTH} characters; refusing to start in production"
                )
        return self

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def ai_enabled(self) -> bool:
        return bool(self.GEMINI_API_KEY)


# Global settings instance
settings = Settings()
