from aiogram import F, types, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from sqlalchemy import select, update

from app.greeter_bots.keyboards.captcha_menu import captcha_menu_keyboard
from app.greeter_bots.keyboards.channel_settings import channel_settings_keyboard
from app.database.base.session import async_session
from app.database.models.channel import Channel
from app.utils.logger import logger
from app.redis_queue.admin_logs import send_log_to_admin  # <-- меняй путь на правильный, если нужно.

class CaptchaTextState(StatesGroup):
    waiting_for_text = State()

class CaptchaButtonState(StatesGroup):
    waiting_for_button_text = State()


def get_router() -> Router:
    router = Router()

    async def get_channel_by_id(channel_id: int | str):
        async with async_session() as session:
            result = await session.execute(
                select(Channel).where(Channel.id == int(channel_id))
            )
            return result.scalars().first()

    async def update_channel_field(channel_id: int, field: str, value):
        async with async_session() as session:
            await session.execute(
                update(Channel).where(Channel.id == int(channel_id)).values({field: value})
            )
            await session.commit()

    @router.callback_query(F.data.startswith("captcha_menu:"))
    async def open_captcha_menu(callback: types.CallbackQuery):
        channel_id = int(callback.data.split(":")[1])
        channel = await get_channel_by_id(channel_id)

        if not channel:
            await callback.answer("Канал не найден!", show_alert=True)
            log_text = (
                f"❌ Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) "
                f"попытался открыть меню капчи несуществующего канала ID={channel_id}"
            )
            await send_log_to_admin(log_text, level="warning")
            logger.warning(log_text)
            return

        log_text = (
            f"🧩 Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) "
            f"открыл меню капчи для канала ID={channel_id}"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

        await callback.message.edit_text(
            text=(
                f"🧩 <b>Капча для вовлечения</b>\n\n"
                f"📌 <i>Это вовлекающий механизм: перед приветствием бот отправляет специальное сообщение с кнопкой.</i>\n"
                f"Когда пользователь нажимает кнопку — он как бы «проходит капчу», и бот может отправлять ему сообщения напрямую (обходит ограничения Telegram).\n\n"
                f"⚙️ <b>Вы можете настроить:</b>\n"
                f"— Включение/выключение капчи\n"
                f"— Текст сообщения капчи\n"
                f"— Кнопку (например, «Я не робот»)\n"
                f"📨 Только после прохождения капчи бот сможет отправлять пользователю рассылки."
            ),
            reply_markup=captcha_menu_keyboard(
                channel_id=channel.id,
                is_enabled=channel.captcha_enabled,
                has_button=channel.captcha_has_button
            )
        )

        await callback.answer()

    @router.callback_query(F.data.startswith("toggle_captcha:"))
    async def toggle_captcha_handler(callback: types.CallbackQuery):
        channel_id = int(callback.data.split(":")[1])
        channel = await get_channel_by_id(channel_id)
        if not channel:
            await callback.answer("Канал не найден!", show_alert=True)
            log_text = (
                f"❌ Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) "
                f"попытался переключить капчу в несуществующем канале ID={channel_id}"
            )
            await send_log_to_admin(log_text, level="warning")
            logger.warning(log_text)
            return

        new_status = not channel.captcha_enabled
        await update_channel_field(channel.id, "captcha_enabled", new_status)

        await callback.message.edit_reply_markup(
            reply_markup=captcha_menu_keyboard(channel.id, new_status, channel.captcha_has_button)
        )
        await callback.answer(f"Капча {'включена' if new_status else 'выключена'}")

        log_text = (
            f"⚙️ Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) "
            f"переключил капчу: {'включил' if new_status else 'выключил'} (channel_id={channel.id})"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

    @router.callback_query(F.data.startswith("edit_captcha_text:"))
    async def edit_captcha_text_handler(callback: types.CallbackQuery, state: FSMContext):
        channel_id = int(callback.data.split(":")[1])
        await state.update_data(channel_id=channel_id)
        await callback.message.answer("Введите новый текст капчи:")
        await state.set_state(CaptchaTextState.waiting_for_text)

        log_text = (
            f"✏️ Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) "
            f"начал редактирование текста капчи (channel_id={channel_id})"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

    @router.message(CaptchaTextState.waiting_for_text)
    async def process_captcha_text(message: types.Message, state: FSMContext):
        data = await state.get_data()
        channel_id = data["channel_id"]
        await update_channel_field(channel_id, "captcha_text", message.text)
        await message.answer("Текст капчи обновлён!")

        channel = await get_channel_by_id(channel_id)
        await message.answer(
            "Настройки капчи:",
            reply_markup=captcha_menu_keyboard(channel.id, channel.captcha_enabled, channel.captcha_has_button)
        )
        await state.clear()

        log_text = (
            f"📝 Пользователь @{message.from_user.username} (ID: {message.from_user.id}) "
            f"обновил текст капчи (channel_id={channel_id}): '{message.text}'"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

    @router.callback_query(F.data.startswith("edit_captcha_button:"))
    async def edit_captcha_button_handler(callback: types.CallbackQuery, state: FSMContext):
        channel_id = int(callback.data.split(":")[1])
        await state.update_data(channel_id=channel_id)
        await callback.message.answer("Введите текст кнопки капчи:")
        await state.set_state(CaptchaButtonState.waiting_for_button_text)

        log_text = (
            f"✏️ Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) "
            f"начал редактирование кнопки капчи (channel_id={channel_id})"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

    @router.message(CaptchaButtonState.waiting_for_button_text)
    async def process_captcha_button_text(message: types.Message, state: FSMContext):
        data = await state.get_data()
        channel_id = data["channel_id"]
        button_text = message.text

        await update_channel_field(channel_id, "captcha_button_text", button_text)
        await update_channel_field(channel_id, "captcha_has_button", bool(button_text))

        await message.answer("Кнопка капчи обновлена.")
        channel = await get_channel_by_id(channel_id)
        await message.answer(
            "Настройки капчи:",
            reply_markup=captcha_menu_keyboard(channel.id, channel.captcha_enabled, channel.captcha_has_button)
        )
        await state.clear()

        log_text = (
            f"🔘 Пользователь @{message.from_user.username} (ID: {message.from_user.id}) "
            f"обновил кнопку капчи (channel_id={channel_id}): '{button_text}'"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

    @router.callback_query(F.data.startswith("delete_captcha_button:"))
    async def delete_captcha_button_handler(callback: types.CallbackQuery):
        channel_id = int(callback.data.split(":")[1])
        channel = await get_channel_by_id(channel_id)
        if not channel:
            await callback.answer("❌ Канал не найден", show_alert=True)
            return

        await update_channel_field(channel_id, "captcha_button_text", None)
        await update_channel_field(channel_id, "captcha_has_button", False)
        await callback.message.answer("Кнопка капчи удалена.")

        channel = await get_channel_by_id(channel_id)
        await callback.message.answer(
            "Настройки капчи:",
            reply_markup=captcha_menu_keyboard(channel.id, channel.captcha_enabled, channel.captcha_has_button)
        )

        log_text = (
            f"🗑️ Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) "
            f"удалил кнопку капчи (channel_id={channel_id})"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

    @router.callback_query(F.data.startswith("preview_captcha:"))
    async def preview_captcha_handler(callback: types.CallbackQuery):
        channel_id = int(callback.data.split(":")[1])
        channel = await get_channel_by_id(channel_id)
        if not channel:
            await callback.answer("❌ Канал не найден", show_alert=True)
            return

        text = channel.captcha_text or "Пример капчи отсутствует."

        if channel.captcha_has_button and channel.captcha_button_text:
            reply_markup = ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text=channel.captcha_button_text)]],
                resize_keyboard=True,
                one_time_keyboard=True
            )
        else:
            reply_markup = None

        await callback.message.answer(text=text, reply_markup=reply_markup)

        log_text = (
            f"👀 Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) "
            f"посмотрел превью капчи (channel_id={channel_id})"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

    @router.callback_query(F.data.startswith("channel_settings:"))
    async def back_to_channel_settings(callback: types.CallbackQuery):
        channel_id = int(callback.data.split(":")[1])
        channel = await get_channel_by_id(channel_id)

        if not channel:
            await callback.answer("❌ Канал не найден", show_alert=True)
            log_text = (
                f"❌ Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) "
                f"попытался вернуться к настройкам несуществующего канала ID={channel_id}"
            )
            await send_log_to_admin(log_text, level="warning")
            logger.warning(log_text)
            return

        await callback.message.edit_reply_markup(
            reply_markup=channel_settings_keyboard(channel)
        )
        await callback.answer()

        log_text = (
            f"🔙 Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) "
            f"вернулся в настройки канала (channel_id={channel_id})"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

    return router
