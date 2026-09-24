"""Клавиатуры раздела пополнения баланса (обменник)."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.data.buffs import BuffOption
from bot.database.models import DepositCategory, DepositItem
from bot.keyboards.callbacks import (
    DepositAdminCB,
    DepositBuffCB,
    DepositCloseCB,
    DepositConfirmCB,
    DepositNextCB,
    DepositQtyCB,
    DepositQueueCB,
    DepositResetFiltersCB,
    DepositSearchCB,
    DepositSortCB,
    DepositTabCB,
    StarsCreateInvoiceCB,
    StarsSkipPromoCB,
)

CATEGORY_TAB_LABELS = {
    DepositCategory.BRAINROT.value: "🧩 Брейнроты",
    DepositCategory.HIRSY.value: "🌈 Гирсы",
    "stars": "⭐ Stars",
}

NOOP = "noop"


def _tabs_row(active: str) -> list[InlineKeyboardButton]:
    buttons = []
    for category, label in CATEGORY_TAB_LABELS.items():
        text = f"• {label}" if active == category else label
        buttons.append(InlineKeyboardButton(text=text, callback_data=DepositTabCB(category=category).pack()))
    return buttons


MAX_CATALOG_ROWS = 18


def catalog_keyboard(
    items: list[DepositItem],
    cart: dict[int, int],
    active_category: str,
    sort_desc: bool,
    buff: BuffOption,
    can_submit: bool,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(*_tabs_row(active_category))

    # Telegram принимает не больше 100 кнопок в клавиатуре (4 на предмет):
    # показываем первые MAX_CATALOG_ROWS, остальные — через поиск/сортировку.
    for item in items[:MAX_CATALOG_ROWS]:
        qty = cart.get(item.id, 0)
        min_note = f" · от {item.min_qty} шт" if item.min_qty > 1 else ""
        hot_note = f"🔥 Осталось {item.hot_stock_left} · " if item.hot_stock_left else ""
        label = f"{hot_note}{item.emoji} {item.name} — {item.price_b} B{min_note}"
        builder.row(InlineKeyboardButton(text=label, callback_data=NOOP))
        builder.row(
            InlineKeyboardButton(text="➖", callback_data=DepositQtyCB(item_id=item.id, delta=-1).pack()),
            InlineKeyboardButton(text=str(qty), callback_data=NOOP),
            InlineKeyboardButton(text="➕", callback_data=DepositQtyCB(item_id=item.id, delta=1).pack()),
        )

    if len(items) > MAX_CATALOG_ROWS:
        builder.row(InlineKeyboardButton(
            text=f"…ещё {len(items) - MAX_CATALOG_ROWS} — найди через 🔍 Поиск", callback_data=NOOP))
    builder.row(
        InlineKeyboardButton(text="🔍 Поиск", callback_data=DepositSearchCB().pack()),
        InlineKeyboardButton(
            text="Цена ↓" if not sort_desc else "Цена ↑",
            callback_data=DepositSortCB(direction="desc" if not sort_desc else "asc").pack(),
        ),
        InlineKeyboardButton(text="✖ Сброс", callback_data=DepositResetFiltersCB().pack()),
    )
    builder.row(InlineKeyboardButton(text=f"Бафы: {buff.label} ▾", callback_data=DepositBuffCB().pack()))

    if can_submit:
        builder.row(InlineKeyboardButton(text="ДАЛЕЕ →", callback_data=DepositNextCB().pack()))

    builder.row(InlineKeyboardButton(text="✕ Закрыть", callback_data=DepositCloseCB().pack()))
    return builder.as_markup()


def confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Отправить заявку", callback_data=DepositConfirmCB(action="send").pack()),
        InlineKeyboardButton(text="✖ Отмена", callback_data=DepositConfirmCB(action="cancel").pack()),
    )
    return builder.as_markup()


def deposit_unavailable_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="Закрыть", callback_data=DepositQueueCB(action="close").pack()),
        InlineKeyboardButton(text="ВСТАТЬ В ОЧЕРЕДЬ", callback_data=DepositQueueCB(action="join").pack()),
    )
    return builder.as_markup()


def admin_request_keyboard(request_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Одобрить", callback_data=DepositAdminCB(request_id=request_id, action="approve").pack()
        ),
        InlineKeyboardButton(
            text="❌ Отклонить", callback_data=DepositAdminCB(request_id=request_id, action="reject").pack()
        ),
    )
    return builder.as_markup()


def stars_amount_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(*_tabs_row("stars"))
    builder.row(InlineKeyboardButton(text="✕ Отмена", callback_data=DepositCloseCB().pack()))
    return builder.as_markup()


def stars_promo_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Пропустить", callback_data=StarsSkipPromoCB().pack()))
    builder.row(InlineKeyboardButton(text="✕ Отмена", callback_data=DepositCloseCB().pack()))
    return builder.as_markup()


def stars_invoice_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="СОЗДАТЬ СЧЁТ В STARS", callback_data=StarsCreateInvoiceCB().pack()))
    builder.row(InlineKeyboardButton(text="✕ Отмена", callback_data=DepositCloseCB().pack()))
    return builder.as_markup()
