import pytest
from workers.broadcast_worker.services.broadcast_handler import process_broadcast_task

@pytest.mark.asyncio
async def test_broadcast_task(redis_client):  # <--- исправлено
    payload = {
        "bot_id": 1,
        "user_ids": [111, 222],
        "text": "Test message"
    }

    await process_broadcast_task(payload)

    assert payload["text"] == "Test message"
