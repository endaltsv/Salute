# app/main_bot/handlers/create_bot.py
import os
import subprocess
import sys

from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext

from app.greeter_bots.core.launcher import run_greeter_bot
from app.main_bot.states.create_bot import CreateBotState
from app.database.base.session import async_session
from app.database.models.bot import Bot as BotModel
from app.database.models.user import User
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramUnauthorizedError, TelegramBadRequest
from sqlalchemy import select
import asyncio

from app.utils.logger import logger

router = Router()


@router.callback_query(F.data == "create_bot")
async def process_create_bot_button(callback: types.CallbackQuery, state: FSMContext):
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Передумал", callback_data="back_to_main_menu")]
    ])

    await callback.message.answer(
        "<b>🔐 Введите API токен нового бота</b>\n\n"
        "Чтобы подключить своего Telegram-бота, отправьте сюда <b>токен доступа</b>, который вы получили от <a href='https://t.me/BotFather'>@BotFather</a>.\n\n"
        "📌 <b>Где взять токен?</b>\n"
        "1. Перейдите в <a href='https://t.me/BotFather'>@BotFather</a>\n"
        "2. Отправьте команду <code>/newbot</code>\n"
        "3. Придумайте имя и юзернейм бота\n"
        "4. Получите API токен (выглядит как длинная строка из цифр и букв)\n\n"
        "⚠️ <b>Обратите внимание:</b>\n"
        "• <i>Не используйте токены других сервисов (например, от ботов постинга или рассылок) — это может нарушить их работу.</i>\n"
        "• <i>Избегайте слов “Telegram” или “Телеграм” в названии вашего бота.</i>\n"
        "• <i>Не ставьте логотип Telegram (самолётик) на аватарку — это может привести к блокировке со стороны модерации.</i>\n\n"
        "<b>Вставьте токен ниже, и я подключу вашего бота в систему.</b>👇",
        reply_markup=cancel_keyboard,
        disable_web_page_preview=True
    )

    await state.set_state(CreateBotState.waiting_for_token)
    await callback.answer()

    logger.info(
        f"🚀 Пользователь @{callback.from_user.username} (ID: {callback.from_user.id}) "
        f"🤖 Хочет создать бота"
    )


@router.message(CreateBotState.waiting_for_token)
async def process_token(message: types.Message, state: FSMContext):
    token = message.text.strip()
    new_bot = None  # 👈 добавляем заранее

    back_to_main_menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main_menu")]
    ])

    try:
        new_bot = Bot(token=token)
        bot_info = await new_bot.get_me()
    except TelegramUnauthorizedError:
        await message.answer("❌ Токен недействителен. Пожалуйста, проверь и попробуй снова.", reply_markup=back_to_main_menu_keyboard)
        logger.warning(f"⛔ Пользователь {message.from_user.id} ввёл недействительный токен.")
        return
    except TelegramBadRequest as e:
        await message.answer(f"❌ Ошибка при проверке токена: {str(e)}", reply_markup=back_to_main_menu_keyboard)
        logger.warning(f"⚠ Ошибка при get_me(): {e}")
        return
    except Exception as e:
        await message.answer("❌ Что-то пошло не так при проверке токена.", reply_markup=back_to_main_menu_keyboard)
        logger.exception(
            f"❌ Исключение при создании бота!\n"
            f"👤 Пользователь: @{message.from_user.username} (ID: {message.from_user.id})\n"
            f"📦 Токен: {token[:5]}... (обрезан)\n"
            f"⚠ Ошибка: {e}"
        )
        return
    finally:
        if new_bot:
            await new_bot.session.close()

    if not getattr(bot_info, "is_bot", False):
        await message.answer("❌ Этот токен принадлежит НЕ боту. Убедитесь, что вы скопировали токен от @BotFather.", reply_markup=back_to_main_menu_keyboard)
        logger.warning(f"❌ Полученный объект от get_me() не является ботом: {bot_info}")
        return

    async with async_session() as session:
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()

        if not user:
            await message.answer("❌ Не удалось найти пользователя в базе. Пожалуйста, начни сначала с /start.")
            logger.error(f"❌ User {message.from_user.id} отсутствует в таблице users.")
            await state.clear()
            return

        result = await session.execute(select(BotModel).where(BotModel.token == token))
        existing = result.scalar_one_or_none()
        if existing:
            await message.answer("⚠ Такой бот уже зарегистрирован в системе.", reply_markup=back_to_main_menu_keyboard)
            await state.clear()
            return

        bot_entry = BotModel(
            token=token,
            name=bot_info.username,
            owner_id=user.id,
        )
        session.add(bot_entry)
        await session.commit()
        bot_id = bot_entry.id  # получаем ID добавленного бота

    # 🟢 Автоматический запуск greeter_bot
    await message.answer(f"✅ Бот @{bot_info.username} успешно добавлен и запущен!", reply_markup=back_to_main_menu_keyboard)

    # 📲 Переход в bot_menu
    text = f"⚙ <b>Меню бота:</b> @{bot_info.username}\n\n" \
           f"🔹 Все функции управления доступны внутри самого бота.\n" \
           f"Нажми кнопку ниже, чтобы перейти к управлению."

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡ Перейти к боту", url=f"https://t.me/{bot_info.username}?start=go")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="my_bots")]
    ])
    await message.answer(text, reply_markup=keyboard)

    # ⬇️ запускаем greeter_runner.py через subprocess
    subprocess.Popen(
        [sys.executable, "greeter_runner.py"],
        env={**os.environ, "BOT_TOKEN": token},
        # 👇 Если хочешь полностью отвязать greeter-бота от main_bot (Windows only)
        # creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    )

    # 📦 Альтернатива: запуск через Docker (пока закомментировано)
    # subprocess.Popen([
    #     "docker", "run", "--rm",
    #     "-e", f"BOT_TOKEN={token}",
    #     "salute_greeter:latest"
    # ])

    logger.info(
        f"🚀 Пользователь @{message.from_user.username} (ID: {message.from_user.id}) "
        f"создал Greeter-бота: @{bot_info.username} (ID: {bot_info.id})"
    )

    await state.clear()
