"""Навигация по разделам главного меню."""
from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.database.engine import async_session
from bot.database.models import CaseCategory
from bot.database.repo.users import get_user_by_tg_id
from bot.handlers.battle import open_battle_home
from bot.handlers.bonuses import open_bonuses_home
from bot.handlers.cases.catalog import open_cases_home
from bot.handlers.crash import open_crash_home
from bot.handlers.deposit.catalog import DEFAULT_CATALOG_STATE, open_catalog
from bot.handlers.dice import open_dice_home
from bot.handlers.faq import open_faq_home
from bot.handlers.giveaways import open_giveaways_home
from bot.handlers.quests import open_quests_home
from bot.handlers.upgrader import open_upgrader_home
from bot.keyboards.callbacks import MainMenuCB
from bot.keyboards.main_menu import main_menu_keyboard
from bot.utils.texts import SECTION_IN_PROGRESS, WELCOME_TEXT

router = Router(name="menu")


@router.callback_query(MainMenuCB.filter())
async def handle_menu(callback: CallbackQuery, callback_data: MainMenuCB, state: FSMContext) -> None:
    section = callback_data.section

    if section == "deposit":
        await state.set_data(dict(DEFAULT_CATALOG_STATE))
        await open_catalog(callback, state, category="brainrot")
        return

    if section == "upgrader":
        await open_upgrader_home(callback, state)
        return

    if section == "crash":
        await open_crash_home(callback, state)
        return

    if section == "dice":
        await open_dice_home(callback, state)
        return

    if section == "battle":
        await open_battle_home(callback, state)
        return

    if section == "quests":
        await open_quests_home(callback, state)
        return

    if section == "giveaways":
        await open_giveaways_home(callback, state)
        return

    if section == "faq":
        await open_faq_home(callback, state)
        return

    if section == "bonuses":
        await open_bonuses_home(callback, state)
        return

    if section == "home":
        # [ПОДТВЕРЖДЕНО СКРИНШОТОМ] «ГЛАВНАЯ» — это сама лента кейсов
        # (КЕЙСЫ / ТЕМАТИЧЕСКИЕ / ALL-IN / ПАРТНЁРЫ / БЕСПЛАТНЫЕ), а не
        # текстовый список разделов.
        await open_cases_home(callback, state, category=CaseCategory.STARTER, page=0)
        return

    if section == "menu":
        await _render_drawer(callback)
        return

    await callback.answer(SECTION_IN_PROGRESS, show_alert=True)


async def _render_drawer(callback: CallbackQuery) -> None:
    async with async_session() as session:
        user = await get_user_by_tg_id(session, callback.from_user.id)

    await callback.message.edit_text(
        WELCOME_TEXT.format(
            name=callback.from_user.first_name or "игрок",
            balance=user.balance if user else 0,
        ),
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()
