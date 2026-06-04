"""Alembic Environment Configuration"""

import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# This is the Alembic Config object, which provides the values of the [alembic] section
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object for 'autogenerate' support
try:
    from crm_models import Base
    target_metadata = Base.metadata
except ImportError:
    target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    configuration = config.get_section(config.config_ini_section)
    
    # Get database URL from environment or use default
    sqlalchemy_url = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost/pureleven_crm')
    configuration["sqlalchemy.url"] = sqlalchemy_url
    
    context.configure(
        url=sqlalchemy_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section)
    
    # Get database URL from environment or use default
    configuration["sqlalchemy.url"] = os.environ.get('DATABASE_URL', 'postgresql://user:password@localhost/pureleven_crm')
    
    connectable = engine_from_config(
        configuration, prefix="sqlalchemy.", poolclass=pool.NullPool
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
