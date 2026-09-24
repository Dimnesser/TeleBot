"""Кнопки модератора для заявок на вывод."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.callbacks import WithdrawAdminCB


def admin_withdraw_keyboard(request_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Выдано", callback_data=WithdrawAdminCB(request_id=request_id, action="done").pack()),
        InlineKeyboardButton(text="↩️ Отменить", callback_data=WithdrawAdminCB(request_id=request_id, action="cancel").pack()),
    )
    return builder.as_markup()
