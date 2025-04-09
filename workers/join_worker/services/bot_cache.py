# workers/join_worker/services/bot_cache.py

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties

from app.database.base.session import async_session
from app.database.models.bot import Bot as BotModel
from app.utils.logger import logger

DEFAULT_PARSE_MODE = DefaultBotProperties(parse_mode="HTML")

bot_cache = {}


async def init_bot_cache():
    logger.info("🔄 Initializing bot cache...")

    # Закрываем старые сессии
    for bot in bot_cache.values():
        try:
            await bot.session.close()
        except Exception as e:
            logger.warning(f"⚠️ Failed to close bot session: {e}")

    bot_cache.clear()

    async with async_session() as session:
        result = await session.execute(BotModel.__table__.select())
        bots = result.fetchall()

        for bot_row in bots:
            bot_id = bot_row.id
            bot_token = bot_row.token
            bot_cache[bot_id] = Bot(token=bot_token, default=DEFAULT_PARSE_MODE)

    logger.info(f"✅ Cached {len(bot_cache)} bots")


def get_bot(bot_id: int) -> Bot:
    return bot_cache.get(bot_id)
