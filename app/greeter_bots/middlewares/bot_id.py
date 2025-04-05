from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Dict, Any, Awaitable


class BotIDMiddleware(BaseMiddleware):
    def __init__(self, bot_id: int):
        self.bot_id = bot_id

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        data["bot_id"] = self.bot_id
        return await handler(event, data)
