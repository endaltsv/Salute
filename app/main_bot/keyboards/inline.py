# app/main_bot/keyboards/inline.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🤖 Создать бота", callback_data="create_bot"),
         InlineKeyboardButton(text="📂 Мои боты", callback_data="my_bots")],
        [InlineKeyboardButton(text="💎 Тарифы", callback_data="pricing")],

        [
            # InlineKeyboardButton(text="ℹ️ О сервисе", callback_data="about_service"),
         InlineKeyboardButton(text="💬 Поддержка", callback_data="support")],
    ])
