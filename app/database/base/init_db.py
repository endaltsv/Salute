from app.database.base.session import engine
from app.database.base.base_model import Base
import logging

logger = logging.getLogger(__name__)


async def init_db():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Таблицы успешно инициализированы.")
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации базы: {e}")
