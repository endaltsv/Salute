import asyncio
from redis.asyncio import Redis


async def main():
    redis = Redis.from_url("redis://localhost")
    await redis.set("test_key", "hello")
    value = await redis.get("test_key")
    print(f"🔁 Redis value: {value.decode()}")


asyncio.run(main())
