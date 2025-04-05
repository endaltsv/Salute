# app/redis_queue/admin_log.py

import os
import json
from redis.asyncio import Redis

redis = Redis.from_url(os.getenv("REDIS_URL", "redis://localhost"))


async def send_log_to_admin(text: str, level: str = "info"):
    """Кладёт лог в Redis, откуда его заберёт воркер"""
    await redis.rpush("admin_logs", json.dumps({
        "message": text,
        "level": level
    }))
