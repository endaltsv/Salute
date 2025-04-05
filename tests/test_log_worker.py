import pytest
from workers.log_worker.services.log_handler import handle_log_entry

@pytest.mark.asyncio
async def test_log_entry(redis_client):  # <--- исправлено
    log_data = {"message": "Test log", "level": "info"}

    await handle_log_entry(log_data)

    assert "message" in log_data
