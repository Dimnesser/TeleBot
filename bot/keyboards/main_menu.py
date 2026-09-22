"""Клавиатура бокового меню (гамбургер) — [ПОДТВЕРЖДЕНО СКРИНШОТОМ]."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.callbacks import MainMenuCB

# [ПОДТВЕРЖДЕНО СКРИНШОТОМ] порядок пунктов — из бокового меню:
# ГЛАВНАЯ, АПГРЕЙДЕР, БАТЛ, ДАЙСЫ, КРАШ, КВЕСТЫ, РОЗЫГРЫШИ, FAQ, БОНУСЫ.
# «ГЛАВНАЯ» на скриншотах — это сама лента кейсов (см. cases_list_keyboard),
# а не текстовый список разделов: это меню — гамбургер поверх неё.
# [ЛОГИЧЕСКИ ПРЕДПОЛОЖЕНО] пункт «ПОПОЛНИТЬ БАЛАНС» добавлен отдельно — на
# скриншотах вход в раздел пополнения не показан явно (вероятно, кнопка
# кошелька в профиле).
MENU_SECTIONS: list[tuple[str, str]] = [
    ("home", "🏠 ГЛАВНАЯ"),
    ("deposit", "💰 ПОПОЛНИТЬ БАЛАНС"),
    ("upgrader", "⬆️ АПГРЕЙДЕР"),
    ("battle", "🛡️ БАТЛ"),
    ("dice", "🎲 ДАЙСЫ"),
    ("crash", "🚀 КРАШ"),
    ("quests", "📋 КВЕСТЫ"),
    ("giveaways", "🏆 РОЗЫГРЫШИ"),
    ("faq", "❓ FAQ"),
    ("bonuses", "🍀 БОНУСЫ"),
]


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for section, label in MENU_SECTIONS:
        builder.row(InlineKeyboardButton(text=label, callback_data=MainMenuCB(section=section).pack()))
    return builder.as_markup()
