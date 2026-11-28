"""Alembic environment. The database URL comes from VOYA_DB / DATABASE_URL."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from voya.store import default_db_path

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def sqlalchemy_url() -> str:
    target = default_db_path()
    if target.startswith("postgres"):
        raw = target.replace("postgresql+psycopg://", "postgresql://", 1)
        if raw.startswith("postgresql://"):
            return "postgresql+psycopg://" + raw[len("postgresql://") :]
        return raw
    if target == ":memory:":
        return "sqlite://"
    return "sqlite:///" + target


def run_migrations_offline() -> None:
    context.configure(url=sqlalchemy_url(), literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    section = config.get_section(config.config_ini_section) or {}
    section["sqlalchemy.url"] = sqlalchemy_url()
    connectable = engine_from_config(section, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=None)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
