# app/utils/telegram_handler.py

import logging
import asyncio
import time
from aiogram import Bot

MAX_MESSAGE_LENGTH = 4000      # Ограничение Telegram
THROTTLE_INTERVAL = 1.0        # В секунду максимум 1 лог в Telegram


class TelegramLogHandler(logging.Handler):
    def __init__(self, bot: Bot, chat_id: int, level=logging.INFO):
        super().__init__(level)
        self.bot = bot
        self.chat_id = chat_id
        self.last_sent_time = 0

    def emit(self, record):
        now = time.time()

        # Защита от спама (не чаще одного сообщения в секунду)
        if now - self.last_sent_time < THROTTLE_INTERVAL:
            return

        self.last_sent_time = now
        log_entry = self.format(record)

        # Обрезка слишком длинных сообщений
        if len(log_entry) > MAX_MESSAGE_LENGTH:
            log_entry = log_entry[:MAX_MESSAGE_LENGTH] + "\n...🔚 обрезано"

        asyncio.create_task(self._send(log_entry))

    async def _send(self, message: str):
        try:
            await self.bot.send_message(
                self.chat_id,
                f"{message}",
                parse_mode="HTML"
            )
        except Exception as e:
            print("❌ Ошибка отправки лога в Telegram:", e)
