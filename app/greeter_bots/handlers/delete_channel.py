from aiogram import Router, F, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import delete
from app.database.base.session import async_session
from app.database.models import ChannelMember
from app.database.models.channel import Channel
from app.utils.logger import logger
from app.redis_queue.admin_logs import send_log_to_admin

# Импортируем функцию удаления из кеша
from workers.join_worker.services.channel_cache import remove_channel_from_cache

def get_router() -> Router:
    router = Router()

    @router.callback_query(F.data.startswith("delete_channel:"))
    async def handle_delete_channel(callback: types.CallbackQuery):
        channel_id = int(callback.data.split(":")[1])

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Да",
                    callback_data=f"confirm_delete_channel:{channel_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Назад",
                    callback_data="back_to_main_menu"
                )
            ]
        ])

        log_text = (
            f"🗑 Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) "
            f"хочет удалить канал (ID={channel_id})"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

        await callback.message.edit_text(
            "⚠️ Вы уверены, что хотите <b>удалить этот канал</b>?\n"
            "Все настройки и участники, связанные с ним, будут удалены.",
            reply_markup=keyboard
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("confirm_delete_channel:"))
    async def confirm_delete_channel(callback: types.CallbackQuery, bot_id: int):
        channel_id = int(callback.data.split(":")[1])

        log_text = (
            f"✅ Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) "
            f"подтвердил удаление канала (ID={channel_id}, bot_id={bot_id})"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

        async with async_session() as session:
            # Удаляем участников канала
            await session.execute(
                delete(ChannelMember).where(ChannelMember.channel_id == channel_id)
            )
            logger.info(f"🧹 Удалены участники канала (ID={channel_id})")

            # Удаляем сам канал
            await session.execute(
                delete(Channel).where(Channel.id == channel_id, Channel.bot_id == bot_id)
            )
            await session.commit()

            log_text = (
                f"♻️ Канал (ID={channel_id}) успешно удалён из базы (bot_id={bot_id})"
            )
            await send_log_to_admin(log_text)
            logger.info(log_text)

        # Удаляем канал из кеша
        await remove_channel_from_cache(channel_id, bot_id)

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main_menu")]
        ])

        await callback.message.edit_text(
            "✅ Канал успешно удалён.\n\n",
            reply_markup=keyboard
        )
        await callback.answer("Канал удалён")

    return router
