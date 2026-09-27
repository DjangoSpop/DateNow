"""
Database configuration and session management.

The schema is managed exclusively by Alembic (see ``backend/alembic``).
The application never calls ``Base.metadata.create_all``.
"""
from pathlib import Path

from sqlalchemy import MetaData, create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import settings

# Deterministic constraint names so Alembic migrations (incl. SQLite batch
# mode) can reference and drop constraints reliably.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


def is_sqlite_url(url: str) -> bool:
    return url.startswith("sqlite")


def build_engine(url: str, **kwargs) -> Engine:
    """Create an engine with sensible per-backend defaults."""
    if is_sqlite_url(url):
        kwargs.setdefault("connect_args", {"check_same_thread": False})
    elif settings.ENVIRONMENT == "testing":
        kwargs.setdefault("poolclass", NullPool)
    kwargs.setdefault("echo", settings.SQL_ECHO)
    return create_engine(url, **kwargs)


@event.listens_for(Engine, "connect")
def _sqlite_enable_foreign_keys(dbapi_connection, connection_record):
    """SQLite ignores FOREIGN KEY / ON DELETE unless enabled per connection."""
    module = type(dbapi_connection).__module__
    if module.startswith("sqlite3") or module.startswith("pysqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# Create SQLAlchemy engine
engine = build_engine(settings.DATABASE_URL)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base(metadata=MetaData(naming_convention=NAMING_CONVENTION))


def get_db():
    """
    Dependency for getting database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Bring the database schema up to date by running Alembic migrations
    (``alembic upgrade head``). Kept for scripts such as ``seed_data.py``;
    the API server does not call this on startup.
    """
    from alembic import command
    from alembic.config import Config

    backend_dir = Path(__file__).resolve().parent.parent
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "alembic"))
    command.upgrade(cfg, "head")
