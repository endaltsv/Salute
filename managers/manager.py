import asyncio
import os

import docker
from docker.errors import APIError

from app.redis_queue.connection import redis
from app.utils.logger import logger

CHECK_INTERVAL = 5
INACTIVITY_TIMEOUT = 60
HEALTH_TIMEOUT = 30
MAX_EXTRA_BROADCAST_WORKERS = 5


class DockerWorkerManager:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.running_workers = {}  # key: name, value: container_id
        self.image_name = "salute_manager"
        self.network_name = "salute_default"  # Имя сети Docker Compose

    async def monitor(self):
        logger.info("📡 Docker Worker Manager запущен...")

        while True:
            try:
                await self.ensure_base_workers()
                await self.check_broadcast_queues()
                await self.cleanup_inactive_workers()
                await asyncio.sleep(CHECK_INTERVAL)
            except Exception as e:
                logger.error(f"Ошибка в мониторе: {e}")
                await asyncio.sleep(CHECK_INTERVAL)

    async def ensure_base_workers(self):
        # 🔸 log_worker
        if "log_worker" not in self.running_workers:
            try:
                container = self.docker_client.containers.run(
                    self.image_name,
                    command="python workers/log_worker/worker.py",
                    environment=self._get_environment(),
                    volumes=self._get_volumes(),
                    network=self.network_name,
                    detach=True,
                    restart_policy={"Name": "unless-stopped"},
                )
                self.running_workers["log_worker"] = container.id
                logger.info("🧾 Запущен log_worker")
            except APIError as e:
                logger.error(f"Ошибка запуска log_worker: {e}")

        # 🔸 broadcast_worker
        if "broadcast_worker" not in self.running_workers:
            try:
                container = self.docker_client.containers.run(
                    self.image_name,
                    command="python workers/broadcast_worker/worker.py",
                    environment=self._get_environment(),
                    volumes=self._get_volumes(),
                    network=self.network_name,
                    detach=True,
                    restart_policy={"Name": "unless-stopped"},
                )
                self.running_workers["broadcast_worker"] = container.id
                logger.info("🚀 Запущен broadcast_worker")
            except APIError as e:
                logger.error(f"Ошибка запуска broadcast_worker: {e}")

    async def check_broadcast_queues(self):
        try:
            keys = await redis.keys("broadcast_tasks:*")
            for key in keys:
                bot_id = key.split(":")[-1]
                worker_name = f"broadcast_worker_{bot_id}"

                queue_length = await redis.llen(key)
                current_workers = len(
                    [
                        k
                        for k in self.running_workers
                        if k.startswith(f"broadcast_worker_{bot_id}")
                    ]
                )

                if (
                    queue_length > current_workers
                    and current_workers < MAX_EXTRA_BROADCAST_WORKERS
                ):
                    try:
                        container = self.docker_client.containers.run(
                            "salute_broadcast_worker",
                            command=f"python workers/broadcast_worker/worker.py {bot_id}",
                            name=f"salute_broadcast_worker_{bot_id}_{current_workers}",
                            environment=self._get_environment(),
                            volumes=self._get_volumes(),
                            network=self.network_name,
                            detach=True,
                            restart_policy={"Name": "unless-stopped"},
                        )
                        self.running_workers[f"{worker_name}_{current_workers}"] = (
                            container.id
                        )
                        logger.info(f"🚀 Запущен broadcast_worker для bot_id={bot_id}")
                    except APIError as e:
                        logger.error(f"Ошибка запуска broadcast_worker: {e}")
        except Exception as e:
            logger.error(f"Ошибка проверки broadcast очередей: {e}")

    async def cleanup_inactive_workers(self):
        try:
            for worker_name, container_id in list(self.running_workers.items()):
                try:
                    container = self.docker_client.containers.get(container_id)
                    if container.status != "running":
                        logger.info(f"🛑 Удаление неактивного воркера: {worker_name}")
                        container.remove(force=True)
                        del self.running_workers[worker_name]
                except docker.errors.NotFound:
                    del self.running_workers[worker_name]
        except Exception as e:
            logger.error(f"Ошибка очистки неактивных воркеров: {e}")

    def _get_environment(self):
        return {
            "DATABASE_URL": os.getenv("DATABASE_URL"),
            "ALEMBIC_DATABASE_URL": os.getenv("ALEMBIC_DATABASE_URL"),
            "BOT_TOKEN": os.getenv("BOT_TOKEN"),
            "ADMIN_CHAT_ID": os.getenv("ADMIN_CHAT_ID"),
            "SUPPORT_USERNAME": os.getenv("SUPPORT_USERNAME"),
            "REDIS_URL": os.getenv("REDIS_URL"),
        }

    def _get_volumes(self):
        return {f"{os.getcwd()}/logs": {"bind": "/app/logs", "mode": "rw"}}


if __name__ == "__main__":
    manager = DockerWorkerManager()
    asyncio.run(manager.monitor())
