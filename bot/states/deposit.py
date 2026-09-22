"""FSM-состояния раздела пополнения баланса."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class DepositCatalog(StatesGroup):
    browsing = State()
    waiting_search = State()
    waiting_nickname = State()


class DepositStars(StatesGroup):
    waiting_amount = State()
    waiting_promo = State()
