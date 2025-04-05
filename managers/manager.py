import asyncio
import os
import signal
import sys
import time

from app.redis_queue.connection import redis
from app.utils.logger import logger

CHECK_INTERVAL = 5
INACTIVITY_TIMEOUT = 60
HEALTH_TIMEOUT = 30
MAX_EXTRA_BROADCAST_WORKERS = 5
MAX_EXTRA_JOIN_WORKERS = 3


class WorkerManager:
    def __init__(self):
        self.running_workers = {}  # key: name, value: (process, last_active)

    async def monitor(self):
        logger.info("📡 Worker Manager запущен...")

        await self.ensure_main_bot()

        while True:
            await self.ensure_base_workers()
            await self.check_broadcast_queues()
            await self.check_join_queue()
            await self.cleanup_inactive_workers()
            await self.check_health_status()
            await self.restart_failed_workers()
            await asyncio.sleep(CHECK_INTERVAL)

    async def ensure_main_bot(self):
        key = "main_bot"
        if key not in self.running_workers:
            logger.info("🤖 Запуск главного бота main.py...")
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "main.py", env=os.environ.copy()
            )
            self.running_workers[key] = (proc, asyncio.get_event_loop().time())

    async def ensure_base_workers(self):
        # 🔸 log_worker
        log_key = "log_worker:base"
        if log_key not in self.running_workers:
            logger.info("🧾 Запуск log_worker...")
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "workers/log_worker/worker.py", env=os.environ.copy()
            )
            self.running_workers[log_key] = (proc, asyncio.get_event_loop().time())

        # 🔸 join_worker (base)
        join_key = "join_worker:base"
        if join_key not in self.running_workers:
            logger.info("🚪 Запуск базового join_worker...")
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "workers/join_worker/worker.py", env=os.environ.copy()
            )
            self.running_workers[join_key] = (proc, asyncio.get_event_loop().time())

    async def check_broadcast_queues(self):
        keys = await redis.keys("broadcast_tasks:*")
        for key in keys:
            bot_id = key.split(":")[-1]
            base_key = f"broadcast_worker:{bot_id}:base"

            if base_key not in self.running_workers:
                logger.info(f"🚀 Запуск базового broadcast_worker для bot_id={bot_id}")
                proc = await asyncio.create_subprocess_exec(
                    sys.executable,
                    "workers/broadcast_worker/worker.py",
                    bot_id,
                    env=os.environ.copy(),
                )
                self.running_workers[base_key] = (proc, asyncio.get_event_loop().time())

            queue_length = await redis.llen(key)
            active_extras = [
                k
                for k in self.running_workers
                if k.startswith(f"broadcast_worker:{bot_id}:extra")
            ]
            total_running = 1 + len(active_extras)

            if (
                queue_length > total_running
                and len(active_extras) < MAX_EXTRA_BROADCAST_WORKERS
            ):
                extra_id = len(active_extras) + 1
                extra_key = f"broadcast_worker:{bot_id}:extra{extra_id}"
                logger.info(
                    f"⚡ Запуск доп. broadcast_worker {extra_key} "
                    f"(очередь: {queue_length}, всего: {total_running})"
                )
                proc = await asyncio.create_subprocess_exec(
                    sys.executable,
                    "workers/broadcast_worker/worker.py",
                    bot_id,
                    env=os.environ.copy(),
                )
                self.running_workers[extra_key] = (
                    proc,
                    asyncio.get_event_loop().time(),
                )

            for k in [base_key] + active_extras:
                self.running_workers[k] = (
                    self.running_workers[k][0],
                    asyncio.get_event_loop().time(),
                )

    async def check_join_queue(self):
        queue_length = await redis.llen("join_queue")
        base_key = "join_worker:base"

        if base_key in self.running_workers and queue_length > 0:
            self.running_workers[base_key] = (
                self.running_workers[base_key][0],
                asyncio.get_event_loop().time(),
            )

        active_extras = [
            k for k in self.running_workers if k.startswith("join_worker:extra")
        ]
        total_running = 1 + len(active_extras)

        if queue_length > total_running and len(active_extras) < MAX_EXTRA_JOIN_WORKERS:
            extra_id = len(active_extras) + 1
            extra_key = f"join_worker:extra{extra_id}"
            logger.info(
                f"⚡ Запуск доп. join_worker {extra_key} "
                f"(очередь: {queue_length}, всего: {total_running})"
            )
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "workers/join_worker/worker.py", env=os.environ.copy()
            )
            self.running_workers[extra_key] = (proc, asyncio.get_event_loop().time())

        for k in [base_key] + active_extras:
            self.running_workers[k] = (
                self.running_workers[k][0],
                asyncio.get_event_loop().time(),
            )

    async def cleanup_inactive_workers(self):
        now = asyncio.get_event_loop().time()
        to_remove = []

        for key, (proc, last_active) in self.running_workers.items():
            if "base" in key or "log_worker" in key or key == "main_bot":
                continue
            if now - last_active > INACTIVITY_TIMEOUT:
                logger.info(f"🛑 Завершение неактивного воркера: {key}")
                try:
                    proc.send_signal(signal.SIGTERM)
                    await proc.wait()
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось завершить {key}: {e}")
                to_remove.append(key)

        for key in to_remove:
            self.running_workers.pop(key)

    async def check_health_status(self):
        now = int(time.time())
        for key in list(self.running_workers.keys()):
            if key == "main_bot":
                continue
            last_ping = await redis.get(f"worker_status:{key}")
            if last_ping and now - int(last_ping) > HEALTH_TIMEOUT:
                logger.warning(
                    f"🧟 Воркер {key} давно не пинговал "
                    f"({now - int(last_ping)}s). Рестарт..."
                )
                proc = self.running_workers[key][0]
                try:
                    proc.send_signal(signal.SIGTERM)
                    await proc.wait()
                except Exception:
                    pass
                self.running_workers.pop(key)

    async def restart_failed_workers(self):
        for key, (proc, _) in list(self.running_workers.items()):
            if proc.returncode is not None and key != "main_bot":
                logger.warning(
                    f"💥 Воркер {key} завершился с кодом {proc.returncode}. "
                    f"Перезапуск..."
                )
                try:
                    await proc.wait()
                except Exception:
                    pass
                self.running_workers.pop(key)

                args = []
                if key == "log_worker:base":
                    args = ["workers/log_worker/worker.py"]
                elif key == "join_worker:base" or key.startswith("join_worker:extra"):
                    args = ["workers/join_worker/worker.py"]
                elif key.startswith("broadcast_worker:"):
                    parts = key.split(":")
                    args = ["workers/broadcast_worker/worker.py", parts[1]]

                if args:
                    proc = await asyncio.create_subprocess_exec(
                        sys.executable, *args, env=os.environ.copy()
                    )
                    self.running_workers[key] = (proc, asyncio.get_event_loop().time())


if __name__ == "__main__":
    manager = WorkerManager()
    asyncio.run(manager.monitor())
