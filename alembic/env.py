import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection

from alembic import context

# Заглушки для Pydantic Settings при запуске alembic без .env
# (autogenerate только смотрит на метаданные, реальные ключи не нужны)
for _var, _val in {
    "BOT_TOKEN": "dummy",
    "TELEGRAM_API_ID": "0",
    "TELEGRAM_API_HASH": "dummy",
    "DEEPSEEK_API_KEY": "dummy",
    "ADMIN_ID": "0",
}.items():
    os.environ.setdefault(_var, _val)

# Импортируем Base + все модели чтобы autogenerate их видел
import database.models  # noqa: F401 — side-effect: регистрирует таблицы
from database.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Генерация SQL без подключения к БД."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Синхронный движок — Alembic не требует async."""
    from sqlalchemy import engine_from_config

    section = dict(config.get_section(config.config_ini_section, {}))
    # Подменяем async-драйвер на синхронный
    url: str = section.get("sqlalchemy.url", "")
    section["sqlalchemy.url"] = (
        url.replace("sqlite+aiosqlite", "sqlite")
           .replace("postgresql+asyncpg", "postgresql")
    )

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        do_run_migrations(connection)
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
