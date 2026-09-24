"""FSM-состояние чата с поддержкой."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class Support(StatesGroup):
    chatting = State()
