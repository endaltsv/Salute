from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta

from app.database.base.session import async_session
from app.database.models import ChannelMember
from app.database.models.channel import Channel
from app.utils.logger import logger
from app.redis_queue.admin_logs import send_log_to_admin


def get_router(bot_id: int) -> Router:
    router = Router()

    @router.callback_query(F.data == "stats")
    async def stats_menu(callback: CallbackQuery):
        async with async_session() as session:
            result = await session.execute(
                select(Channel).where(Channel.bot_id == bot_id)
            )
            channels = result.scalars().all()

        logger.info(
            f"📊 Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) открыл меню статистики (bot_id={bot_id})"
        )
        await send_log_to_admin(
            f"📊 <code>{callback.from_user.id}</code> открыл <b>статистику</b> Greeter-бота (bot_id={bot_id})"
        )

        if not channels:
            await callback.message.edit_text("❌ У вас пока нет добавленных каналов.")
            return

        keyboard = [
            [InlineKeyboardButton(
                text=channel.channel_name or f"Канал {channel.channel_id}",
                callback_data=f"stats:{channel.id}"
            )] for channel in channels
        ]
        keyboard.append([InlineKeyboardButton(text="📢 Все каналы", callback_data="stats:all")])
        keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main_menu")])

        await callback.message.edit_text(
            "📊 <b>Выберите канал для просмотра статистики:</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("stats:"))
    async def stats_handler(callback: CallbackQuery):
        _, channel_id_raw = callback.data.split(":")

        async with async_session() as session:
            result = await session.execute(
                select(Channel).where(Channel.bot_id == bot_id)
            )
            channels = result.scalars().all()
            available_channel_ids = [c.id for c in channels]

            if channel_id_raw == "all":
                selected_channels = channels
                channel_ids = available_channel_ids
                channel_label = "всех ваших каналов"

                logger.info(
                    f"📊 Пользователь @{callback.from_user.username} запросил статистику по всем каналам (bot_id={bot_id})"
                )
                await send_log_to_admin(
                    f"📊 <code>{callback.from_user.id}</code> запросил <b>статистику по всем каналам</b> (bot_id={bot_id})"
                )

                total_subscribers = 0
                failed_channels = []

                for ch in selected_channels:
                    try:
                        chat = await callback.bot.get_chat(ch.channel_id)
                        count = await callback.bot.get_chat_member_count(chat.id)
                        total_subscribers += count
                    except Exception:
                        failed_channels.append(ch.channel_name or f"ID {ch.channel_id}")

                total_subscribers_text = (
                    f"👥 Подписчиков во всех каналах: <b>{total_subscribers}</b>\n"
                    if total_subscribers else
                    "👥 Подписчиков во всех каналах: <i>не удалось получить</i>\n"
                )
                if failed_channels:
                    total_subscribers_text += f"⚠️ Не удалось получить из: {', '.join(failed_channels)}\n"
            else:
                channel_id = int(channel_id_raw)
                if channel_id not in available_channel_ids:
                    await callback.answer("🚫 Этот канал недоступен для текущего бота.", show_alert=True)
                    return

                selected_channel = next((c for c in channels if c.id == channel_id), None)
                selected_channels = [selected_channel]
                channel_ids = [channel_id]

                logger.info(
                    f"📊 Пользователь @{callback.from_user.username} запросил статистику по каналу {selected_channel.channel_name} (bot_id={bot_id})"
                )
                await send_log_to_admin(
                    f"📊 <code>{callback.from_user.id}</code> запросил <b>статистику</b> по каналу <b>{selected_channel.channel_name}</b> (bot_id={bot_id})"
                )

                try:
                    chat = await callback.bot.get_chat(selected_channel.channel_id)
                    count = await callback.bot.get_chat_member_count(chat.id)
                    total_subscribers_text = f"👥 Подписчиков в канале: <b>{count}</b>\n"
                except Exception:
                    total_subscribers_text = "👥 Подписчиков в канале: <i>не удалось получить</i>\n"

                channel_label = f"канала <b>{selected_channel.channel_name}</b>"

            now = datetime.now(timezone.utc)
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = now - timedelta(days=7)
            month_ago = now - timedelta(days=30)

            known_users = await session.scalar(
                select(func.count()).where(ChannelMember.channel_id.in_(channel_ids))
            )
            broadcastable = await session.scalar(
                select(func.count()).where(
                    ChannelMember.channel_id.in_(channel_ids),
                    ChannelMember.is_available_for_broadcast.is_(True)
                )
            )
            new_today = await session.scalar(
                select(func.count()).where(
                    ChannelMember.channel_id.in_(channel_ids),
                    ChannelMember.joined_at >= today_start
                )
            )
            new_week = await session.scalar(
                select(func.count()).where(
                    ChannelMember.channel_id.in_(channel_ids),
                    ChannelMember.joined_at >= week_ago
                )
            )
            new_month = await session.scalar(
                select(func.count()).where(
                    ChannelMember.channel_id.in_(channel_ids),
                    ChannelMember.joined_at >= month_ago
                )
            )

            text = (
                f"📊 <b>Статистика {channel_label}</b>\n\n"
                f"{total_subscribers_text}"
                f"🤖 Пользователей, с кем бот уже знаком: <b>{known_users}</b>\n"
                f"📢 Из них можно отправлять сообщения: <b>{broadcastable}</b>\n\n"
                f"📅 Новых пользователей за сегодня: <b>{new_today}</b>\n"
                f"🗓 За последние 7 дней: <b>{new_week}</b>\n"
                f"📈 За последние 30 дней: <b>{new_month}</b>\n"
            )

            builder = InlineKeyboardBuilder()
            builder.button(text="⬅ Назад", callback_data="stats")

            await callback.message.edit_text(text, reply_markup=builder.as_markup())
            await callback.answer()

    return router
