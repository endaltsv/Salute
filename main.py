# main.py

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.database.base.init_db import init_db
from app.greeter_bots.core.launcher_all import launch_all_greeter_bots
from app.main_bot.config.config import settings
from app.main_bot.handlers import (
    about,
    create_bot,
    delete_bot,
    my_bots,
    pricing,
    start,
    support,
)
from app.main_bot.middlewares.UserMiddleware import UserMiddleware
from app.utils.logger import add_telegram_log_handler

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger(__name__)


def setup_middlewares(dp: Dispatcher) -> None:
    dp.message.middleware(UserMiddleware())
    dp.callback_query.middleware(UserMiddleware())
    logger.info("✅ Мидлвари зарегистрированы")


def setup_routers(dp: Dispatcher) -> None:
    dp.include_router(start.router)
    dp.include_router(create_bot.router)
    dp.include_router(my_bots.router)
    dp.include_router(delete_bot.router)
    dp.include_router(about.router)
    dp.include_router(support.router)
    dp.include_router(pricing.router)

    logger.info("✅ Роутеры подключены")


async def main() -> None:
    logger.info("🔄 Инициализация базы данных...")
    await init_db()
    logger.info("✅ База данных готова")

    logger.info("🤖 Запуск основного управляющего бота...")
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    add_telegram_log_handler(bot, settings.admin_chat_id)
    logger.info("🚀 Логгер запущен")

    dp = Dispatcher()
    setup_middlewares(dp)
    setup_routers(dp)

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.warning("�� Бот остановлен.")
