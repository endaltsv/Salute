# app/main_bot/keyboards/bot_list.py

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.database.models.bot import Bot


def bots_list_keyboard(bots: list[Bot]) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text=f"🤖 @{bot.name or 'Без имени'}", callback_data=f"bot_menu:{bot.id}")]
        for bot in bots
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
