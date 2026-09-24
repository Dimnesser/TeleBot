"""Каталог и открытие кейсов в чате (оплата балансом B)."""
from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.database.engine import async_session
from bot.database.models import CaseCategory
from bot.database.repo import cases as cases_repo
from bot.database.repo import inventory as inventory_repo
from bot.database.repo.users import add_balance, get_or_create_user
from bot.config import config
from bot.keyboards.callbacks import (
    CaseConfirmOpenCB,
    CaseOpenViewCB,
    CaseQtySelectCB,
    CasesCategoryCB,
    CasesInventoryCB,
)
from bot.keyboards.cases import case_detail_keyboard, cases_list_keyboard
from bot.services import quest_service
from bot.data.brainrot_roster import RARITY_LABEL, rarity_for
from bot.services.cases_service import draw_items, total_cost
from bot.utils.texts import (
    CASE_DETAIL_BALANCE_LINE,
    CASE_DETAIL_DROP_POOL_HEADER,
    CASE_DETAIL_HEADER,
    CASE_DETAIL_NOT_OPENABLE,
    CASE_DETAIL_NOTE_LINE,
    CASE_DETAIL_PRICE_LINE,
    CASE_DETAIL_PRICE_UNKNOWN_LINE,
    CASE_DETAIL_TOTAL_COST_LINE,
    CASE_OPEN_NOT_ENOUGH_TOKENS,
    CASE_OPEN_NOT_OPENABLE_ALERT,
    CASE_OPEN_NO_PRICE_ALERT,
    CASE_OPEN_RESULT_FOOTER,
    CASE_OPEN_RESULT_HEADER,
    CASE_OPEN_RESULT_LINE,
    CASES_CATEGORY_TITLES,
    CASES_HOME_TEXT,
    CASES_INVENTORY_EMPTY,
    CASES_INVENTORY_HEADER,
    CASES_INVENTORY_LINE,
)

router = Router(name="cases_catalog")

INVENTORY_LIMIT = 10


async def open_cases_home(
    callback: CallbackQuery, state: FSMContext, category: CaseCategory = CaseCategory.STARTER, page: int = 0
) -> None:
    await state.update_data(cases_category=category.value, cases_page=page)

    async with async_session() as session:
        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        cases = await cases_repo.list_cases(session, category)

    text = CASES_HOME_TEXT.format(title=CASES_CATEGORY_TITLES[category], tokens=user.balance)
    markup = cases_list_keyboard(cases, category, page)

    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(CasesCategoryCB.filter())
async def handle_category(callback: CallbackQuery, callback_data: CasesCategoryCB, state: FSMContext) -> None:
    await open_cases_home(callback, state, category=CaseCategory(callback_data.category), page=callback_data.page)


async def _render_case_detail(callback: CallbackQuery, state: FSMContext, case_id: int, qty: int) -> None:
    data = await state.get_data()
    category = CaseCategory(data.get("cases_category", CaseCategory.STARTER.value))
    page = data.get("cases_page", 0)

    async with async_session() as session:
        case = await cases_repo.get_case(session, case_id)
        if case is None:
            await callback.answer("Кейс не найден.", show_alert=True)
            return
        items = await cases_repo.list_case_items(session, case_id)
        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)

    lines = [CASE_DETAIL_HEADER.format(name=case.name)]
    if case.price_tokens is not None:
        lines.append(CASE_DETAIL_PRICE_LINE.format(price=case.price_tokens, count=case.item_count_label or "?"))
    else:
        lines.append(CASE_DETAIL_PRICE_UNKNOWN_LINE.format(count=case.item_count_label or "?"))
    if case.note:
        lines.append(CASE_DETAIL_NOTE_LINE.format(note=case.note))

    lines.append("")
    if items:
        lines.append(CASE_DETAIL_DROP_POOL_HEADER)
        for item in items:
            rarity = RARITY_LABEL[rarity_for(item.name, item.value)]
            lines.append(f"• {item.name} · {rarity} · {item.value} B")
    else:
        lines.append(CASE_DETAIL_NOT_OPENABLE)

    lines.append("")
    lines.append(CASE_DETAIL_BALANCE_LINE.format(tokens=user.balance))
    cost = total_cost(case, qty)
    if cost is not None:
        lines.append(CASE_DETAIL_TOTAL_COST_LINE.format(qty=qty, cost=cost))

    await callback.message.edit_text("\n".join(lines), reply_markup=case_detail_keyboard(case, qty, category, page))
    await callback.answer()


@router.callback_query(CaseOpenViewCB.filter())
async def handle_view(callback: CallbackQuery, callback_data: CaseOpenViewCB, state: FSMContext) -> None:
    await state.update_data(cases_qty=1)
    await _render_case_detail(callback, state, callback_data.case_id, qty=1)


@router.callback_query(CaseQtySelectCB.filter())
async def handle_qty_select(callback: CallbackQuery, callback_data: CaseQtySelectCB, state: FSMContext) -> None:
    await state.update_data(cases_qty=callback_data.qty)
    await _render_case_detail(callback, state, callback_data.case_id, qty=callback_data.qty)


@router.callback_query(CaseConfirmOpenCB.filter())
async def handle_confirm_open(callback: CallbackQuery, callback_data: CaseConfirmOpenCB, state: FSMContext) -> None:
    async with async_session() as session:
        case = await cases_repo.get_case(session, callback_data.case_id)
        if case is None:
            await callback.answer("Кейс не найден.", show_alert=True)
            return
        if not case.is_openable:
            await callback.answer(CASE_OPEN_NOT_OPENABLE_ALERT, show_alert=True)
            return

        cost = total_cost(case, callback_data.qty)
        if cost is None:
            await callback.answer(CASE_OPEN_NO_PRICE_ALERT, show_alert=True)
            return

        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        if user.balance < cost:
            await callback.answer(
                CASE_OPEN_NOT_ENOUGH_TOKENS.format(cost=cost, balance=user.balance), show_alert=True
            )
            return

        items = await cases_repo.list_case_items(session, case.id)
        won = draw_items(items, callback_data.qty, luck=user.luck, case_price=case.price_tokens)

        user.balance -= cost
        await session.commit()
        await session.refresh(user)

        await inventory_repo.add_items(
            session, user, case.name, [(item.name, item.value) for item in won], case_id=case.id
        )
        await quest_service.record_progress(session, user, f"open_case:{case.code}")
        tokens_after = user.balance

    result_lines = [CASE_OPEN_RESULT_HEADER.format(name=case.name, qty=callback_data.qty)]
    result_lines.extend(
        CASE_OPEN_RESULT_LINE.format(name=item.name, value=item.value, rarity=RARITY_LABEL[rarity_for(item.name, item.value)])
        for item in won
    )
    result_lines.append(CASE_OPEN_RESULT_FOOTER.format(tokens=tokens_after))

    await callback.message.edit_text(
        "\n".join(result_lines),
        reply_markup=case_detail_keyboard(case, callback_data.qty, case.category, 0),
    )
    await callback.answer()


@router.callback_query(CasesInventoryCB.filter())
async def handle_inventory(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session() as session:
        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        entries = await inventory_repo.list_recent(session, user, limit=INVENTORY_LIMIT)

    data = await state.get_data()
    category = CaseCategory(data.get("cases_category", CaseCategory.STARTER.value))
    page = data.get("cases_page", 0)

    lines = [CASES_INVENTORY_HEADER.format(limit=INVENTORY_LIMIT)]
    if entries:
        lines.extend(
            CASES_INVENTORY_LINE.format(item_name=e.item_name, case_name=e.case_name, value=e.value) for e in entries
        )
    else:
        lines.append(CASES_INVENTORY_EMPTY)

    async with async_session() as session:
        cases = await cases_repo.list_cases(session, category)

    await callback.message.edit_text("\n".join(lines), reply_markup=cases_list_keyboard(cases, category, page))
    await callback.answer()
