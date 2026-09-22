"""Клавиатуры раздела кейсов."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.database.models import Case, CaseCategory
from bot.keyboards.callbacks import (
    CaseConfirmOpenCB,
    CaseOpenViewCB,
    CaseQtySelectCB,
    CasesCategoryCB,
    CasesInventoryCB,
    CasesTopUpCB,
)

CATEGORY_LABELS = {
    CaseCategory.CASES: "📦 Кейсы",
    CaseCategory.THEMATIC: "🎭 Тематические",
    CaseCategory.ALLIN: "🎰 ALL-IN",
    CaseCategory.PARTNERS: "🤝 Партнёры",
    CaseCategory.FREE: "🎁 Бесплатные",
}

PAGE_SIZE = 6


def _category_tab_rows(active: CaseCategory) -> list[list[InlineKeyboardButton]]:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for category, label in CATEGORY_LABELS.items():
        text = f"• {label}" if category == active else label
        row.append(InlineKeyboardButton(text=text, callback_data=CasesCategoryCB(category=category.value).pack()))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return rows


def category_tabs_keyboard(active: CaseCategory) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for row in _category_tab_rows(active):
        builder.row(*row)
    return builder.as_markup()


def cases_list_keyboard(cases: list[Case], category: CaseCategory, page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for row in _category_tab_rows(category):
        builder.row(*row)

    start = page * PAGE_SIZE
    page_items = cases[start : start + PAGE_SIZE]
    for case in page_items:
        price = f"{case.price_tokens} 🎫" if case.price_tokens is not None else "цена уточняется"
        count = f"{case.item_count_label} предм." if case.item_count_label is not None else "? предм."
        lock = "" if case.is_openable else "🔒 "
        label = f"{lock}{case.name} — {price} · {count}"
        builder.row(InlineKeyboardButton(text=label, callback_data=CaseOpenViewCB(case_id=case.id).pack()))

    nav_row = []
    if page > 0:
        nav_row.append(
            InlineKeyboardButton(text="⬅️", callback_data=CasesCategoryCB(category=category.value, page=page - 1).pack())
        )
    if start + PAGE_SIZE < len(cases):
        nav_row.append(
            InlineKeyboardButton(text="➡️", callback_data=CasesCategoryCB(category=category.value, page=page + 1).pack())
        )
    if nav_row:
        builder.row(*nav_row)

    builder.row(InlineKeyboardButton(text="🎒 Инвентарь", callback_data=CasesInventoryCB().pack()))
    builder.row(InlineKeyboardButton(text="🎁 Пополнить демо-баланс", callback_data=CasesTopUpCB().pack()))
    return builder.as_markup()


def case_detail_keyboard(case: Case, qty: int, category: CaseCategory, page: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    qty_row = []
    for option in (1, 3, 5):
        text = f"• {option}" if option == qty else str(option)
        qty_row.append(InlineKeyboardButton(text=text, callback_data=CaseQtySelectCB(case_id=case.id, qty=option).pack()))
    builder.row(*qty_row)

    if case.is_openable:
        builder.row(
            InlineKeyboardButton(
                text=f"ОТКРЫТЬ КЕЙС ×{qty}", callback_data=CaseConfirmOpenCB(case_id=case.id, qty=qty).pack()
            )
        )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад к списку", callback_data=CasesCategoryCB(category=category.value, page=page).pack())
    )
    return builder.as_markup()
