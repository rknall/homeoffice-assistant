"""Alembic environment configuration."""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from sqlalchemy.schema import SchemaItem

from alembic import context
from src.config import settings
from src.models import Base
from src.plugins.loader import PluginLoader

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    """Return the database URL to migrate.

    A caller that migrates another database (the restore staging copy, test
    databases) hands its URL over in ``config.attributes`` rather than as a
    main option, because ConfigParser would interpolate a ``%`` in the URL.
    Without one, the command line case, the application settings apply.
    """
    return config.attributes.get("sqlalchemy.url") or settings.database_url


def plugin_table_prefixes() -> tuple[str, ...]:
    """Return the table prefixes declared by the discovered plugin manifests.

    Plugin tables live in the same database but are managed by each plugin's
    own migration chain, so the core autogenerate must not see them.
    """
    return tuple(
        manifest.table_prefix
        for _, manifest in PluginLoader().discover_plugins()
        if manifest.table_prefix
    )


PLUGIN_TABLE_PREFIXES = plugin_table_prefixes()


def include_object(
    obj: SchemaItem,
    name: str | None,
    type_: str,
    reflected: bool,
    compare_to: SchemaItem | None,
) -> bool:
    """Exclude plugin tables and plugin version tables from core comparisons.

    The exclusion holds whether the table was reflected from the database or
    comes from the metadata: a loaded plugin registers its models in the shared
    ``Base.metadata``, and the core chain must not create or drop them.

    Args:
        obj: The schema item being compared.
        name: Its name.
        type_: Item kind, e.g. "table", "column", "index".
        reflected: True when the item was reflected from the database.
        compare_to: The matching metadata item, None if there is none.

    Returns:
        False for tables named ``alembic_version_*`` or starting with a plugin
        table prefix, True for everything else.
    """
    if type_ == "table" and name:
        if name.startswith("alembic_version_"):
            return False
        if name.startswith(PLUGIN_TABLE_PREFIXES):
            return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
