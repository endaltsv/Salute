# greeter_runner.py
import os
import asyncio
from app.greeter_bots.core.launcher import run_greeter_bot


async def main():
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("❌ BOT_TOKEN не найден в переменных окружения")
    await run_greeter_bot(token)


if __name__ == "__main__":
    asyncio.run(main())
