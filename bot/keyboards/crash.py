"""Клавиатуры раздела «Краш»."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.models import InventoryItem
from bot.keyboards.callbacks import (
    CrashCashoutCB,
    CrashHomeCB,
    CrashPickItemCB,
    CrashPickItemsCB,
    CrashStartCB,
    MainMenuCB,
)

PAGE_SIZE = 8


def crash_home_keyboard(has_stake: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="↓ Выбрать брейнрота", callback_data=CrashPickItemsCB(page=0).pack()))
    if has_stake:
        builder.row(InlineKeyboardButton(text="🚀 СТАРТ", callback_data=CrashStartCB().pack()))
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data=MainMenuCB(section="home").pack()))
    return builder.as_markup()


def crash_items_keyboard(items: list[InventoryItem], page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    start = page * PAGE_SIZE
    page_items = items[start : start + PAGE_SIZE]
    for item in page_items:
        builder.row(
            InlineKeyboardButton(
                text=f"{item.item_name} — {item.value} B", callback_data=CrashPickItemCB(item_id=item.id).pack()
            )
        )

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=CrashPickItemsCB(page=page - 1).pack()))
    if start + PAGE_SIZE < len(items):
        nav.append(InlineKeyboardButton(text="➡️", callback_data=CrashPickItemsCB(page=page + 1).pack()))
    if nav:
        builder.row(*nav)

    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=CrashHomeCB().pack()))
    return builder.as_markup()


def crash_in_flight_keyboard(multiplier: float) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f"🛑 ЗАБРАТЬ ×{multiplier}", callback_data=CrashCashoutCB().pack()))
    return builder.as_markup()
