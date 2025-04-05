async def get_channel_by_id(channel_id: int):
    async with SessionLocal() as session:
        result = await session.execute(select(Channel).where(Channel.channel_id == channel_id))
        return result.scalars().first()

async def update_channel_field(channel_id: int, field: str, value):
    async with SessionLocal() as session:
        await session.execute(
            update(Channel).where(Channel.channel_id == channel_id).values({field: value})
        )
        await session.commit()
