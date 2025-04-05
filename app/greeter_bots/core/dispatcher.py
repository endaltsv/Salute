# app/greeter_bots/core/dispatcher.py

from aiogram import Dispatcher

from app.greeter_bots.middlewares.bot_id import BotIDMiddleware
from app.greeter_bots.middlewares.logging import LoggingMiddleware

from app.greeter_bots.handlers import (
    start,
    welcome,
    captcha,
    broadcast,
    add_channel,
    my_channels, autoapprove, delete_channel, noop, stats, captcha_text,
)

# Важно — импорт как функции get_router(bot_id)
from app.greeter_bots.handlers.member_join import get_router as get_member_join_router


def get_dispatcher(bot_id: int) -> Dispatcher:
    dp = Dispatcher()

    dp.message.middleware(LoggingMiddleware(bot_id))
    dp.callback_query.middleware(LoggingMiddleware(bot_id))

    dp.message.middleware(BotIDMiddleware(bot_id))
    dp.callback_query.middleware(BotIDMiddleware(bot_id))


    dp.include_router(get_member_join_router(bot_id))
    dp.include_router(start.get_router())
    dp.include_router(broadcast.get_router())
    dp.include_router(welcome.get_router())
    dp.include_router(add_channel.get_router())
    dp.include_router(captcha.get_router())
    # dp.include_router(captcha_text.get_router())
    dp.include_router(my_channels.get_router())
    dp.include_router(autoapprove.get_router(bot_id))
    dp.include_router(delete_channel.get_router())
    dp.include_router(noop.get_router())
    dp.include_router(stats.get_router(bot_id))

    return dp
