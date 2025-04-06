# workers/join_worker/worker.py

import asyncio
import json
import os
import time
from typing import Dict, List

from app.redis_queue.connection import redis
from app.utils.logger import logger
from workers.join_worker.services.join_handler import handle_join

# Константы для пакетной обработки
BATCH_SIZE = 20  # Максимальный размер пачки
BATCH_TIMEOUT = 1  # Максимальное время ожидания в секундах

# Настройки Redis из переменных окружения
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")


async def heartbeat(name: str):
    await redis.set(f"worker_status:{name}", int(time.time()))


async def process_batch(tasks: List[Dict]):
    """Обработка пачки задач"""
    if not tasks:
        return

    logger.info(f"📦 Processing batch of {len(tasks)} tasks")
    for task in tasks:
        asyncio.create_task(handle_join(task))


async def main():
    logger.info(f"🚀 Join worker started... (Redis: {REDIS_URL})")
    tasks_buffer = []
    last_batch_time = time.time()

    while True:
        try:
            # Получаем задачу с таймаутом
            task = await redis.blpop("join_queue", timeout=0.1)

            if task:
                _, data = task
                payload = json.loads(data)
                tasks_buffer.append(payload)

                # Если накопилось достаточно задач или прошло достаточно времени
                current_time = time.time()
                if len(tasks_buffer) >= BATCH_SIZE or (
                    tasks_buffer and current_time - last_batch_time >= BATCH_TIMEOUT
                ):
                    await process_batch(tasks_buffer)
                    tasks_buffer = []
                    last_batch_time = current_time
            else:
                # Если нет новых задач, но есть накопленные - обрабатываем их
                if tasks_buffer:
                    await process_batch(tasks_buffer)
                    tasks_buffer = []
                    last_batch_time = time.time()

            # Пульс всегда, даже если нет задач
            await heartbeat("join_worker:base")

        except Exception as e:
            logger.error(f"🔥 Error in worker loop: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
