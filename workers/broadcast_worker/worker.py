import asyncio
import json
import time

from app.redis_queue.connection import redis
from app.utils.logger import logger
from workers.broadcast_worker.services.broadcast_handler import process_broadcast_task


async def heartbeat(name: str):
    await redis.set(f"worker_status:{name}", int(time.time()))


async def main():
    logger.info("📡 Universal Broadcast Worker started. Listening for any bot_id...")

    while True:
        try:
            keys = await redis.keys("broadcast_tasks:*")
            if not keys:
                await asyncio.sleep(0.5)
                continue

            for queue in keys:
                task = await redis.blpop(queue)
                if task:
                    _, raw_data = task
                    data = json.loads(raw_data)
                    logger.info(f"📥 Task from {queue}: {data}")
                    asyncio.create_task(process_broadcast_task(data))

            # ✅ Пингуем в Redis, чтобы manager знал что мы живы
            await heartbeat("broadcast_worker:universal")

        except Exception as e:
            logger.error(f"🔥 Error in universal broadcast worker: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
