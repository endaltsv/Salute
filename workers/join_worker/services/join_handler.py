import asyncio

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from sqlalchemy import select, tuple_
from sqlalchemy.exc import IntegrityError

from app.database.base.session import async_session
from app.database.models.member import ChannelMember
from app.utils.logger import logger
from workers.join_worker.services.bot_cache import get_bot
from workers.join_worker.services.channel_cache import get_channel, get_channels_bulk


async def handle_join_batch(payloads: list):
    if not payloads:
        return

    async with async_session() as session:
        keys = set((p["chat_id"], p["user_id"], p["bot_id"]) for p in payloads)

        channels = await get_channels_bulk([
            (chat_id, bot_id)
            for chat_id, _, bot_id in keys
        ])

        # Получаем ботов (если get_bot у тебя sync — оставляем так, иначе тоже надо переписать)
        bots = {bot_id: get_bot(bot_id) for _, _, bot_id in keys}

        existing_members_result = await session.execute(
            select(ChannelMember).where(
                tuple_(
                    ChannelMember.channel_id,
                    ChannelMember.user_id,
                    ChannelMember.bot_id,
                ).in_(
                    [
                        (channels.get((chat_id, bot_id))["id"], user_id, bot_id)
                        for chat_id, user_id, bot_id in keys
                        if channels.get((chat_id, bot_id))
                    ]
                )
            )
        )
        existing_members = set(
            (m.channel_id, m.user_id, m.bot_id)
            for m in existing_members_result.scalars().all()
        )

        new_members = []

        tasks = []
        for payload in payloads:
            tasks.append(process_payload(payload, channels, bots, existing_members, new_members))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"⚠️ Exception in process_payload: {result}")

        if new_members:
            try:
                session.add_all(new_members)
                await session.commit()
                logger.info(f"📦 Bulk inserted {len(new_members)} members")
            except IntegrityError:
                await session.rollback()
                logger.warning(f"⚠️ Bulk insert failed due to IntegrityError")



async def process_payload(payload, channels, bots, existing_members, new_members):
    user_id = payload["user_id"]
    chat_id = payload["chat_id"]
    bot_id = payload["bot_id"]

    channel = channels.get((chat_id, bot_id))
    bot = bots.get(bot_id)

    if not channel or not bot:
        logger.warning(
            f"⚠️ Channel or Bot not found for chat_id={chat_id}, bot_id={bot_id}"
        )
        return

    member_key = (channel["id"], user_id, bot_id)

    if member_key in existing_members:
        logger.info(
            f"ℹ️ Member already in DB: user_id={user_id}, bot_id={bot_id}"
        )
        await approve_and_welcome(bot, channel, chat_id, user_id)
        return

    if channel["captcha_enabled"]:
        await send_captcha(bot, user_id, channel)

    new_members.append(
        ChannelMember(
            channel_id=channel["id"], user_id=user_id, bot_id=bot_id
        )
    )

    await approve_and_welcome(bot, channel, chat_id, user_id)


async def approve_and_welcome(bot, channel, chat_id, user_id):
    try:
        await safe_approve(bot, channel, chat_id, user_id)

        if channel["welcome_enabled"]:
            await send_welcome(bot, user_id, channel)
    except Exception as e:
        logger.warning(f"⚠️ approve_and_welcome failed: {e}")


async def send_captcha(bot, user_id: int, channel):
    try:
        kb = None
        if channel["captcha_has_button"] and channel["captcha_button_text"]:
            kb = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=channel["captcha_button_text"])]],
                resize_keyboard=True,
                one_time_keyboard=True,
            )
        await bot.send_message(
            chat_id=user_id,
            text=channel["captcha_text"] or "Пожалуйста, подтвердите, что вы не робот:",
            reply_markup=kb,
        )
    except Exception as e:
        logger.warning(f"⚠️ Failed to send captcha to user {user_id}: {e}")


async def send_welcome(bot, user_id: int, channel):
    try:
        kb = None
        if channel["has_button"]:
            if (
                    channel["button_type"] == "inline"
                    and channel["button_text"]
                    and channel["button_url"]
            ):
                kb = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text=channel["button_text"], url=channel["button_url"]
                            )
                        ]
                    ]
                )
            elif channel["button_type"] == "reply" and channel["button_text"]:
                kb = ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text=channel["button_text"])]],
                    resize_keyboard=True,
                    one_time_keyboard=True,
                )

        await bot.send_message(
            chat_id=user_id, text=channel["welcome_message"], reply_markup=kb
        )
    except Exception as e:
        logger.warning(f"⚠️ Failed to send welcome to user {user_id}: {e}")


async def safe_approve(bot, channel, chat_id, user_id):
    try:
        mode = channel["auto_approve_mode"]
        if mode == "instant":
            await try_approve(bot, chat_id, user_id)
        elif mode == "1min":
            asyncio.create_task(delayed_approve(bot, chat_id, user_id, 60))
        elif mode == "5min":
            asyncio.create_task(delayed_approve(bot, chat_id, user_id, 300))
        elif mode and mode.endswith("s"):
            try:
                delay = int(mode[:-1])
                asyncio.create_task(delayed_approve(bot, chat_id, user_id, delay))
            except ValueError:
                logger.error(f"❌ Invalid delay format: {mode}")
    except Exception as e:
        logger.warning(f"⚠️ safe_approve failed: {e}")


async def delayed_approve(bot, chat_id: int, user_id: int, delay: int):
    logger.info(f"⏱ Waiting {delay}s before approving user")
    await asyncio.sleep(delay)
    await try_approve(bot, chat_id, user_id)


async def try_approve(bot, chat_id: int, user_id: int):
    try:
        await bot.approve_chat_join_request(chat_id, user_id)
        logger.info(f"✅ Approved join request for user {user_id} in chat {chat_id}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to approve user: {e}")
