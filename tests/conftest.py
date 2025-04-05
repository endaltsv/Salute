# tests/conftest.py

import pytest
import asyncio
from dotenv import load_dotenv
from redis.asyncio import Redis

load_dotenv(".env")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def redis_client(event_loop):
    """
    Synchronous fixture that returns an async Redis client.
    We manually run async init/cleanup using event_loop.
    """
    client = Redis(decode_responses=True)

    # Инициализация (flushdb)
    event_loop.run_until_complete(client.flushdb())

    yield client  # <-- возвращаем сам объект Redis

    # Очистка (flushdb, close)
    async def cleanup():
        await client.flushdb()
        await client.close()

    event_loop.run_until_complete(cleanup())
