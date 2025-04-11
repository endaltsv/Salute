from aiogram import Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from app.main_bot.config.config import settings
from app.utils.logger import logger

router = Router()


@router.callback_query(lambda c: c.data == "support")
async def support(callback: types.CallbackQuery):
    support_username = settings.support_username

    text = (
        "<b>💬 Поддержка</b>\n\n"
        "Если у тебя возникли вопросы или нужна помощь:\n"
        f"👨‍💻 <a href='https://t.me/{support_username}'>@{support_username}</a>\n\n"
        "📌 Мы всегда на связи 😉"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main_menu")]
        ]
    )

    await callback.message.edit_text(text, disable_web_page_preview=True, reply_markup=keyboard)
    logger.info(f"🆘 Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) открыл 'Поддержка'")
    await callback.answer()
