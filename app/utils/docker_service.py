import docker
import os
from app.utils.logger import logger


def create_greeter_service(bot_id: int, token: str):
    client = docker.from_env()

    service_name = f"salute_greeter_{bot_id}"
    image = "salute_manager"  # универсальный образ
    network = "salute_default"  # swarm-сеть

    env_vars = [
        f"BOT_TOKEN={token}",
        "PYTHONUNBUFFERED=1",
        "PYTHONPATH=/app",
    ]

    command = ["python", "greeter_runner.py"]

    try:
        client.services.create(
            name=service_name,
            image=image,
            command=command,
            env=env_vars,
            networks=[network],
            restart_policy=docker.types.RestartPolicy(condition="any"),
        )
        logger.info(f"✅ Greeter service {service_name} created.")
    except docker.errors.APIError as e:
        logger.error(f"❌ Failed to create service {service_name}: {e.explanation}")
