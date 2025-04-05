import asyncio

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from app.database.base.session import async_session
from app.database.models.channel import Channel
from app.database.models.member import ChannelMember
from app.utils.logger import logger

DEFAULT_PARSE_MODE = DefaultBotProperties(parse_mode="HTML")

# В самом верху файла:
semaphore = asyncio.Semaphore(20)  # регулируй по нагрузке


async def handle_join(payload: dict):
    async with semaphore:
        user_id = payload["user_id"]
        chat_id = payload["chat_id"]
        bot_id = payload["bot_id"]

        logger.info(
            f"🚪 Join handler received: user_id={user_id}, chat_id={chat_id}, bot_id={bot_id}"
        )

        async with async_session() as session:
            result = await session.execute(
                select(Channel)
                .options(joinedload(Channel.bot))
                .where(Channel.channel_id == str(chat_id), Channel.bot_id == bot_id)
            )
            channel = result.scalar_one_or_none()

            if not channel:
                logger.warning(
                    f"⚠️ Channel not found for chat_id={chat_id}, bot_id={bot_id}"
                )
                return

            try:
                async with Bot(
                    token=channel.bot.token, default=DEFAULT_PARSE_MODE
                ) as bot:
                    await process_channel_join(bot, session, channel, user_id, chat_id)
            except Exception as e:
                logger.error(f"❌ Error processing bot_id={bot_id}: {e}")


async def process_channel_join(
    bot: Bot, session, channel: Channel, user_id: int, chat_id: int
):
    result = await session.execute(
        select(ChannelMember).where(
            ChannelMember.channel_id == channel.id,
            ChannelMember.user_id == user_id,
            ChannelMember.bot_id == channel.bot_id,
        )
    )
    member = result.scalar_one_or_none()

    if member:
        logger.info(f"ℹ️ Member already in DB for bot_id={channel.bot_id}")

        try:
            await schedule_auto_approve(bot, channel, chat_id, user_id)
            logger.info(f"✅ Approved (existing member) user {user_id}")
        except Exception as e:
            logger.warning(f"⚠️ Could not approve existing member: {e}")

        if channel.welcome_message:
            await send_welcome(bot, user_id, channel)
        return

    if channel.captcha_enabled:
        if not member or member.is_available_for_broadcast is False:
            kb = None
            if channel.captcha_has_button and channel.captcha_button_text:
                kb = ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text=channel.captcha_button_text)]],
                    resize_keyboard=True,
                    one_time_keyboard=True,
                )
            await bot.send_message(
                chat_id=user_id,
                text=channel.captcha_text
                or "Пожалуйста, подтвердите, что вы не робот:",
                reply_markup=kb,
            )

    new_member = ChannelMember(
        channel_id=channel.id, user_id=user_id, bot_id=channel.bot_id
    )
    session.add(new_member)
    try:
        await session.commit()
        logger.info(f"📜 Added new member: user_id={user_id}, channel_id={channel.id}")
    except IntegrityError:
        await session.rollback()
        logger.info(f"ℹ️ Member already exists (commit): user_id={user_id}")

    if channel.welcome_message:
        await send_welcome(bot, user_id, channel)

    await schedule_auto_approve(bot, channel, chat_id, user_id)


async def send_welcome(bot: Bot, user_id: int, channel: Channel):
    kb = None
    if not channel.welcome_enabled:
        return
    if channel.has_button:
        if (
            channel.button_type == "inline"
            and channel.button_text
            and channel.button_url
        ):
            kb = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text=channel.button_text, url=channel.button_url
                        )
                    ]
                ]
            )
        elif channel.button_type == "reply" and channel.button_text:
            kb = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=channel.button_text)]],
                resize_keyboard=True,
                one_time_keyboard=True,
            )

    await bot.send_message(
        chat_id=user_id, text=channel.welcome_message, reply_markup=kb
    )


async def schedule_auto_approve(bot: Bot, channel: Channel, chat_id: int, user_id: int):
    mode = channel.auto_approve_mode
    if mode == "instant":
        try:
            await bot.approve_chat_join_request(chat_id, user_id)
            logger.info(f"✅ Instantly approved user {user_id}")
        except Exception as e:
            logger.warning(f"❌ Failed to instantly approve user: {e}")
    elif mode == "1min":
        asyncio.create_task(auto_approve(bot.token, chat_id, user_id, 60))
    elif mode == "5min":
        asyncio.create_task(auto_approve(bot.token, chat_id, user_id, 300))
    elif mode and mode.endswith("s"):
        try:
            delay = int(mode[:-1])
            asyncio.create_task(auto_approve(bot.token, chat_id, user_id, delay))
        except ValueError:
            logger.error(f"❌ Invalid delay format: {mode}")


async def auto_approve(bot_token: str, chat_id: int, user_id: int, delay: int):
    logger.info(f"⏱ Waiting {delay}s before approving user")
    await asyncio.sleep(delay)
    try:
        async with Bot(token=bot_token, default=DEFAULT_PARSE_MODE) as bot:
            await bot.approve_chat_join_request(chat_id, user_id)
            logger.info(
                f"✅ Approved join request for user {user_id} in chat {chat_id}"
            )
    except Exception as e:
        logger.error(f"❌ Error approving join request: {e}")
