# app/main_bot/states/create_bot.py

from aiogram.fsm.state import StatesGroup, State

class CreateBotState(StatesGroup):
    waiting_for_token = State()
