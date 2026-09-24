"""Клавиатура бокового меню (гамбургер) — [ПОДТВЕРЖДЕНО СКРИНШОТОМ]."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.config import config
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
    # Telegram принимает web_app-кнопку только на https-адресе — если
    # WEBAPP_URL не задан (Mini App ещё не выложен), кнопку просто не рисуем,
    # чтобы не падать при отправке клавиатуры.
    if config.webapp_url:
        builder.row(InlineKeyboardButton(text="🎮 ОТКРЫТЬ MINI APP", web_app=WebAppInfo(url=config.webapp_url)))
    for section, label in MENU_SECTIONS:
        builder.row(InlineKeyboardButton(text=label, callback_data=MainMenuCB(section=section).pack()))
    return builder.as_markup()


def welcome_keyboard(news_url: str | None, support_url: str | None) -> InlineKeyboardMarkup:
    """Кнопки под приветствием: «Играть!» (Mini App), «Новости», «Поддержка».
    Ссылки задаёт админ в Mini App; незаданные кнопки не рисуются."""
    builder = InlineKeyboardBuilder()
    if config.webapp_url:
        builder.row(InlineKeyboardButton(text="🚀 Играть!", web_app=WebAppInfo(url=config.webapp_url)))
    links = [InlineKeyboardButton(text=t, url=u) for t, u in (("Новости", news_url), ("Поддержка", support_url)) if u]
    if links:
        builder.row(*links)
    return builder.as_markup()
