"""
Application configuration settings
"""
import logging
from typing import List, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Environments in which a missing/weak JWT secret is tolerated (a fixed, clearly insecure dev key is used).
INSECURE_SECRET_ENVIRONMENTS = ("development", "testing")

# Only ever used in development/testing when JWT_SECRET_KEY is not provided.
DEV_INSECURE_JWT_SECRET = "insecure-dev-only-jwt-secret-do-not-use-in-production"

# Known placeholder values (from .env.example / docker-compose) that must never be used outside dev.
KNOWN_WEAK_SECRETS = {
    "",
    "secret",
    "changeme",
    "change-me",
    "your-secret-key",
    "your-super-secret-jwt-key-change-this-in-production",
    "your-secret-key-change-in-production",
    DEV_INSECURE_JWT_SECRET,
}
MIN_SECRET_LENGTH = 32


class Settings(BaseSettings):
    """Application settings"""

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "DateNow"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str

    # Redis (not used by the API yet)
    REDIS_URL: str = "redis://localhost:6379"

    # JWT Settings
    JWT_SECRET_KEY: Optional[str] = None
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI Configuration (optional: the API starts without it; AI features fail only when used)
    GEMINI_API_KEY: Optional[str] = None
    AI_MODEL: str = "gemini-pro"
    AI_TEMPERATURE: float = 0.7
    AI_MAX_TOKENS: int = 2048

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

    @model_validator(mode="after")
    def check_jwt_secret(self) -> "Settings":
        secret = self.JWT_SECRET_KEY or ""
        weak = secret in KNOWN_WEAK_SECRETS or len(secret) < MIN_SECRET_LENGTH
        if not weak:
            return self
        if self.ENVIRONMENT not in INSECURE_SECRET_ENVIRONMENTS:
            raise ValueError(
                "JWT_SECRET_KEY is missing or weak (placeholder value or shorter than "
                f"{MIN_SECRET_LENGTH} characters); refusing to start with ENVIRONMENT={self.ENVIRONMENT!r}"
            )
        if not secret:
            self.JWT_SECRET_KEY = DEV_INSECURE_JWT_SECRET
        logger.warning("Using a weak/insecure JWT_SECRET_KEY (ENVIRONMENT=%s). Never do this in production.",
                       self.ENVIRONMENT)
        return self

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

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}


# Global settings instance
settings = Settings()
