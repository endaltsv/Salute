# app/main_bot/database/base/session.py

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.main_bot.config.config import settings

DATABASE_URL = settings.database_url

# ✅ Увеличиваем пул соединений
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=40,
    pool_timeout=15,
)

# ✅ Создаём sessionmaker
async_session = async_sessionmaker(
    engine,
    expire_on_commit=False,
    class_=AsyncSession
)


# Не меняем get_session — пусть будет на будущее, если где-то нужно через Depends
async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
