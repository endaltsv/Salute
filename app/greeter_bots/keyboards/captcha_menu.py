from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def captcha_menu_keyboard(channel_id: int, is_enabled: bool, has_button: bool) -> InlineKeyboardMarkup:
    status_text = "🟢 Включена" if is_enabled else "🔴 Выключена"
    status_text = "❌ Выключить капчу" if is_enabled else "✅ Включить капчу"
    button_text = "♻️ Изменить кнопку" if has_button else "➕ Добавить кнопку"

    keyboard = [
        [InlineKeyboardButton(text=f"{status_text}", callback_data=f"toggle_captcha:{channel_id}")],
        [InlineKeyboardButton(text="✏️ Изменить текст капчи", callback_data=f"edit_captcha_text:{channel_id}")],
        [InlineKeyboardButton(text=button_text, callback_data=f"edit_captcha_button:{channel_id}")],
    ]

    if has_button:
        keyboard.append([
            InlineKeyboardButton(text="🗑 Удалить кнопку", callback_data=f"delete_captcha_button:{channel_id}")
        ])

    keyboard.append([
        InlineKeyboardButton(text="👁 Посмотреть пример", callback_data=f"preview_captcha:{channel_id}")
    ])

    keyboard.append([
        InlineKeyboardButton(text="⬅ Назад", callback_data=f"channel_settings:{channel_id}")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
