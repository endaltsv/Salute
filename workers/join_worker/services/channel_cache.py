# workers/join_worker/services/channel_cache.py
from app.database.base.session import async_session
from app.database.models.channel import Channel
from app.utils.logger import logger

channel_cache = {}


async def init_channel_cache():
    logger.info("🔄 Initializing channel cache...")
    async with async_session() as session:
        result = await session.execute(Channel.__table__.select())
        channels = result.fetchall()

        for row in channels:
            key = (row.channel_id, row.bot_id)
            channel_cache[key] = {
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

    logger.info(f"✅ Cached {len(channel_cache)} channels")


def get_channel(channel_id: str, bot_id: int):
    return channel_cache.get((channel_id, bot_id))
