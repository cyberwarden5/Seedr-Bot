"""Bot FSM states."""
from aiogram.fsm.state import State, StatesGroup


class CheckStates(StatesGroup):
    """States for checking operations."""
    waiting_for_file = State()
    checking = State()