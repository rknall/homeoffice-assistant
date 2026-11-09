# SPDX-FileCopyrightText: 2025 Roland Knall <rknall@gmail.com>
# SPDX-License-Identifier: GPL-2.0-only
"""Alembic environment for time-tracking plugin.

The host passes an open connection in ``config.attributes["connection"]`` and
the database URL in ``config.attributes["sqlalchemy.url"]``. The URL is not a
main option because ConfigParser interpolation rejects a ``%`` in it.
"""

from logging.config import fileConfig

from sqlalchemy import Connection, create_engine, pool

from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def _database_url() -> str | None:
    """Return the database URL handed over by the host, if any."""
    return config.attributes.get("sqlalchemy.url") or config.get_main_option(
        "sqlalchemy.url"
    )


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=config.get_main_option("version_table"),
    )

    with context.begin_transaction():
        context.run_migrations()


def _run_on(connection: Connection) -> None:
    """Run the migrations on an open connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        version_table=config.get_main_option("version_table"),
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connection = config.attributes.get("connection")
    if connection is not None:
        _run_on(connection)
        return

    connectable = create_engine(_database_url(), poolclass=pool.NullPool)
    with connectable.connect() as conn:
        _run_on(conn)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
