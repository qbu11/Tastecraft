"""Alembic env.py — works with both SQLite (dev) and PostgreSQL (prod).

Derives a synchronous database URL from the app's async DATABASE_URL setting.
"""

import os
from logging.config import fileConfig

from sqlalchemy import Connection, pool, create_engine
from alembic import context

# ── Import app config and models ──────────────────────────────────
from app.core.config import settings
from app.core.database import Base

# Import all models so Base.metadata is fully populated for autogenerate
import app.models  # noqa: F401

# ── Alembic config ────────────────────────────────────────────────
config = context.config

# Derive a *synchronous* URL from the async one used by the app.
# Alembic runs with a sync engine; the app runs with async.
_async_url = settings.database_url
if "+aiosqlite" in _async_url:
    _sync_url = _async_url.replace("+aiosqlite", "")
elif "+asyncpg" in _async_url:
    _sync_url = _async_url.replace("+asyncpg", "+psycopg2")
else:
    _sync_url = _async_url

# Allow env-var override for CI / offline generation
_sync_url = os.environ.get("ALEMBIC_DATABASE_URL", _sync_url)

config.set_main_option("sqlalchemy.url", _sync_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL without DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def _do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode with a synchronous engine."""
    url = config.get_main_option("sqlalchemy.url")
    engine_kwargs: dict = {"poolclass": pool.NullPool}

    if url and url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}

    connectable = create_engine(url or "", **engine_kwargs)

    with connectable.connect() as connection:
        _do_run_migrations(connection)

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
