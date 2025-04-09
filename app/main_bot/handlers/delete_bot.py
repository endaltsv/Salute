from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, delete
from app.database.base.session import async_session
from app.database.models.bot import Bot as BotModel
from app.database.models.channel import Channel
from app.database.models.member import ChannelMember
from app.utils.logger import logger
import docker

router = Router()


@router.callback_query(F.data.startswith("delete_bot:"))
async def delete_bot(callback: types.CallbackQuery, state: FSMContext):
    bot_id = int(callback.data.split(":")[1])

    async with async_session() as session:
        result = await session.execute(select(BotModel).where(BotModel.id == bot_id))
        bot = result.scalar_one_or_none()

        if not bot:
            await callback.message.answer("❌ Бот не найден в базе данных.")
            logger.warning(f"❌ Попытка удалить несуществующего бота с ID {bot_id} от пользователя {callback.from_user.id}")
            return

        token = bot.token
        username = bot.name

        logger.info(f"🔄 Начато удаление бота @{username} (ID: {bot_id}) пользователем {callback.from_user.id}")

        # 🧹 1. Удаляем участников всех каналов этого бота
        result = await session.execute(select(Channel).where(Channel.bot_id == bot.id))
        channels = result.scalars().all()
        channel_ids = [ch.id for ch in channels]

        if channel_ids:
            await session.execute(delete(ChannelMember).where(ChannelMember.channel_id.in_(channel_ids)))
            logger.info(f"🧼 Удалены участники каналов: {channel_ids} (бот @{username})")

        # 🧹 2. Удаляем каналы бота
        await session.execute(delete(Channel).where(Channel.bot_id == bot.id))
        logger.info(f"📤 Удалены все каналы бота @{username}")

        # 🧹 3. Удаляем самого бота
        await session.delete(bot)
        await session.commit()
        logger.info(f"✅ Бот @{username} удалён из базы (ID: {bot_id})")

        # 🛑 4. Удаляем greeter-сервис Docker
        deleted = remove_docker_service(bot_id)
        if deleted:
            logger.info(f"🛑 Greeter-сервис @{username} успешно удалён")
        else:
            logger.warning(f"⚠ Не найден Docker-сервис для @{username} (bot_id={bot_id})")

        await callback.message.answer(f"✅ Бот @{username} удалён.")
        await callback.answer()


def remove_docker_service(bot_id: int) -> bool:
    """Удаляет Docker-сервис greeter-бота по bot_id"""
    service_name = f"salute_greeter_{bot_id}"
    client = docker.from_env()

    try:
        service = client.services.get(service_name)
        service.remove()
        return True
    except docker.errors.NotFound:
        return False
    except docker.errors.APIError as e:
        logger.error(f"❌ Ошибка при удалении сервиса {service_name}: {e.explanation}")
        return False
