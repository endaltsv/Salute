# workers/join_worker/worker.py

import asyncio
import json
import os
import time
from typing import Dict, List

from app.redis_queue.connection import redis
from app.utils.logger import logger
from workers.join_worker.services.bot_cache import init_bot_cache
from workers.join_worker.services.channel_cache import init_channel_cache
from workers.join_worker.services.join_handler import handle_join_batch

BATCH_SIZE = 200
BATCH_TIMEOUT = 1
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


async def heartbeat(name: str):
    await redis.set(f"worker_status:{name}", int(time.time()))


async def refresh_caches():
    while True:
        try:
            logger.info("🔄 Refreshing caches...")
            await init_bot_cache()
            await init_channel_cache()
            logger.info("✅ Caches refreshed successfully")
        except Exception as e:
            logger.error(f"❌ Failed to refresh caches: {e}")
        await asyncio.sleep(20)  # Обновляем раз в 60 секунд


async def process_batch(tasks: List[Dict]):
    if not tasks:
        return

    logger.info(f"📦 Processing batch of {len(tasks)} tasks")
    await handle_join_batch(tasks)


async def main():
    logger.info(f"🚀 Join worker started... (Redis: {REDIS_URL})")

    # Init caches
    await init_bot_cache()
    await init_channel_cache()

    # Запускаем фоновую задачу обновления кэша
    asyncio.create_task(refresh_caches())

    tasks_buffer = []
    last_batch_time = time.time()

    while True:
        try:
            task = await redis.blpop("join_queue", timeout=0.1)

            if task:
                _, data = task
                payload = json.loads(data)
                tasks_buffer.append(payload)

                current_time = time.time()
                if len(tasks_buffer) >= BATCH_SIZE or (
                    tasks_buffer and current_time - last_batch_time >= BATCH_TIMEOUT
                ):
                    await process_batch(tasks_buffer)
                    tasks_buffer = []
                    last_batch_time = current_time
            else:
                if tasks_buffer:
                    await process_batch(tasks_buffer)
                    tasks_buffer = []
                    last_batch_time = time.time()

            await heartbeat("join_worker:base")

        except Exception as e:
            logger.error(f"🔥 Error in worker loop: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
