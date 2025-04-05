import asyncio
import logging
import os
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.client.default import DefaultBotProperties
from redis.asyncio import Redis
from app.utils.logger import logger
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", 0))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost")
DEFAULT_PARSE_MODE = DefaultBotProperties(parse_mode="HTML")

bot = Bot(token=BOT_TOKEN, default=DEFAULT_PARSE_MODE)
redis = Redis.from_url(REDIS_URL)

MAX_MSG_SIZE = 4096

log_buffer: dict[str, list[str]] = {
    "info": [],
    "warning": [],
    "error": [],
}

level_prefix = {
    "info": "<b>ℹ️ INFO</b>",
    "warning": "<b>⚠️ WARNING</b>",
    "error": "<b>❌ ERROR</b>",
}


async def flush_logs():
    for level, messages in log_buffer.items():
        if not messages:
            continue

        prefix = level_prefix.get(level, "")
        combined = prefix + "\n"

        while messages:
            msg = messages.pop(0)
            if len(combined) + len(msg) + 1 < MAX_MSG_SIZE:
                combined += f"{msg}\n"
            else:
                await send_safe(combined.strip())
                combined = prefix + "\n" + msg + "\n"

        if combined.strip() != prefix:
            await send_safe(combined.strip())


async def send_safe(text: str):
    try:
        await bot.send_message(ADMIN_CHAT_ID, text)
    except TelegramRetryAfter as e:
        logger.warning(f"⏳ FloodWait! Ждём {e.retry_after} сек...")
        await asyncio.sleep(e.retry_after)
        await send_safe(text)
    except Exception as e:
        logger.exception(f"❌ Ошибка при отправке лога в Telegram: {e}")


async def handle_log_entry(log_data: dict):
    msg = log_data["message"]
    level_str = log_data.get("level", "info").lower()
    level = level_str if level_str in log_buffer else "info"

    # Лог в буфер
    log_buffer[level].append(msg)

    # Также лог в stdout или файл
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }
    logging_level = level_map.get(level, logging.INFO)
    logger.log(logging_level, msg)
