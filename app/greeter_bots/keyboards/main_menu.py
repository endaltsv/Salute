from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.database.models.channel import Channel


def greeter_main_menu(channels: list[Channel] = None) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="➕ Добавить канал", callback_data="add_channel")],
        [
            InlineKeyboardButton(text="📢 Рассылка", callback_data="broadcast_menu"),
            InlineKeyboardButton(text="🗒 Статистика", callback_data="stats")
        ],
    ]

    if channels:
        # 🔹 Добавим пустую строку-разделитель
        keyboard.append([InlineKeyboardButton(text=" ", callback_data="noop")])  # Unicode пустой пробел

        # 🔹 Кнопки каналов по 2 в ряд
        row = []
        for index, ch in enumerate(channels, start=1):
            row.append(
                InlineKeyboardButton(
                    text=ch.channel_name or str(ch.channel_id),
                    callback_data=f"channel_menu:{ch.id}"
                )
            )
            if index % 2 == 0:
                keyboard.append(row)
                row = []

        if row:  # если осталась одна кнопка
            keyboard.append(row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)
