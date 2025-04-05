from aiogram import types, Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import select

from app.database.base.session import async_session
from app.database.models.channel import Channel
from app.greeter_bots.keyboards.channel_settings import channel_settings_keyboard
from app.utils.logger import logger
from app.redis_queue.admin_logs import send_log_to_admin


def get_router() -> Router:
    router = Router()

    CHANNELS_LIST_TEXT = "📋 Твои каналы:"

    async def send_channels_list(callback: types.CallbackQuery, bot_id: int):
        async with async_session() as session:
            result = await session.execute(select(Channel).where(Channel.bot_id == bot_id))
            channels = result.scalars().all()

        if not channels:
            logger.info(f"📭 У пользователя @{callback.from_user.username} (ID: {callback.from_user.id}) нет каналов (bot_id={bot_id})")
            await send_log_to_admin(
                f"📭 У пользователя <code>{callback.from_user.id}</code> нет каналов (bot_id={bot_id})"
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main_menu")]
            ])
            await callback.message.edit_text("📭 У тебя пока нет каналов.", reply_markup=keyboard)
        else:
            logger.info(f"📋 Отображение списка каналов для пользователя @{callback.from_user.username} (ID: {callback.from_user.id})")
            await send_log_to_admin(
                f"📋 Пользователь <code>{callback.from_user.id}</code> просматривает список каналов (bot_id={bot_id})"
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text=ch.channel_name or ch.channel_id,
                    callback_data=f"channel_menu:{ch.id}"
                )] for ch in channels
            ] + [
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main_menu")]
            ])
            await callback.message.edit_text(CHANNELS_LIST_TEXT, reply_markup=keyboard)

    @router.callback_query(F.data == "my_channels")
    async def show_my_channels(callback: types.CallbackQuery, bot_id: int):
        await send_channels_list(callback, bot_id)
        await callback.answer()

    @router.callback_query(F.data == "back_to_channels_menu")
    async def back_to_channels_menu(callback: types.CallbackQuery, bot_id: int):
        await send_channels_list(callback, bot_id)
        await callback.answer()

    @router.callback_query(F.data.startswith("channel_menu:"))
    async def open_channel_menu(callback: types.CallbackQuery, bot_id: int):
        channel_id = int(callback.data.split(":")[1])

        async with async_session() as session:
            result = await session.execute(
                select(Channel).where(Channel.id == channel_id, Channel.bot_id == bot_id)
            )
            channel = result.scalar_one_or_none()

        if not channel:
            await callback.answer("❌ Канал не найден")
            logger.warning(
                f"❌ Канал ID {channel_id} не найден у пользователя @{callback.from_user.username} (ID: {callback.from_user.id})"
            )
            await send_log_to_admin(
                f"❌ Ошибка: канал <code>{channel_id}</code> не найден при открытии настроек (bot_id={bot_id})"
            )
            return

        logger.info(
            f"⚙️ Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) открыл настройки канала "
            f"{channel.channel_name or channel.channel_id} (ID: {channel_id})"
        )
        await send_log_to_admin(
            f"⚙️ Пользователь <code>{callback.from_user.id}</code> открыл настройки канала <b>{channel.channel_name}</b> (ID: {channel.channel_id})"
        )

        await callback.message.edit_text(
            f"<b>⚙ Настройка канала: <u>{channel.channel_name or 'Без названия'}</u></b>\n\n"
            "📌 Доступные опции:\n\n"
            "• <b>Приветственное сообщение</b> — автоматическая отправка сообщения при вступлении в канал\n"
            "• <b>Автоодобрение</b> — настройка принятий заявок в канал\n"
            "• <b>Капча</b> — присылает кнопку с текстом при нажатии на которую человек записывается в базу для дальнейших рассылок\n"
            "• <b>Удалить канал</b> — удаляет канал из бота и базы\n"
            "• <b>В главное меню</b> — вернуться к общему списку каналов",
            reply_markup=channel_settings_keyboard(channel)
        )

        await callback.answer()

    return router
