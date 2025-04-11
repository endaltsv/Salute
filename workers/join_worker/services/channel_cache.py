import asyncio
import json

from sqlalchemy import select

from app.database.base.session import async_session
from app.database.models.channel import Channel
from app.redis_queue.connection import redis
from app.utils.logger import logger


# 🔥 Ключи в Redis будем хранить в виде: channel:{bot_id}:{channel_id}
def _make_redis_key(channel_id: int, bot_id: int):
    return f"channel:{bot_id}:{channel_id}"


async def init_channel_cache():
    logger.info("🔄 Initializing channel cache...")

    async with async_session() as session:
        result = await session.execute(Channel.__table__.select())
        channels = result.fetchall()

        pipe = redis.pipeline()

        for row in channels:
            key = _make_redis_key(row.channel_id, row.bot_id)
            channel_data = {
                "id": row.id,
                "channel_id": row.channel_id,
                "channel_name": row.channel_name,
                "bot_id": row.bot_id,
                "welcome_enabled": row.welcome_enabled,
                "welcome_message": row.welcome_message,
                "has_button": row.has_button,
                "button_type": row.button_type,
                "button_text": row.button_text,
                "button_url": row.button_url,
                "captcha_enabled": row.captcha_enabled,
                "captcha_text": row.captcha_text,
                "captcha_has_button": row.captcha_has_button,
                "captcha_button_text": row.captcha_button_text,
                "captcha_only_for_new_users": row.captcha_only_for_new_users,
                "auto_approve_mode": row.auto_approve_mode,
            }

            pipe.set(key, json.dumps(channel_data))

        await pipe.execute()

    logger.info(f"✅ Cached {len(channels)} channels in Redis")


async def update_channel_in_cache(channel_id: int, bot_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(Channel).where(Channel.channel_id == channel_id, Channel.bot_id == bot_id)
        )
        channel = result.scalar_one_or_none()

        if channel:
            key = _make_redis_key(channel_id, bot_id)
            channel_data = {
                "id": channel.id,
                "channel_id": channel.channel_id,
                "channel_name": channel.channel_name,
                "bot_id": channel.bot_id,
                "welcome_enabled": channel.welcome_enabled,
                "welcome_message": channel.welcome_message,
                "has_button": channel.has_button,
                "button_type": channel.button_type,
                "button_text": channel.button_text,
                "button_url": channel.button_url,
                "captcha_enabled": channel.captcha_enabled,
                "captcha_text": channel.captcha_text,
                "captcha_has_button": channel.captcha_has_button,
                "captcha_button_text": channel.captcha_button_text,
                "captcha_only_for_new_users": channel.captcha_only_for_new_users,
                "auto_approve_mode": channel.auto_approve_mode,
            }

            await redis.set(key, json.dumps(channel_data))
            logger.info(f"🧩 Обновили кеш канала (channel_id={channel_id}, bot_id={bot_id}) в Redis")


async def get_channel(channel_id: int, bot_id: int):
    key = _make_redis_key(channel_id, bot_id)
    data = await redis.get(key)
    if data:
        return json.loads(data)
    logger.warning(f"⚠️ Канал не найден в Redis кеш: {key}")
    return None


async def get_channels_bulk(pairs: list[tuple[int, int]]) -> dict:
    keys = [_make_redis_key(channel_id, bot_id) for channel_id, bot_id in pairs]
    results = await redis.mget(*keys)

    channels = {}
    for (channel_id, bot_id), data in zip(pairs, results):
        if data:
            channels[(channel_id, bot_id)] = json.loads(data)
        else:
            logger.warning(f"⚠️ Канал не найден в Redis кеш: channel_id={channel_id}, bot_id={bot_id}")
    return channels


async def remove_channel_from_cache(channel_id: int, bot_id: int):
    key = _make_redis_key(channel_id, bot_id)
    result = await redis.delete(key)

    if result:
        logger.info(f"🧹 Канал (ID={channel_id}, bot_id={bot_id}) удалён из кеша Redis")
    else:
        logger.warning(f"⚠️ Пытались удалить канал (ID={channel_id}, bot_id={bot_id}), но его не было в кеш Redis")
