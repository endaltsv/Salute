from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import select

from app.database.base.session import async_session
from app.database.models.channel import Channel
from app.database.models.member import ChannelMember
from app.greeter_bots.states.broadcast import BroadcastState
from app.redis_queue.broadcast import enqueue_broadcast_task
from app.utils.logger import logger
from app.redis_queue.admin_logs import send_log_to_admin  # <-- Добавили импорт для логов


def channel_selection_keyboard(channels, selected, all_selected=False):
    keyboard = []

    for ch in channels:
        check = "✅ " if ch.id in selected else ""
        keyboard.append([
            InlineKeyboardButton(
                text=f"{check}{ch.channel_name or ch.channel_id}",
                callback_data=f"broadcast_toggle:{ch.id}"
            )
        ])

    all_check = "✅ " if all_selected else ""
    keyboard.append([
        InlineKeyboardButton(text=f"{all_check}📢 Все каналы", callback_data="broadcast_all")
    ])

    # 👇 Добавляем кнопку "Начать рассылку", только если выбран хотя бы один канал или all_selected
    if selected or all_selected:
        keyboard.append([
            InlineKeyboardButton(text="🚀 Начать рассылку", callback_data="broadcast_start")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(text="🚫 Выберите каналы", callback_data="noop")
        ])

    keyboard.append([
        InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def yes_no_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="broadcast_add_button_yes")],
        [InlineKeyboardButton(text="❌ Нет", callback_data="broadcast_add_button_no")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="broadcast_menu")]
    ])


def get_router() -> Router:
    router = Router()

    @router.callback_query(F.data == "broadcast_menu")
    async def broadcast_start(callback: types.CallbackQuery, state: FSMContext, bot_id: int):
        async with async_session() as session:
            result = await session.execute(select(Channel).where(Channel.bot_id == bot_id))
            channels = result.scalars().all()

        await state.update_data(channels=channels, selected=set(), all_selected=False, bot_id=bot_id)
        await state.set_state(BroadcastState.choosing_channels)

        await callback.message.edit_text(
            "📬 Выберите каналы, на которые хотите сделать рассылку:",
            reply_markup=channel_selection_keyboard(channels, set(), all_selected=False)
        )
        await callback.answer()

        log_text = (
            f"📬 Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) "
            f"открыл меню рассылки (bot_id={bot_id})"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

    @router.callback_query(F.data.startswith("broadcast_toggle:"))
    async def toggle_channel(callback: types.CallbackQuery, state: FSMContext):
        channel_id = int(callback.data.split(":")[1])
        data = await state.get_data()
        selected = data.get("selected", set())
        channels = data["channels"]

        # Добавляем или убираем из выбранных
        if channel_id in selected:
            selected.remove(channel_id)
        else:
            selected.add(channel_id)

        await state.update_data(selected=selected, all_selected=False)
        await safe_edit_reply_markup(callback.message, channel_selection_keyboard(channels, selected, False))
        await callback.answer()

        log_text = (
            f"🔘 Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) "
            f"{'выбрал' if channel_id not in selected else 'убрал'} канал ID {channel_id} для рассылки"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

    @router.callback_query(F.data == "broadcast_all")
    async def select_all_channels(callback: types.CallbackQuery, state: FSMContext):
        data = await state.get_data()
        channels = data["channels"]

        await state.update_data(selected=set(), all_selected=True)
        await safe_edit_reply_markup(callback.message, channel_selection_keyboard(channels, set(), True))
        await callback.answer()

        log_text = (
            f"📢 Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) выбрал 'Все каналы' для рассылки"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

    @router.callback_query(F.data == "broadcast_start")
    async def ask_message(callback: types.CallbackQuery, state: FSMContext):
        await state.set_state(BroadcastState.entering_message)
        await callback.message.edit_text(
            "📝 Введите сообщение с форматированием (жирный, курсив и т.д.). "
            "Форматирование будет сохранено и использовано как HTML."
        )
        await callback.answer()

        log_text = (
            f"✍️ Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) "
            f"приступил к вводу текста рассылки"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

    @router.message(BroadcastState.entering_message)
    async def save_message_and_ask_button(message: types.Message, state: FSMContext):
        await state.update_data(text=message.html_text)  # ✅ сохраняем HTML-версию текста
        await state.set_state(BroadcastState.ask_add_button)

        await message.answer(
            "🔘 Добавить кнопку к сообщению?",
            reply_markup=yes_no_keyboard()
        )

        log_text = (
            f"💬 Пользователь @{message.from_user.username} (ID: {message.from_user.id}) "
            f"ввёл сообщение для рассылки"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

    @router.callback_query(F.data == "broadcast_add_button_yes")
    async def ask_button_text(callback: types.CallbackQuery, state: FSMContext):
        await state.set_state(BroadcastState.entering_button_text)
        await callback.message.edit_text("🔤 Введите текст кнопки:")
        await callback.answer()

        log_text = (
            f"➕ Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) "
            f"решил добавить кнопку к рассылке"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

    @router.message(BroadcastState.entering_button_text)
    async def save_button_text(message: types.Message, state: FSMContext):
        await state.update_data(button_text=message.text)
        await state.set_state(BroadcastState.entering_button_url)
        await message.answer("🔗 Введите ссылку для кнопки:")

    @router.message(BroadcastState.entering_button_url)
    async def start_broadcast_with_button(message: types.Message, state: FSMContext, bot: Bot):
        await state.update_data(button_url=message.text)
        data = await state.get_data()
        await finish_broadcast(bot, message, data)
        await state.clear()

        log_text = (
            f"🔗 Пользователь @{message.from_user.username} (ID: {message.from_user.id}) "
            f"задал кнопку к рассылке: текст='{message.text}'"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

    @router.callback_query(F.data == "broadcast_add_button_no")
    async def start_broadcast_without_button(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
        data = await state.get_data()
        await finish_broadcast(bot, callback.message, data)
        await callback.answer()
        await state.clear()

        log_text = (
            f"❌ Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) отказался от кнопки"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

    async def finish_broadcast(bot: Bot, message: types.Message, data: dict):
        text = data["text"]
        button_text = data.get("button_text")
        button_url = data.get("button_url")
        all_selected = data.get("all_selected", False)
        bot_id = data.get("bot_id")

        async with async_session() as session:
            if all_selected:
                result = await session.execute(select(Channel).where(Channel.bot_id == bot_id))
            else:
                result = await session.execute(select(Channel).where(Channel.id.in_(data["selected"])))
            channels = result.scalars().all()
            channel_ids = [ch.id for ch in channels]

            members_result = await session.execute(
                select(ChannelMember.user_id).where(
                    ChannelMember.channel_id.in_(channel_ids),
                    ChannelMember.bot_id == bot_id,
                    ChannelMember.is_available_for_broadcast.is_(True)  # ✅ Только доступные для рассылки
                )
            )

            user_ids = {row[0] for row in members_result.fetchall()}

        # 🔁 Вместо отправки — кладём задачу в Redis
        await enqueue_broadcast_task(
            bot_id=bot_id,
            text=text,
            user_ids=list(user_ids),
            button_text=button_text,
            button_url=button_url,
            response_chat_id=message.chat.id,
            response_message_id=message.message_id
        )

        builder = InlineKeyboardBuilder()
        builder.button(text="⬅ В главное меню", callback_data="back_to_main_menu")

        await message.answer(
            f"✅ Рассылка запущена в фоне. Всего в боте: {len(user_ids)}. "
            f"Ожидайте ⏳",
            reply_markup=builder.as_markup()
        )

        log_text = (
            f"🚀 Запущена рассылка (bot_id={bot_id}) | каналов: {len(channel_ids)} | пользователей: {len(user_ids)} "
            f"| кнопка: {'да' if button_text and button_url else 'нет'}"
        )
        await send_log_to_admin(log_text)
        logger.info(log_text)

    async def safe_edit_reply_markup(message: types.Message, markup: InlineKeyboardMarkup):
        try:
            await message.edit_reply_markup(reply_markup=markup)
        except TelegramBadRequest as e:
            if "message is not modified" not in str(e):
                raise e

    return router
