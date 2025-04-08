import asyncio
import os

import docker
import redis.asyncio as aioredis
from dotenv import load_dotenv

load_dotenv(".env")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
SERVICE_NAME = "salute_broadcast_worker"
CHECK_INTERVAL = 10  # seconds
MAX_WORKERS = 5


async def get_queue_length():
    redis = await aioredis.from_url(REDIS_URL)
    length = await redis.llen("broadcast_tasks")
    await redis.close()
    return length


def scale_service(client, replicas):
    service = client.services.get(SERVICE_NAME)
    service.scale(replicas)
    print(f"🚀 Scaled {SERVICE_NAME} to {replicas} replicas")


async def auto_scale():
    client = docker.DockerClient(base_url="unix://var/run/docker.sock")

    while True:
        try:
            queue_length = await get_queue_length()
            service = client.services.get(SERVICE_NAME)
            current_replicas = service.attrs["Spec"]["Mode"]["Replicated"]["Replicas"]

            print(
                f"📊 Queue length: {queue_length} | Current replicas: {current_replicas}"
            )

            # Решаем, сколько нужно воркеров
            if queue_length > current_replicas and current_replicas < MAX_WORKERS:
                scale_service(client, min(current_replicas + 1, MAX_WORKERS))
            elif queue_length == 0 and current_replicas > 1:
                scale_service(client, 1)

        except Exception as e:
            print(f"⚠️ Error during scaling: {e}")

        await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    asyncio.run(auto_scale())
