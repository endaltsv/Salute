# app/greeter_bots/core/launcher.py

import logging
from sqlalchemy import select

from app.database.base.session import async_session
from app.greeter_bots.core.bot import get_bot
from app.greeter_bots.core.dispatcher import get_dispatcher
from app.database.models.bot import Bot as BotModel


async def run_greeter_bot(token: str):
    logger = logging.getLogger(f"greeter_bot_{token[-6:]}")

    # 1️⃣ Получаем bot_id из базы
    async with async_session() as session:
        result = await session.execute(select(BotModel.id).where(BotModel.token == token))
        bot_id = result.scalar_one_or_none()

    if not bot_id:
        logger.error("❌ Не найден bot_id по токену. Запуск прерван.")
        return

    # 2️⃣ Инициализируем Aiogram бота
    bot = get_bot(token)

    # 3️⃣ Передаём bot_id в диспетчер
    dp = get_dispatcher(bot_id=bot_id)

    logger.info(f"✅ Greeter-бот запущен с bot_id={bot_id}")
    await dp.start_polling(bot)
