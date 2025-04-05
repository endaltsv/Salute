# app/main_bot/handlers/pricing.py

from aiogram import Router, types
import logging

from app.utils.logger import logger

router = Router()


@router.callback_query(lambda c: c.data == "pricing")
async def pricing(callback: types.CallbackQuery):
    text = (
        "<b>💎 Тарифы</b>\n\n"
        "🔹 <b>Бесплатный</b> — до 1 бота, базовая статистика\n"
        "🔸 <b>Премиум</b> — от 490₽/мес:\n"
        "• до 10 ботов\n"
        "• рассылки\n"
        "• аналитика\n"
        "• автоодобрение\n\n"
        "Подписка скоро будет доступна ⏳"
    )
    await callback.message.edit_text(text)
    logger.info(f"💎 Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) открыл 'Тарифы'")
    await callback.answer()
