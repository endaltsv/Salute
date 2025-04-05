from aiogram import Router, F
from aiogram.types import CallbackQuery, Message

from app.utils.logger import logger
from app.redis_queue.admin_logs import send_log_to_admin


def get_router():
    router = Router(name=__name__)

    @router.message()
    async def catch_all_messages(message: Message):
        logger.info(
            f"🟡 Пользователь @{message.from_user.username} (ID: {message.from_user.id}) написал сообщение: {message.text}"
        )

    @router.callback_query(F.data == "noop")
    async def noop_callback(callback: CallbackQuery):
        logger.info(
            f"🟡 Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) нажал на техническую кнопку 'noop'"
        )

        await send_log_to_admin(
            f"🟡 <code>{callback.from_user.id}</code> нажал на техническую кнопку (noop)"
        )

        await callback.answer(
            text="🔘 Это техническая кнопка, которая разделяет функции бота и список ваших каналов.",
            show_alert=True
        )

    return router
