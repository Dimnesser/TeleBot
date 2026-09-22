"""Клавиатура раздела «Квесты»."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.models import Quest
from bot.keyboards.callbacks import MainMenuCB, QuestClaimCB


def quests_keyboard(claimable_quests: list[Quest]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for quest in claimable_quests:
        builder.row(
            InlineKeyboardButton(
                text=f"🎁 Забрать: {quest.title}", callback_data=QuestClaimCB(quest_id=quest.id).pack()
            )
        )
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data=MainMenuCB(section="home").pack()))
    return builder.as_markup()
