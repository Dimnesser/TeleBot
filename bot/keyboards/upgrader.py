"""Клавиатуры раздела «Апгрейдер»."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.models import InventoryItem
from bot.database.repo.known_items import KnownItem
from bot.keyboards.callbacks import (
    MainMenuCB,
    UpgraderConfirmCB,
    UpgraderHomeCB,
    UpgraderMyItemsCB,
    UpgraderPickContributionCB,
    UpgraderPickTargetCB,
    UpgraderPresetCB,
    UpgraderResetCB,
    UpgraderTargetsCB,
)

PAGE_SIZE = 8


def upgrader_home_keyboard(
    has_contribution: bool, has_target: bool, contribution_label: str, target_label: str
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f"↓ {contribution_label}", callback_data=UpgraderMyItemsCB(page=0).pack()))
    builder.row(InlineKeyboardButton(text=f"🎯 {target_label}", callback_data=UpgraderTargetsCB(page=0).pack()))

    builder.row(
        InlineKeyboardButton(text="×2", callback_data=UpgraderPresetCB(kind="mult", value=2).pack()),
        InlineKeyboardButton(text="×5", callback_data=UpgraderPresetCB(kind="mult", value=5).pack()),
        InlineKeyboardButton(text="×10", callback_data=UpgraderPresetCB(kind="mult", value=10).pack()),
    )
    builder.row(
        InlineKeyboardButton(text="30%", callback_data=UpgraderPresetCB(kind="chance", value=30).pack()),
        InlineKeyboardButton(text="50%", callback_data=UpgraderPresetCB(kind="chance", value=50).pack()),
        InlineKeyboardButton(text="75%", callback_data=UpgraderPresetCB(kind="chance", value=75).pack()),
    )

    if has_contribution and has_target:
        builder.row(InlineKeyboardButton(text="ПРОКАЧАТЬ ›", callback_data=UpgraderConfirmCB().pack()))
    if has_contribution or has_target:
        builder.row(InlineKeyboardButton(text="🔄 Сбросить выбор", callback_data=UpgraderResetCB().pack()))
    builder.row(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data=MainMenuCB(section="home").pack()))
    return builder.as_markup()


def _pagination_row(page: int, has_more: bool, page_cb_factory) -> list[InlineKeyboardButton]:
    row = []
    if page > 0:
        row.append(InlineKeyboardButton(text="⬅️", callback_data=page_cb_factory(page - 1)))
    if has_more:
        row.append(InlineKeyboardButton(text="➡️", callback_data=page_cb_factory(page + 1)))
    return row


def my_items_keyboard(items: list[InventoryItem], page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    start = page * PAGE_SIZE
    page_items = items[start : start + PAGE_SIZE]
    for item in page_items:
        builder.row(
            InlineKeyboardButton(
                text=f"{item.item_name} — {item.value} B",
                callback_data=UpgraderPickContributionCB(item_id=item.id).pack(),
            )
        )
    nav = _pagination_row(page, start + PAGE_SIZE < len(items), lambda p: UpgraderMyItemsCB(page=p).pack())
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=UpgraderHomeCB().pack()))
    return builder.as_markup()


def targets_keyboard(items: list[KnownItem], page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    start = page * PAGE_SIZE
    page_items = items[start : start + PAGE_SIZE]
    for offset, item in enumerate(page_items):
        index = start + offset
        builder.row(
            InlineKeyboardButton(
                text=f"{item.name} — {item.value} B", callback_data=UpgraderPickTargetCB(index=index).pack()
            )
        )
    nav = _pagination_row(page, start + PAGE_SIZE < len(items), lambda p: UpgraderTargetsCB(page=p).pack())
    if nav:
        builder.row(*nav)
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=UpgraderHomeCB().pack()))
    return builder.as_markup()
