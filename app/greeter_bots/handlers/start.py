from aiogram import types, Router
from aiogram.filters import Command
from sqlalchemy import select

from app.database.base.session import async_session
from app.database.models.channel import Channel
from app.greeter_bots.keyboards.main_menu import greeter_main_menu
from app.utils.logger import logger
from app.redis_queue.admin_logs import send_log_to_admin


def get_router() -> Router:
    router = Router()

    text = (
        "<b>👋 Добро пожаловать в дочернего бота!</b>\n\n"
        "Этот бот помогает вам эффективно взаимодействовать с аудиторией в ваших Telegram-каналах:\n\n"
        "• <b>➕ Добавить канал</b> — подключите канал для приветствий, капчи и рассылок\n"
        "• <b>📢 Рассылка</b> — отправляйте автоматические сообщения новым участникам\n"
        "• <b>🗒 Статистика</b> — следите, кто вступил, прошёл капчу и получил рассылку\n\n"
        "<i>Ниже вы увидите список подключённых каналов — нажмите на нужный, чтобы перейти к его настройке.</i>"
    )

    @router.message(Command("start"))
    async def start_handler(message: types.Message, bot_id: int):
        async with async_session() as session:
            result = await session.execute(select(Channel).where(Channel.bot_id == bot_id))
            channels = result.scalars().all()

        logger.info(
            f"🚀 Пользователь @{message.from_user.username} (ID: {message.from_user.id}) запустил /start (bot_id={bot_id})"
        )
        await send_log_to_admin(
            f"🚀 <code>{message.from_user.id}</code> запустил <b>/start</b> в Greeter-боте (bot_id={bot_id})"
        )

        await message.answer(
            text,
            reply_markup=greeter_main_menu(channels)
        )

    @router.callback_query(lambda c: c.data == "back_to_main_menu")
    async def back_to_main_menu_handler(callback: types.CallbackQuery, bot_id: int):
        async with async_session() as session:
            result = await session.execute(select(Channel).where(Channel.bot_id == bot_id))
            channels = result.scalars().all()

        logger.info(
            f"⬅️ Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) вернулся в главное меню (bot_id={bot_id})"
        )
        await send_log_to_admin(
            f"⬅️ <code>{callback.from_user.id}</code> вернулся в главное меню Greeter-бота (bot_id={bot_id})"
        )

        await callback.message.edit_text(
            text,
            reply_markup=greeter_main_menu(channels)
        )
        await callback.answer()

    return router
