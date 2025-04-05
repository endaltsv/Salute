from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

import sys
import os

from app.database.base.base_model import Base

# 📁 Добавляем путь к app, если запуск из корня
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ⬇ Импорт настроек и моделей
from app.main_bot.config.config import settings
from app.database import models  # 🔥 Обязательный импорт всех моделей

# Alembic Config
config = context.config

# Подключаем логирование (если указано в alembic.ini)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Подставляем URL базы из settings
config.set_main_option("sqlalchemy.url", settings.alembic_database_url)

# Указываем metadata — нужно для autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Миграции в offline-режиме (без подключения к базе, только SQL-скрипт)"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Миграции в online-режиме (подключение к базе и выполнение изменений)"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
