from aiogram.fsm.state import StatesGroup, State

class BroadcastState(StatesGroup):
    choosing_channels = State()
    entering_message = State()
    ask_add_button = State()
    entering_button_text = State()
    entering_button_url = State()
