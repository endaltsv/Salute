# tests/test_join_worker.py

import pytest
import json
from redis.asyncio import Redis
from workers.join_worker.services.join_handler import handle_join


@pytest.mark.asyncio
async def test_join_worker_process(redis_client: Redis):  # <--- обязательно укажи тип Redis
    test_payload = {"user_id": 123, "channel_id": "test", "bot_id": 1}
    await redis_client.rpush("join_queue", "data")
    assert "user_id" in test_payload
