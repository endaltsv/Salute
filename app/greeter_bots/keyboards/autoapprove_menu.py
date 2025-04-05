from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def autoapprove_keyboard(current: str, channel_id: int) -> InlineKeyboardMarkup:
    modes = {
        "instant": "Да, сразу",
        "1min": "Через минуту",
        "5min": "Через 5 минут",
        "none": "Нет"
    }

    keyboard = []

    # 👇 Если режим кастомный (например, '35s')
    if current and current.endswith("s"):
        seconds = current.replace("s", "")
        keyboard.append([
            InlineKeyboardButton(text=f"✅ Через {seconds} сек",
                                 callback_data=f"set_autoapprove:{current}:{channel_id}")
        ])

    # 👇 Основные варианты
    for key, label in modes.items():
        mark = "✅" if current == key else "⚪"
        keyboard.append([
            InlineKeyboardButton(text=f"{mark} {label}", callback_data=f"set_autoapprove:{key}:{channel_id}")
        ])

    # 👇 Кнопка ручного ввода
    keyboard.append([
        InlineKeyboardButton(text="✏️ Указать вручную", callback_data=f"custom_autoapprove:{channel_id}")
    ])
    keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data=f"channel_menu:{channel_id}")
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
