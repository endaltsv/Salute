from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.database.base.session import async_session
from app.greeter_bots.keyboards.channel_settings import channel_settings_keyboard
from app.greeter_bots.states.add_channel import AddChannelState
from app.database.models.channel import Channel
from app.redis_queue.admin_logs import send_log_to_admin


def get_router() -> Router:
    router = Router()

    @router.callback_query(F.data == "add_channel")
    async def add_channel_start(callback: types.CallbackQuery, state: FSMContext):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main_menu")]
        ])
        await callback.message.answer(
            "📥 Отправьте ID канала или пересланное сообщение из канала.",
            reply_markup=keyboard
        )
        await state.set_state(AddChannelState.waiting_for_channel)

        await send_log_to_admin(
            f"➕ Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) начал добавление канала"
        )

        await callback.answer()

    @router.message(AddChannelState.waiting_for_channel)
    async def process_channel(message: types.Message, state: FSMContext, bot_id: int):
        if message.forward_from_chat:
            channel_id = str(message.forward_from_chat.id)
            channel_name = message.forward_from_chat.title
        else:
            channel_id = message.text.strip()
            channel_name = "Без названия"

        async with async_session() as session:
            exists = await session.execute(
                Channel.__table__.select().where(
                    Channel.channel_id == channel_id,
                    Channel.bot_id == bot_id
                )
            )
            if exists.first():
                await message.answer("⚠ Этот канал уже добавлен.")
                await send_log_to_admin(
                    f"⚠ Пользователь @{message.from_user.username} (ID: {message.from_user.id}) "
                    f"попытался повторно добавить канал {channel_id} в бота ID {bot_id}",
                    level="warning"
                )
                await state.clear()
                return

            channel = Channel(
                bot_id=bot_id,
                channel_id=channel_id,
                channel_name=channel_name,
                welcome_message=""
            )
            session.add(channel)
            await session.commit()

            await send_log_to_admin(
                f"✅ Пользователь @{message.from_user.username} (ID: {message.from_user.id}) добавил канал "
                f"{channel_name} (ID: {channel_id}) в бота ID {bot_id}"
            )

            await message.answer(
                f"<b>✅ Канал <u>{channel_name}</u> добавлен!</b>\n\n"
                "Выберите, что хотите настроить для этого канала:\n\n"
                "• <b>Приветственное сообщение</b> — автоматическая отправка сообщения при вступлении в канал\n"
                "• <b>Автоодобрение</b> — настройка принятий заявок в канал\n"
                "• <b>Капча</b> — присылает кнопку с текстом при нажатии на которую человек записывается в базу для дальнейших рассылок\n"
                "• <b>Удалить канал</b> — удаляет канал из бота и базы\n"
                "• <b>В главное меню</b> — вернуться к общему списку каналов",
                reply_markup=channel_settings_keyboard(channel)
            )

        await state.clear()

    return router
