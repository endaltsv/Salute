# app/main_bot/handlers/start.py

from aiogram import Router, types
from aiogram.filters import Command
from app.main_bot.keyboards.inline import main_menu_keyboard
from app.utils.logger import logger

router = Router()

text = (
    f"<b>👋 Привет!</b>\n\n"
    "Я — твой <b>приветственный бот</b> для Telegram-каналов и чатов.\n"
    "Помогаю автоматизировать <b>воронки продаж</b> и вовлекать новых участников.\n\n"
    "<b>Вот, что я умею:</b>\n"
    "• <i>Встречать новых подписчиков с приветствием или воронкой</i>\n"
    "• <i>Проверять через капчу (и сохранять для рассылок)</i>\n"
    "• <i>Делать автоматические рассылки</i>\n"
    "• <i>Получать детальную статистику</i>\n\n"
    "<b>Выбери, с чего начнём 👇</b>"
)


@router.message(Command('start'))
async def cmd_start(message: types.Message):
    await message.answer(text, reply_markup=main_menu_keyboard())
    logger.info(f"🚀 Пользователь @{message.from_user.username} (ID: {message.from_user.id}) начал с /start")


@router.callback_query(lambda c: c.data == "main_menu" or c.data == "back_to_main_menu")
async def back_to_main_menu(callback: types.CallbackQuery):
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard())
    await callback.answer()
