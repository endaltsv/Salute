# app/redis_queue/connection.py
from redis.asyncio import Redis

redis = Redis(decode_responses=True)
