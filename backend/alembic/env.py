"""Alembic environment for DateNow.

URL resolution order:
1. an existing Connection passed via ``config.attributes["connection"]``
2. ``sqlalchemy.url`` set on the Alembic Config (e.g. by tests)
3. ``app.config.settings.DATABASE_URL``
"""
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make "app" importable when alembic is run from anywhere.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402
from app.database import Base  # noqa: E402
import app.models  # noqa: E402,F401  (register all tables on Base.metadata)

config = context.config

if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _database_url() -> str:
    return config.get_main_option("sqlalchemy.url") or settings.DATABASE_URL


def _configure_kwargs(url: str) -> dict:
    return dict(
        target_metadata=target_metadata,
        render_as_batch=url.startswith("sqlite"),
        compare_type=True,
        compare_server_default=False,
    )


def run_migrations_offline() -> None:
    url = _database_url()
    context.configure(
        url=url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **_configure_kwargs(url),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connection = config.attributes.get("connection")
    if connection is not None:
        context.configure(
            connection=connection,
            **_configure_kwargs(str(connection.engine.url)),
        )
        with context.begin_transaction():
            context.run_migrations()
        return

    url = _database_url()
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = url
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, **_configure_kwargs(url))
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
