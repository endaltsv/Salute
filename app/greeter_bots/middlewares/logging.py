from typing import Any, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import TelegramObject
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
        self, handler: Callable, event: TelegramObject, data: Dict[str, Any]
    ) -> Any:
        try:
            user_id = getattr(event.from_user, "id", None)
            tg_user = getattr(event, "from_user", None)

            if not tg_user:
                return await handler(event, data)

            telegram_id = tg_user.id

            await send_log_to_admin(
                f"🔍 Проверка пользователя {telegram_id} на владельца "
                f"Greeter-бота {self.bot_id}"
            )

            async with async_session() as session:
                result = await session.execute(
                    select(User.telegram_id)
                    .join(Bot, Bot.owner_id == User.id)
                    .where(Bot.id == self.bot_id)
                )
                owner_telegram_id = result.scalar_one_or_none()

                if telegram_id == owner_telegram_id:
                    # await send_log_to_admin(
                    #     f"✅ Пользователь {telegram_id} является владельцем "
                    #     f"Greeter-бота {self.bot_id}"
                    # )
                    return await handler(event, data)

                await send_log_to_admin(
                    f"👤 Пользователь {telegram_id} — НЕ владелец бота "
                    f"{self.bot_id}"
                )

                existing_member = await session.execute(
                    select(ChannelMember).where(
                        ChannelMember.user_id == user_id,
                        ChannelMember.bot_id == self.bot_id,
                    )
                )
                member = existing_member.scalar_one_or_none()

                if not member:
                    await send_log_to_admin(
                        f"❌ Пользователь {telegram_id} отсутствует в "
                        f"channel_members (bot_id={self.bot_id})",
                        level="warning",
                    )
                    return

                if not member.is_available_for_broadcast:
                    member.is_available_for_broadcast = True
                    await session.commit()

                    await send_log_to_admin(
                        f"🔓 Капча пройдена: пользователь {telegram_id} "
                        f"(bot_id={self.bot_id})"
                    )

                    return await event.answer("✅ Спасибо, вы прошли капчу.")

                if member.is_available_for_broadcast:
                    await send_log_to_admin(
                        f"📌 Пользователь {telegram_id} уже прошёл капчу "
                        f"(bot_id={self.bot_id})"
                    )
                    return

            return await handler(event, data)

        except Exception as e:
            await send_log_to_admin(
                f"🔥 <b>Ошибка в LoggingMiddleware</b>\n<code>{str(e)}</code>",
                level="error",
            )
