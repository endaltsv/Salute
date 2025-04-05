# app/greeter_bots/states/add_channel.py

from aiogram.fsm.state import StatesGroup, State

class AddChannelState(StatesGroup):
    waiting_for_channel = State()
