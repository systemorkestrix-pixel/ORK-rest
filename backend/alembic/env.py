from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config, pool
from alembic import context

from app.database import Base
import app.models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """
    Single source of truth for Alembic DB connection.
    Priority:
    1. DATABASE_URL (preferred)
    2. DATABASE_PATH (fallback for SQLite file path)
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return url

    path = os.getenv("DATABASE_PATH")
    if path:
        return f"sqlite:///{path}"

    # safe fallback for local dev only
    return "sqlite:///restaurant.db"


DATABASE_URL = get_database_url()


def _enforce_autogenerate_policy() -> None:
    app_env = (os.getenv("APP_ENV") or "development").strip().lower()
    cmd_opts = getattr(config, "cmd_opts", None)
    is_autogenerate = bool(cmd_opts and getattr(cmd_opts, "autogenerate", False))

    if app_env == "production" and is_autogenerate:
        raise RuntimeError("Alembic autogenerate is blocked in production.")


_enforce_autogenerate_policy()


def run_migrations_offline() -> None:
    url = DATABASE_URL

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        render_as_batch=url.startswith("sqlite"),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    config.set_main_option("sqlalchemy.url", DATABASE_URL)

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=DATABASE_URL.startswith("sqlite"),
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()