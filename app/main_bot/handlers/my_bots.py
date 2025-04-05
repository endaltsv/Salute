from aiogram import Router, types, F
from sqlalchemy import select
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.database.base.session import async_session
from app.database.models.user import User
from app.database.models.bot import Bot as BotModel
from app.utils.logger import logger

router = Router()


@router.callback_query(F.data == "my_bots")
async def process_my_bots(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    username = callback.from_user.username

    async with async_session() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await callback.message.answer("❌ Не удалось найти тебя в базе. Пожалуйста, сначала используй /start.")
            logger.warning(f"❌ Пользователь {user_id} не найден в базе при попытке открыть 'Мои боты'")
            await callback.answer()
            return

        result = await session.execute(
            select(BotModel).where(BotModel.owner_id == user.id)
        )
        bots = result.scalars().all()

    logger.info(f"📂 Пользователь @{username} (ID: {user_id}) открыл раздел 'Мои боты' (найдено: {len(bots)})")

    if not bots:
        await callback.message.answer("У тебя пока нет ни одного бота.")
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                *[
                    [InlineKeyboardButton(text=f"🤖 @{bot.name}", callback_data=f"bot_menu:{bot.id}")]
                    for bot in bots
                ],
                [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main_menu")]
            ]
        )
        await callback.message.answer("<b>Выбери бота для просмотра: 👇</b>", reply_markup=keyboard)

    await callback.answer()


@router.callback_query(F.data.startswith("bot_menu:"))
async def bot_menu(callback: types.CallbackQuery):
    bot_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    username = callback.from_user.username

    async with async_session() as session:
        result = await session.execute(select(BotModel).where(BotModel.id == bot_id))
        bot = result.scalar_one_or_none()

    if not bot:
        await callback.message.answer("❌ Бот не найден.")
        logger.warning(f"❌ Бот с ID {bot_id} не найден (пользователь: {user_id})")
        await callback.answer()
        return

    logger.info(
        f"⚙️ Пользователь @{username} (ID: {user_id}) открыл меню бота @{bot.name} (ID: {bot_id})"
    )

    text = f"⚙ <b>Меню бота:</b> @{bot.name}\n\n" \
           f"🔹 Все функции управления доступны внутри самого бота.\n" \
           f"Нажми кнопку ниже, чтобы перейти к управлению."

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡ Перейти к боту", url=f"https://t.me/{bot.name}?start=go")],
        [InlineKeyboardButton(text="🗑 Удалить бота", callback_data=f"delete_bot:{bot_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="my_bots")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()
