# app/main_bot/middlewares/user_saver.py

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from app.database.models.user import User
from app.database.base.session import async_session
from sqlalchemy import select
from typing import Callable, Dict, Any


class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable,
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        tg_user = getattr(event, 'from_user', None)

        if tg_user:
            async with async_session() as session:
                result = await session.execute(select(User).where(User.telegram_id == tg_user.id))
                user = result.scalar_one_or_none()

                if not user:
                    user = User(
                        telegram_id=tg_user.id,
                    )
                    session.add(user)
                    await session.commit()

        return await handler(event, data)
