import asyncio
import json
import os
import time

from redis.asyncio import Redis

from app.utils.logger import logger
from workers.log_worker.services.log_handler import flush_logs, handle_log_entry

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
redis_client = Redis.from_url(REDIS_URL, decode_responses=True)


async def heartbeat(name: str):
    await redis_client.set(f"worker_status:{name}", int(time.time()))


async def periodic_flush(interval: int = 5):
    while True:
        try:
            await flush_logs()
        except Exception as e:
            logger.warning(f"⚠️ Ошибка во время flush_logs: {e}")
        await asyncio.sleep(interval)


async def main():
    logger.info("🧾 Log worker запущен...")

    # 🔄 Запускаем фоновую задачу на регулярную отправку логов
    asyncio.create_task(periodic_flush())

    while True:
        try:
            task = await redis_client.blpop("admin_logs", timeout=1)
            if task:
                _, raw_data = task
                log_data = json.loads(raw_data)
                logger.info(f"📨 Получен лог: {log_data}")
                asyncio.create_task(handle_log_entry(log_data))

            await heartbeat("log_worker:base")

        except Exception as e:
            logger.exception(f"🔥 Ошибка в log worker loop: {e}")
            await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())
