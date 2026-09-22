"""Навигация по разделам главного меню."""
from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.database.engine import async_session
from bot.database.models import CaseCategory
from bot.database.repo.users import get_user_by_tg_id
from bot.handlers.cases.catalog import open_cases_home
from bot.handlers.deposit.catalog import DEFAULT_CATALOG_STATE, open_catalog
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

    if section == "cases":
        await open_cases_home(callback, state, category=CaseCategory.CASES, page=0)
        return

    if section == "home":
        await _render_home(callback)
        return

    await callback.answer(SECTION_IN_PROGRESS, show_alert=True)


async def _render_home(callback: CallbackQuery) -> None:
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
