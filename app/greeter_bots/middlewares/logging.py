from aiogram.fsm.context import FSMContext
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from typing import Callable, Dict, Any
from sqlalchemy import select
from app.database.base.session import async_session
from app.database.models import ChannelMember
from app.database.models.bot import Bot
from app.database.models.user import User
from app.redis_queue.admin_logs import send_log_to_admin


class LoggingMiddleware(BaseMiddleware):
    def __init__(self, bot_id: int):
        self.bot_id = bot_id

    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        try:
            user_id = getattr(event.from_user, "id", None)
            state: FSMContext = data.get("state")
            tg_user = getattr(event, "from_user", None)

            if not tg_user:
                return await handler(event, data)

            telegram_id = tg_user.id

            await send_log_to_admin(
                f"🔍 Проверка пользователя <code>{telegram_id}</code> на владельца Greeter-бота <b>{self.bot_id}</b>"
            )

            async with async_session() as session:
                result = await session.execute(
                    select(User.telegram_id)
                    .join(Bot, Bot.owner_id == User.id)
                    .where(Bot.id == self.bot_id)
                )
                owner_telegram_id = result.scalar_one_or_none()

                if telegram_id == owner_telegram_id:
                    await send_log_to_admin(
                        f"✅ Пользователь <code>{telegram_id}</code> является владельцем Greeter-бота <b>{self.bot_id}</b>"
                    )
                    return await handler(event, data)

                await send_log_to_admin(
                    f"👤 Пользователь <code>{telegram_id}</code> — НЕ владелец бота <b>{self.bot_id}</b>"
                )

                existing_member = await session.execute(
                    select(ChannelMember).where(
                        ChannelMember.user_id == user_id,
                        ChannelMember.bot_id == self.bot_id
                    )
                )
                member = existing_member.scalar_one_or_none()

                if not member:
                    await send_log_to_admin(
                        f"❌ Пользователь <code>{telegram_id}</code> отсутствует в <b>channel_members</b> (bot_id={self.bot_id})",
                        level="warning"
                    )
                    return

                if not member.is_available_for_broadcast:
                    member.is_available_for_broadcast = True
                    await session.commit()

                    await send_log_to_admin(
                        f"🔓 Капча пройдена: пользователь <code>{telegram_id}</code> (bot_id={self.bot_id})"
                    )

                    return await event.answer("✅ Спасибо, вы прошли капчу.")

                if member.is_available_for_broadcast:
                    await send_log_to_admin(
                        f"📌 Пользователь <code>{telegram_id}</code> уже прошёл капчу (bot_id={self.bot_id})"
                    )
                    return

            return await handler(event, data)

        except Exception as e:
            await send_log_to_admin(
                f"🔥 <b>Ошибка в LoggingMiddleware</b>\n<code>{e}</code>",
                level="error"
            )
