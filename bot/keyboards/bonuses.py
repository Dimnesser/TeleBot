"""Клавиатуры раздела «Бонусы» (рефералы + стейкинг)."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.callbacks import (
    BonusesTabCB,
    MainMenuCB,
    StakeCancelCB,
    StakeClaimCB,
    StakeConfirmCB,
    StakeStartCB,
)
from bot.services.staking_service import STAKE_TIERS


def _tabs_row(active: str) -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(
            text="• 👥 Рефералы" if active == "referral" else "👥 Рефералы",
            callback_data=BonusesTabCB(tab="referral").pack(),
        ),
        InlineKeyboardButton(
            text="• 🔒 Стейкинг" if active == "staking" else "🔒 Стейкинг",
            callback_data=BonusesTabCB(tab="staking").pack(),
        ),
    ]


def referral_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(*_tabs_row("referral"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data=MainMenuCB(section="home").pack()))
    return builder.as_markup()


def staking_tiers_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(*_tabs_row("staking"))
    for tier in STAKE_TIERS:
        builder.row(
            InlineKeyboardButton(
                text=f"{tier.label} +{tier.bonus_percent}%",
                callback_data=StakeStartCB(term_days=tier.term_days).pack(),
            )
        )
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data=MainMenuCB(section="home").pack()))
    return builder.as_markup()


def staking_active_keyboard(claimable: bool, stake_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(*_tabs_row("staking"))
    if claimable:
        builder.row(InlineKeyboardButton(text="💰 Забрать", callback_data=StakeClaimCB(stake_id=stake_id).pack()))
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data=MainMenuCB(section="home").pack()))
    return builder.as_markup()


def staking_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Заморозить", callback_data=StakeConfirmCB().pack()),
        InlineKeyboardButton(text="✖ Отмена", callback_data=StakeCancelCB().pack()),
    )
    return builder.as_markup()
