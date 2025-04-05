from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def channel_selection_keyboard(channels: list, selected_ids: set) -> InlineKeyboardMarkup:
    buttons = []

    for ch in channels:
        selected = "✅ " if ch.id in selected_ids else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{selected}{ch.channel_name or ch.channel_id}",
                callback_data=f"broadcast_toggle:{ch.id}"
            )
        ])

    buttons.append([
        InlineKeyboardButton(text="✅ Все каналы", callback_data="broadcast_all"),
    ])
    buttons.append([
        InlineKeyboardButton(text="🚀 Запустить рассылку", callback_data="broadcast_start")
    ])
    buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
