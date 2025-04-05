from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def welcome_menu_keyboard(channel_id: int, enabled: bool) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="❌ Отключить приветствие" if enabled else "✅ Включить приветствие",
            callback_data=f"toggle_welcome:{channel_id}"
        )],
        [InlineKeyboardButton(text="✏ Изменить сообщение", callback_data=f"edit_welcome_text:{channel_id}")],
        [InlineKeyboardButton(text="♻️ Изменить кнопку", callback_data=f"edit_welcome_button:{channel_id}")],
        [InlineKeyboardButton(text="👁 Посмотреть пример", callback_data=f"preview_welcome:{channel_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"channel_menu:{channel_id}")]
    ])