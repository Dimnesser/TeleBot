"""Клавиатура главного меню (аналог бокового меню-гамбургера)."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.keyboards.callbacks import CasesCategoryCB, MainMenuCB
from bot.keyboards.cases import CATEGORY_LABELS

# [ПОДТВЕРЖДЕНО СКРИНШОТОМ] порядок пунктов — из бокового меню:
# ГЛАВНАЯ, АПГРЕЙДЕР, БАТЛ, ДАЙСЫ, КРАШ, КВЕСТЫ, РОЗЫГРЫШИ, FAQ, БОНУСЫ.
# [ЛОГИЧЕСКИ ПРЕДПОЛОЖЕНО] пункт «ПОПОЛНИТЬ БАЛАНС» добавлен отдельно — на
# скриншотах вход в раздел пополнения не показан явно (вероятно, кнопка
# кошелька в профиле). Категории кейсов на скриншотах видны сразу на
# главной странице скроллом — здесь вынесены наверх меню быстрыми
# кнопками (см. main_menu_keyboard), а не гаданием об отдельном пункте.
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

    category_row: list[InlineKeyboardButton] = []
    for category, label in CATEGORY_LABELS.items():
        category_row.append(
            InlineKeyboardButton(text=label, callback_data=CasesCategoryCB(category=category.value).pack())
        )
        if len(category_row) == 2:
            builder.row(*category_row)
            category_row = []
    if category_row:
        builder.row(*category_row)

    for section, label in MENU_SECTIONS:
        builder.row(InlineKeyboardButton(text=label, callback_data=MainMenuCB(section=section).pack()))
    return builder.as_markup()
