import os
import subprocess
import logging
import sys
from sqlalchemy import select
from app.database.base.session import async_session
from app.database.models.bot import Bot as BotModel

logger = logging.getLogger(__name__)


async def launch_all_greeter_bots():
    async with async_session() as session:
        result = await session.execute(select(BotModel))
        bots = result.scalars().all()

        if not bots:
            logger.info("📭 Нет greeter-ботов для запуска.")
            return

        logger.info(f"🚀 Найдено {len(bots)} greeter-ботов. Запускаем...")

        for bot in bots:
            try:
                env = os.environ.copy()
                env["BOT_TOKEN"] = bot.token

                # ⚠️ Используем тот же Python, что и у main_bot
                python_executable = sys.executable  # путь до .venv/bin/python или Scripts/python.exe

                subprocess.Popen(
                    [python_executable, "greeter_runner.py"],  # путь к runner
                    env=env
                )
                logger.info(f"✅ Greeter-бот @{bot.name or 'Без имени'} запущен как процесс.")
            except Exception as e:
                logger.exception(f"❌ Ошибка при запуске бота @{bot.name or 'Без имени'}: {e}")
