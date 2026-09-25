"""
Database configuration and session management.

The schema is managed exclusively by Alembic (`alembic upgrade head`); the app never calls create_all.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

_engine_kwargs = {"echo": settings.DEBUG}
if settings.ENVIRONMENT == "testing":
    _engine_kwargs["poolclass"] = NullPool
if settings.DATABASE_URL.startswith("postgresql"):
    # Timestamps are serialised as UTC regardless of the server's timezone setting.
    _engine_kwargs["connect_args"] = {"options": "-c timezone=utc"}

# Create SQLAlchemy engine
engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()


def get_db():
    """
    Dependency for getting database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
