"""Клавиатуры раздела «Батл»."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.models import Case
from bot.keyboards.callbacks import BattleHomeCB, BattleStartCB, MainMenuCB


def battle_cases_keyboard(cases: list[Case]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for case in cases:
        builder.row(
            InlineKeyboardButton(
                text=f"⚔️ {case.name} — вход {case.price_tokens} 🎫",
                callback_data=BattleStartCB(case_id=case.id).pack(),
            )
        )
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data=MainMenuCB(section="home").pack()))
    return builder.as_markup()


def battle_result_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⚔️ Ещё раз", callback_data=BattleHomeCB().pack()))
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data=MainMenuCB(section="home").pack()))
    return builder.as_markup()
