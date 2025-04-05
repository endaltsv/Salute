from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.database.models.channel import Channel


def channel_settings_keyboard(channel: Channel) -> InlineKeyboardMarkup:
    autoapprove_texts = {
        "none": "❌",
        "instant": "✅ Сразу",
        "1min": "⏱ 1 мин",
        "5min": "⏱ 5 мин"
    }

    label = autoapprove_texts.get(channel.auto_approve_mode)

    if not label and channel.auto_approve_mode and channel.auto_approve_mode.endswith("s"):
        seconds = channel.auto_approve_mode.replace("s", "")
        label = f"⌛ {seconds} сек"

    label = label or "❌"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Приветственное сообщение", callback_data=f"welcome_menu:{channel.id}")],
        [InlineKeyboardButton(text=f"⚙ Автоодобрение", callback_data=f"autoapprove_menu:{channel.id}")],
        [InlineKeyboardButton(text="🛡 Капча", callback_data=f"captcha_menu:{channel.id}")],
        # [InlineKeyboardButton(text=f"⚙ Автоодобрение: {label}", callback_data=f"autoapprove_menu:{channel.id}")],
        [InlineKeyboardButton(text="🗑 Удалить канал", callback_data=f"delete_channel:{channel.id}")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back_to_main_menu")]
    ])
