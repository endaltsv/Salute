# app/utils/logger.py

import logging
import os
from logging import StreamHandler, Formatter

logger = logging.getLogger("salute_bot")
logger.setLevel(logging.DEBUG)

# Стандартный вывод в консоль
console_handler = StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(Formatter(
    '[%(asctime)s] [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
logger.addHandler(console_handler)


# Функция для добавления Telegram-хендлера
def add_telegram_log_handler(bot, chat_id: int):
    from app.utils.telegram_handler import TelegramLogHandler

    # Только если включено в .env
    # if os.getenv("LOG_TO_TELEGRAM", "true").lower() != "true":
    #     return

    tg_handler = TelegramLogHandler(bot, chat_id)
    tg_handler.setLevel(logging.INFO)  # Отправляем только важные логи
    tg_handler.setFormatter(Formatter('%(levelname)s: %(message)s'))
    logger.addHandler(tg_handler)
