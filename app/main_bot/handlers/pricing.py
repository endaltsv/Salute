# app/main_bot/handlers/pricing.py

from aiogram import Router, types
import logging

from app.utils.logger import logger

router = Router()

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


@router.callback_query(lambda c: c.data == "pricing")
async def pricing(callback: types.CallbackQuery):
    text = (
        "<b>💎 Тарифы</b>\n\n"
        "Подписка скоро будет доступна ⏳"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_main_menu")]
        ]
    )

    await callback.message.edit_text(text, reply_markup=keyboard)
    logger.info(f"💎 Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) открыл 'Тарифы'")
    await callback.answer()
