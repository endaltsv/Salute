import asyncio
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, update
from sqlalchemy.orm import joinedload
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest, TelegramRetryAfter

from app.database.base.session import async_session
from app.database.models.channel import Channel
from app.database.models.member import ChannelMember
from app.utils.logger import logger

DEFAULT_PARSE_MODE = DefaultBotProperties(parse_mode="HTML")
MAX_CONCURRENT_SENDS = 30
CHUNK_SIZE = 1000
semaphore = asyncio.Semaphore(MAX_CONCURRENT_SENDS)


async def process_broadcast_task(data: dict):
    bot_id = data["bot_id"]
    text = data["text"]
    user_ids = data["user_ids"]
    button_text = data.get("button_text")
    button_url = data.get("button_url")
    response_chat_id = data.get("response_chat_id")
    response_message_id = data.get("response_message_id")

    logger.info(f"📬 Начало рассылки: bot_id={bot_id}, users={len(user_ids)}")

    async with async_session() as session:
        result = await session.execute(
            select(Channel).options(joinedload(Channel.bot)).where(Channel.bot_id == bot_id).limit(1)
        )
        channel = result.scalar_one_or_none()

        if not channel or not channel.bot:
            logger.warning(f"⚠️ Bot not found in DB for bot_id={bot_id}")
            return

        token = channel.bot.token

    async with Bot(token=token, default=DEFAULT_PARSE_MODE) as bot:
        kb = None
        if button_text and button_url:
            kb = InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text=button_text, url=button_url)]]
            )

        # 🔍 Отбираем только доступных к рассылке
        filtered_user_ids = user_ids  # Уже отфильтрованы до отправки задачи

        total = len(filtered_user_ids)
        sent = 0
        failed = 0

        try:
            progress_msg = await bot.send_message(
                chat_id=response_chat_id,
                text="⏳ Начинаем рассылку...",
                reply_to_message_id=response_message_id
            )
        except Exception as e:
            logger.warning(f"⚠️ Не удалось отправить сообщение прогресса: {e}")
            progress_msg = None

        for i in range(0, total, CHUNK_SIZE):
            chunk = filtered_user_ids[i:i + CHUNK_SIZE]

            tasks = [
                send_to_user(bot, bot_id, user_id, text, kb)
                for user_id in chunk
            ]
            results = await asyncio.gather(*tasks)
            sent += sum(1 for r in results if r is True)
            failed += sum(1 for r in results if r is False)

            # 🔁 Обновление прогресса
            if progress_msg:
                try:
                    percent = int((sent + failed) / total * 100)
                    await bot.edit_message_text(
                        chat_id=progress_msg.chat.id,
                        message_id=progress_msg.message_id,
                        text=(
                            f"📊 <b>Рассылка выполняется...</b>\n\n"
                            f"✅ Отправлено: <b>{sent}</b>\n"
                            f"❌ Ошибок: <b>{failed}</b>\n"
                            f"📦 Всего: <b>{total}</b>\n"
                            f"📈 Прогресс: <b>{percent}%</b>"
                        )
                    )
                except TelegramBadRequest as e:
                    if "message is not modified" not in str(e):
                        logger.warning(f"⚠️ Ошибка обновления прогресса: {e}")

        logger.info(f"✅ Рассылка завершена. Успешно: {sent}, Ошибок: {failed}, Всего: {total}")

        if progress_msg:
            try:
                await bot.edit_message_text(
                    chat_id=progress_msg.chat.id,
                    message_id=progress_msg.message_id,
                    text=(
                        f"✅ <b>Рассылка завершена.</b>\n\n"
                        f"✅ Успешно доставлено: <b>{sent}</b>\n"
                        f"❌ Ошибок: <b>{failed}</b>\n"
                        f"📬 Всего: <b>{total}</b>"
                    )
                )
            except Exception as e:
                logger.warning(f"⚠️ Не удалось финализировать прогресс: {e}")


async def send_to_user(bot: Bot, bot_id: int, user_id: int, text: str, kb: InlineKeyboardMarkup | None) -> bool:
    async with semaphore:
        try:
            await bot.send_message(chat_id=user_id, text=text, reply_markup=kb)
            return True

        except TelegramRetryAfter as e:
            logger.warning(f"⏳ FloodWait: {e.retry_after}s for user {user_id}")
            await asyncio.sleep(e.retry_after)
            return await send_to_user(bot, bot_id, user_id, text, kb)

        except (TelegramForbiddenError, TelegramBadRequest) as e:
            logger.warning(f"❌ Telegram error for user {user_id}: {e}")
            if any(x in str(e).lower() for x in ["blocked", "forbidden", "deactivated"]):
                async with async_session() as session:
                    await session.execute(
                        update(ChannelMember)
                        .where(ChannelMember.user_id == user_id, ChannelMember.bot_id == bot_id)
                        .values(is_available_for_broadcast=False)
                    )
                    await session.commit()
                    logger.info(f"🛑 Пользователь {user_id} исключён из рассылок")
            return False

        except Exception as e:
            logger.warning(f"🔥 Unexpected error for user {user_id}: {e}")
            return False
