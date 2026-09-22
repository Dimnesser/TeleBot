"""Сборка всех роутеров бота."""
from __future__ import annotations

from aiogram import Router

from bot.handlers import battle, bonuses, crash, dice, faq, giveaways, menu, quests, start, upgrader
from bot.handlers.cases import catalog as cases_catalog
from bot.handlers.deposit import admin as deposit_admin
from bot.handlers.deposit import catalog as deposit_catalog
from bot.handlers.deposit import stars as deposit_stars

routers: list[Router] = [
    start.router,
    menu.router,
    deposit_catalog.router,
    deposit_stars.router,
    deposit_admin.router,
    cases_catalog.router,
    upgrader.router,
    crash.router,
    dice.router,
    quests.router,
    bonuses.router,
    battle.router,
    giveaways.router,
    faq.router,
]
