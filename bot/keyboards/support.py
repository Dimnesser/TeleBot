"""Кнопки поддержки."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.callbacks import SupportCB
from bot.utils.texts import FAQ_ENTRIES


def support_keyboard() -> InlineKeyboardMarkup:
    """Частые вопросы — по кнопке ответ сразу; внизу «Завершить»."""
    builder = InlineKeyboardBuilder()
    for idx, (question, _) in enumerate(FAQ_ENTRIES):
        builder.row(InlineKeyboardButton(text=f"❓ {question}", callback_data=SupportCB(action="faq", idx=idx).pack()))
    builder.row(InlineKeyboardButton(text="✖️ Завершить обращение", callback_data=SupportCB(action="close").pack()))
    return builder.as_markup()


def support_open_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🆘 Написать в поддержку", callback_data=SupportCB(action="open").pack()))
    return builder.as_markup()
