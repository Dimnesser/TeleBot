"""Клавиатура раздела «Розыгрыши»."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.models import Giveaway
from bot.keyboards.callbacks import GiveawayJoinCB, MainMenuCB


def giveaways_keyboard(giveaways: list[Giveaway], joined_ids: set[int]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for giveaway in giveaways:
        if giveaway.id in joined_ids:
            continue
        builder.row(
            InlineKeyboardButton(
                text=f"🏆 Участвовать: {giveaway.title}",
                callback_data=GiveawayJoinCB(giveaway_id=giveaway.id).pack(),
            )
        )
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data=MainMenuCB(section="home").pack()))
    return builder.as_markup()
