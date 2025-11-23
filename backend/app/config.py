"""
Application configuration settings
"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, validator
import os


class Settings(BaseSettings):
    """Application settings"""

    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "DateNow"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # JWT Settings
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AI Configuration
    GEMINI_API_KEY: str
    AI_MODEL: str = "gemini-pro"
    AI_TEMPERATURE: float = 0.7
    AI_MAX_TOKENS: int = 2048

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8000",
    ]

    @validator("BACKEND_CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, (list, str)):
            return v
        raise ValueError(v)

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

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
