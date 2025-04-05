# workers/join_worker/worker.py

import asyncio
import json
import time

from app.redis_queue.connection import redis
from app.utils.logger import logger
from workers.join_worker.services.join_handler import handle_join


async def heartbeat(name: str):
    await redis.set(f"worker_status:{name}", int(time.time()))


async def main():
    logger.info("🚀 Join worker started...")

    while True:
        try:
            task = await redis.blpop("join_queue", timeout=1)
            if task:
                _, data = task
                payload = json.loads(data)
                logger.info(f"📦 Task received: {payload}")
                asyncio.create_task(handle_join(payload))

            # Пульс всегда, даже если нет задач
            await heartbeat("join_worker:base")

        except Exception as e:
            logger.error(f"🔥 Error in worker loop: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
