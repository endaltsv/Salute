# app/greeter_bots/handlers/captcha_text.py

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove
from sqlalchemy import select

from app.database.base.session import async_session
from app.database.models.channel import Channel
from app.database.models.member import ChannelMember
from aiogram.fsm.state import StatesGroup, State


class CaptchaState(StatesGroup):
    waiting_for_captcha_click = State()


def get_router() -> Router:
    router = Router()

    @router.message()
    async def captcha_check_handler(message: Message, state: FSMContext):
        text = message.text
        user_id = message.from_user.id

        async with async_session() as session:
            result = await session.execute(
                select(Channel).where(Channel.captcha_enabled.is_(True))
            )
            channels = result.scalars().all()

            for channel in channels:
                if channel.captcha_has_button and channel.captcha_button_text == message.text:
                    # Удалим сообщение пользователя
                    try:
                        await message.delete()
                    except Exception:
                        pass

                    # Проверим, есть ли уже участник
                    existing_member = await session.execute(
                        select(ChannelMember).where(
                            ChannelMember.channel_id == channel.id,
                            ChannelMember.user_id == user_id
                        )
                    )
                    member = existing_member.scalar_one_or_none()

                    if member:
                        member.is_available_for_broadcast = True  # ✅ обновляем
                    else:
                        # ✅ создаём нового
                        member = ChannelMember(
                            bot_id=channel.bot_id,
                            channel_id=channel.id,
                            user_id=user_id,
                            is_available_for_broadcast=True
                        )
                        session.add(member)

                    await session.commit()

                    await message.bot.send_message(
                        chat_id=user_id,
                        text="✅ Спасибо, вы прошли капчу!",
                        reply_markup=ReplyKeyboardRemove()
                    )
                    return

    return router
