#app/greeter_bots/handlers/member_join.py
import asyncio
import json

from aiogram import Router

from aiogram.types import ChatJoinRequest, ChatMemberUpdated

from app.redis_queue.admin_logs import send_log_to_admin
from app.redis_queue.connection import redis
from app.utils.logger import logger


def get_router(bot_id: int) -> Router:
    router = Router()
    logger.info(f"📌 Router initialized for bot_id={bot_id}")
    asyncio.create_task(
        send_log_to_admin(f"📌 Greeter router инициализирован для bot_id={bot_id}")
    )

    @router.chat_member()
    async def handle_member_join(update: ChatMemberUpdated):
        if (
            update.old_chat_member.status in ("left", "kicked")
            and update.new_chat_member.status in ("member", "administrator")
            and not update.from_user.is_bot
        ):
            user_id = update.from_user.id
            chat_id = update.chat.id

            logger.info(f"📥 Участник вступил: user_id={user_id}, chat_id={chat_id}")
            await send_log_to_admin(
                f"👥 Пользователь <code>{user_id}</code> вступил в <code>{chat_id}</code> (bot_id={bot_id})"
            )

            await redis.rpush(
                "join_queue",
                json.dumps({"user_id": user_id, "chat_id": chat_id, "bot_id": bot_id}),
            )

            # logger.info(f"📤 Задача добавлена в Redis для user_id={user_id}")
            # await send_log_to_admin(f"📤 Задача на вступление отправлена в Redis (user_id={user_id})")

    @router.chat_join_request()
    async def handle_chat_join_request(update: ChatJoinRequest):
        if not update.from_user.is_bot:
            user_id = update.from_user.id
            chat_id = update.chat.id

            # logger.info(f"📥 Запрос на вступление: user_id={user_id}, chat_id={chat_id}")
            # await send_log_to_admin(
            #     f"📨 Запрос на вступление от <code>{user_id}</code> в <code>{chat_id}</code> (bot_id={bot_id})"
            # )

            await redis.rpush(
                "join_queue",
                json.dumps({"user_id": user_id, "chat_id": chat_id, "bot_id": bot_id}),
            )

            logger.info(f"📤 Задача добавлена в Redis для user_id={user_id}")
            # await send_log_to_admin(f"📤 Задача на join_request отправлена в Redis (user_id={user_id})")

    return router
