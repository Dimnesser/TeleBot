"""FSM-состояние ввода суммы стейкинга."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class StakingStates(StatesGroup):
    waiting_amount = State()
