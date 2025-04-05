# app/redis_queue/admin_log.py

import json

from app.redis_queue.connection import redis


async def send_log_to_admin(text: str, level: str = "info"):
    """Кладёт лог в Redis, откуда его заберёт воркер"""
    await redis.rpush("admin_logs", json.dumps({"message": text, "level": level}))
