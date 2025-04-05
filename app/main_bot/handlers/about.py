# app/main_bot/handlers/about.py

from aiogram import Router, types

from app.utils.logger import logger

router = Router()


@router.callback_query(lambda c: c.data == "about_service")
async def about_service(callback: types.CallbackQuery):
    text = (
        "<b>ℹ️ О сервисе</b>\n\n"
        "Этот бот помогает автоматизировать приём новых участников в Telegram-каналы:\n"
        "• Отправляет приветствия и капчи\n"
        "• Собирает базу участников\n"
        "• Делает рассылки\n"
        "• Даёт аналитику и статистику\n\n"
        "🔐 Сделан с заботой о безопасности и простоте ✨"
    )
    await callback.message.edit_text(text)
    logger.info(f"ℹ️ Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) открыл 'О сервисе'")
    await callback.answer()
