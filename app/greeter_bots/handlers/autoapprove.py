import logging
from aiogram import Router, types, F
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, update

from app.database.base.session import async_session
from app.database.models.channel import Channel
from app.greeter_bots.keyboards.autoapprove_menu import autoapprove_keyboard
from app.redis_queue.admin_logs import send_log_to_admin
from app.utils.logger import logger

class AutoApproveState(StatesGroup):
    waiting_for_seconds = State()


def get_router(bot_id: int) -> Router:
    router = Router()

    @router.callback_query(F.data.startswith("autoapprove_menu:"))
    async def show_autoapprove_menu(callback: types.CallbackQuery):
        channel_id = int(callback.data.split(":")[1])

        async with async_session() as session:
            result = await session.execute(
                select(Channel).where(Channel.id == channel_id, Channel.bot_id == bot_id)
            )
            channel = result.scalar_one_or_none()

        if not channel:
            await callback.answer("❌ Канал не найден")
            await send_log_to_admin(
                f"❌ Канал ID {channel_id} не найден при открытии автоодобрения", level="warning"
            )
            logger.warning(f"❌ Канал ID {channel_id} не найден при открытии автоодобрения")
            return

        log_text = (
            f"⚙️ Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) открыл автоодобрение "
            f"для канала {channel.channel_name} (ID: {channel.channel_id}) | режим: {channel.auto_approve_mode or 'Нет'}"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

        await callback.message.edit_text(
            text=(
                f"🤖 <b>Настройка автоодобрения заявок</b>\n\n"
                f"📌 <i>Если канал закрытый и требует одобрения заявок — вы можете включить автоматическое одобрение новых участников.</i>\n\n"
                f"⚙️ <b>Варианты:</b>\n"
                f"— <b>Нет</b> — заявки не одобряются автоматически\n"
                f"— <b>Сразу</b> — одобряются мгновенно\n"
                f"— <b>Через 1 минуту</b> — одобрение с задержкой 1 минута\n"
                f"— <b>Через 5 минут</b> — одобрение с задержкой 5 минут\n"
                f"— <b>Указать вручную</b> — задать своё время (в секундах)\n\n"
                f"🛠 Текущий режим: <b>{channel.auto_approve_mode or 'Нет'}</b>"
            ),
            reply_markup=autoapprove_keyboard(channel.auto_approve_mode or "none", channel_id)
        )

    @router.callback_query(F.data.startswith("set_autoapprove:"))
    async def set_autoapprove(callback: types.CallbackQuery):
        _, mode, channel_id = callback.data.split(":")
        channel_id = int(channel_id)

        async with async_session() as session:
            await session.execute(
                update(Channel)
                .where(Channel.id == channel_id, Channel.bot_id == bot_id)
                .values(auto_approve_mode=mode)
            )
            await session.commit()

        log_text = (
            f"✅ Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) "
            f"установил автоодобрение: {mode} для канала ID {channel_id}"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

        await callback.answer("✅ Обновлено!")
        await callback.message.edit_reply_markup(
            reply_markup=autoapprove_keyboard(mode, channel_id)
        )

    @router.callback_query(F.data.startswith("custom_autoapprove:"))
    async def ask_custom_seconds(callback: types.CallbackQuery, state: FSMContext):
        channel_id = int(callback.data.split(":")[1])
        await state.set_state(AutoApproveState.waiting_for_seconds)
        await state.update_data(channel_id=channel_id)
        await callback.message.answer("⌛ Введите, через сколько секунд нужно одобрять заявки:")

        log_text = (
            f"⌛ Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) выбрал ручной режим "
            f"автоодобрения для канала ID {channel_id}"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

    @router.message(AutoApproveState.waiting_for_seconds)
    async def save_custom_delay(message: types.Message, state: FSMContext):
        data = await state.get_data()
        channel_id = data["channel_id"]

        try:
            seconds = int(message.text.strip())
            if seconds <= 0 or seconds > 86400:
                raise ValueError
        except ValueError:
            await message.answer("❗ Введите число секунд от 1 до 86400")
            return

        async with async_session() as session:
            await session.execute(
                update(Channel)
                .where(Channel.id == channel_id, Channel.bot_id == bot_id)
                .values(auto_approve_mode=f"{seconds}s")
            )
            await session.commit()

        log_text = (
            f"🕒 Пользователь @{message.from_user.username} (ID: {message.from_user.id}) "
            f"установил автоодобрение: {seconds} сек для канала ID {channel_id}"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

        builder = InlineKeyboardBuilder()
        builder.button(text="⬅ Назад к настройкам", callback_data=f"channel_settings:{channel_id}")

        await message.answer(f"✅ Установлено: {seconds} секунд до автоодобрения.", reply_markup=builder.as_markup())
        await state.clear()

    return router
