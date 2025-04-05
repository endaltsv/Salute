from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select, update

from app.database.base.session import async_session
from app.database.models.channel import Channel
from app.greeter_bots.states.welcome import WelcomeState
from app.greeter_bots.keyboards.welcome_menu import welcome_menu_keyboard
from app.utils.logger import logger
from app.redis_queue.admin_logs import send_log_to_admin  # поправь, если название иное

def get_router() -> Router:
    router = Router()

    @router.callback_query(F.data.startswith("welcome_menu:"))
    async def show_welcome_menu(callback: types.CallbackQuery):
        channel_id = int(callback.data.split(":")[1])
        async with async_session() as session:
            result = await session.execute(select(Channel).where(Channel.id == channel_id))
            channel = result.scalar_one()

        log_text = (
            f"👋 @{callback.from_user.username} (ID: {callback.from_user.id}) открыл меню приветствия "
            f"для канала ID={channel_id}"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

        await callback.message.edit_text(
            f"💬 <b>Приветственное сообщение</b> для канала <b>{channel.channel_name}</b>\n\n"
            f"📌 <i>Это сообщение автоматически отправляется новым участникам канала при вступлении или подачи заявки.</i>\n\n"
            f"⚙️ <b>Функционал:</b>\n"
            f"— Включение/выключение приветствия\n"
            f"— Создание и редактирование текста приветствия\n"
            f"— Добавление кнопки к сообщению (inline или reply)\n"
            f"— Просмотр примера сообщения\n\n",
            reply_markup=welcome_menu_keyboard(channel.id, channel.welcome_enabled)
        )
        await callback.answer()

    @router.callback_query(F.data.startswith("toggle_welcome:"))
    async def toggle_welcome(callback: types.CallbackQuery):
        channel_id = int(callback.data.split(":")[1])
        async with async_session() as session:
            result = await session.execute(select(Channel).where(Channel.id == channel_id))
            channel = result.scalar_one()
            channel.welcome_enabled = not channel.welcome_enabled
            await session.commit()

        status = "✅ Включено" if channel.welcome_enabled else "❌ Выключено"
        log_text = (
            f"🔁 @{callback.from_user.username} (ID: {callback.from_user.id}) "
            f"сменил welcome_enabled={channel.welcome_enabled} для канала ID={channel_id}"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

        await callback.message.edit_reply_markup(
            reply_markup=welcome_menu_keyboard(channel_id, channel.welcome_enabled)
        )
        await callback.answer(status)

    @router.callback_query(F.data.startswith("edit_welcome_text:"))
    async def edit_welcome_text(callback: types.CallbackQuery, state: FSMContext):
        channel_id = int(callback.data.split(":")[1])
        await state.set_state(WelcomeState.entering_text)
        await state.update_data(channel_id=channel_id)

        log_text = (
            f"✏ @{callback.from_user.username} (ID: {callback.from_user.id}) начал редактировать "
            f"текст приветствия канала ID={channel_id}"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

        await callback.message.edit_text("✏ Введите новый текст приветствия:")
        await callback.answer()

    @router.message(WelcomeState.entering_text)
    async def save_welcome_text(message: types.Message, state: FSMContext):
        data = await state.get_data()
        channel_id = data["channel_id"]
        new_text = message.text.strip()

        async with async_session() as session:
            await session.execute(
                update(Channel).where(Channel.id == channel_id).values(welcome_message=new_text)
            )
            await session.commit()

        log_text = (
            f"💬 @{message.from_user.username} (ID: {message.from_user.id}) "
            f"обновил текст приветствия для канала ID={channel_id}\n"
            f"Новый текст: {new_text}"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

        builder = InlineKeyboardBuilder()
        builder.button(text="⬅ Назад к настройкам", callback_data=f"channel_settings:{channel_id}")

        await message.answer("✅ Приветственное сообщение обновлено.", reply_markup=builder.as_markup())
        await state.clear()

    @router.callback_query(F.data.startswith("edit_welcome_button:"))
    async def edit_welcome_button(callback: types.CallbackQuery, state: FSMContext):
        channel_id = int(callback.data.split(":")[1])
        await state.set_state(WelcomeState.entering_button_text)
        await state.update_data(channel_id=channel_id)

        log_text = (
            f"🔘 @{callback.from_user.username} (ID: {callback.from_user.id}) "
            f"начал редактировать кнопку приветствия канала ID={channel_id}"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

        await callback.message.edit_text("✏ Введите текст кнопки для приветствия:")
        await callback.answer()

    @router.message(WelcomeState.entering_button_text)
    async def save_button_text(message: types.Message, state: FSMContext):
        await state.update_data(button_text=message.text.strip())
        log_text = (
            f"🔗 @{message.from_user.username} (ID: {message.from_user.id}) "
            f"указал текст кнопки: {message.text.strip()}"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

        await message.answer("🔗 Теперь введите ссылку для кнопки:")
        await state.set_state(WelcomeState.entering_button_url)

    @router.message(WelcomeState.entering_button_url)
    async def save_button_url(message: types.Message, state: FSMContext):
        data = await state.get_data()
        channel_id = data["channel_id"]
        button_text = data["button_text"]
        button_url = message.text.strip()

        async with async_session() as session:
            await session.execute(
                update(Channel).where(Channel.id == channel_id).values(
                    has_button=True,
                    button_text=button_text,
                    button_url=button_url,
                    button_type="inline"
                )
            )
            await session.commit()

        log_text = (
            f"🔗 @{message.from_user.username} (ID: {message.from_user.id}) "
            f"обновил кнопку приветствия: [{button_text}]({button_url}) для канала {channel_id}"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

        await message.answer("✅ Кнопка для приветствия обновлена.")
        await state.clear()

    @router.callback_query(F.data.startswith("preview_welcome:"))
    async def preview_welcome_message(callback: types.CallbackQuery):
        channel_id = int(callback.data.split(":")[1])
        async with async_session() as session:
            result = await session.execute(select(Channel).where(Channel.id == channel_id))
            channel = result.scalar_one()

        log_text = (
            f"👀 @{callback.from_user.username} (ID: {callback.from_user.id}) "
            f"просмотр приветственного сообщения канала ID={channel_id}"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

        if not channel.welcome_message:
            await callback.message.answer("ℹ Приветственное сообщение ещё не задано.")
            await callback.answer()
            return

        if channel.has_button:
            if channel.button_type == "inline":
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                kb = InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text=channel.button_text, url=channel.button_url)]]
                )
                await callback.message.answer(channel.welcome_message, reply_markup=kb)
            else:
                from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
                kb = ReplyKeyboardMarkup(
                    keyboard=[[KeyboardButton(text=channel.button_text)]],
                    resize_keyboard=True
                )
                await callback.message.answer(channel.welcome_message, reply_markup=kb)
        else:
            await callback.message.answer(channel.welcome_message)

        await callback.answer()

    return router
