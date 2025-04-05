from aiogram.fsm.state import StatesGroup, State

class WelcomeState(StatesGroup):
    entering_text = State()
    entering_button_text = State()
    entering_button_url = State()
