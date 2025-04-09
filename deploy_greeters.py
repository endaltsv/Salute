import asyncio
import docker
from sqlalchemy import select
from app.database.base.session import async_session
from app.database.models.bot import Bot as BotModel
from app.utils.docker_service import create_greeter_service

async def main():
    client = docker.from_env()

    existing_services = {service.name for service in client.services.list()}

    async with async_session() as session:
        result = await session.execute(select(BotModel))
        bots = result.scalars().all()

        for bot in bots:
            service_name = f"salute_greeter_{bot.id}"
            if service_name not in existing_services:
                create_greeter_service(bot.id, bot.token)
            else:
                print(f"✅ Service {service_name} already running.")

if __name__ == "__main__":
    asyncio.run(main())
