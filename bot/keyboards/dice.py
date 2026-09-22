"""Клавиатуры раздела «Дайсы»."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.models import InventoryItem
from bot.keyboards.callbacks import (
    DiceHomeCB,
    DicePickColorCB,
    DicePickItemCB,
    DicePickItemsCB,
    DiceResetCB,
    DiceRollCB,
    MainMenuCB,
)
from bot.services.dice_service import COLORS

PAGE_SIZE = 8


def dice_home_keyboard(has_stake: bool, selected_color: str | None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="↓ Выбрать ставку", callback_data=DicePickItemsCB(page=0).pack()))

    color_buttons = [
        InlineKeyboardButton(
            text=f"• {color}" if color == selected_color else color, callback_data=DicePickColorCB(color=color).pack()
        )
        for color in COLORS
    ]
    builder.row(*color_buttons[:3])
    builder.row(*color_buttons[3:])

    if has_stake and selected_color:
        builder.row(InlineKeyboardButton(text="🎲 БРОСИТЬ", callback_data=DiceRollCB().pack()))
    if has_stake or selected_color:
        builder.row(InlineKeyboardButton(text="🔄 Сбросить выбор", callback_data=DiceResetCB().pack()))
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data=MainMenuCB(section="home").pack()))
    return builder.as_markup()


def dice_items_keyboard(items: list[InventoryItem], page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    start = page * PAGE_SIZE
    page_items = items[start : start + PAGE_SIZE]
    for item in page_items:
        builder.row(
            InlineKeyboardButton(
                text=f"{item.item_name} — {item.value} B", callback_data=DicePickItemCB(item_id=item.id).pack()
            )
        )

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=DicePickItemsCB(page=page - 1).pack()))
    if start + PAGE_SIZE < len(items):
        nav.append(InlineKeyboardButton(text="➡️", callback_data=DicePickItemsCB(page=page + 1).pack()))
    if nav:
        builder.row(*nav)

    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=DiceHomeCB().pack()))
    return builder.as_markup()
