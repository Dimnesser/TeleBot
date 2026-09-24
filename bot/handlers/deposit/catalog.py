"""Каталог депозита предметами: «Брейнроты» и «Гирсы»."""
from __future__ import annotations

from typing import Any

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.database.engine import async_session
from bot.database.models import DepositCategory
from bot.database.repo import deposit_items as items_repo
from bot.database.repo.users import get_or_create_user
from bot.keyboards.callbacks import (
    DepositCloseCB,
    DepositConfirmCB,
    DepositNextCB,
    DepositQtyCB,
    DepositResetFiltersCB,
    DepositSearchCB,
    DepositSortCB,
    DepositTabCB,
)
from bot.keyboards.deposit import catalog_keyboard, confirm_keyboard
from bot.services.deposit_moderation import DepositAlreadyOpen, submit_deposit
from bot.services.deposit_service import apply_delta, cart_is_valid, cart_total, get_buff
from bot.states.deposit import DepositCatalog
from bot.utils.texts import (
    CATALOG_DESCRIPTION,
    CATALOG_HEADER,
    CATALOG_HINT,
    CATALOG_NEED_ITEM,
    CATALOG_TOTAL_LINE,
    DEPOSIT_ASK_NICKNAME,
    DEPOSIT_CANCELLED_TEXT,
    DEPOSIT_CLOSED_TEXT,
    DEPOSIT_CONFIRM_TEXT,
    DEPOSIT_NICKNAME_INVALID,
    DEPOSIT_ALREADY_OPEN_TEXT,
    DEPOSIT_QUEUED_TEXT,
    DEPOSIT_SUBMITTED_TEXT,
)

router = Router(name="deposit_catalog")

NO_BUFF = get_buff("none")  # бафы убраны: цена заявки — ровно цена предметов

DEFAULT_CATALOG_STATE: dict[str, Any] = {
    "category": DepositCategory.BRAINROT.value,
    "cart": {},
    "sort_desc": False,
    "search": None,
}


async def _load_state(state: FSMContext) -> dict[str, Any]:
    data = await state.get_data()
    return {**DEFAULT_CATALOG_STATE, **data}


async def _render(message: Message, state: FSMContext, *, edit: bool) -> None:
    data = await _load_state(state)
    category = DepositCategory(data["category"])
    cart: dict[int, int] = {int(k): v for k, v in data["cart"].items()}
    sort_desc: bool = data["sort_desc"]
    search: str | None = data["search"]
    async with async_session() as session:
        items = await items_repo.list_items(session, category, search=search, sort_desc=sort_desc)

    total = cart_total(items, cart, NO_BUFF)
    can_submit = cart_is_valid(items, cart)

    body = CATALOG_TOTAL_LINE.format(total=total) if can_submit else CATALOG_HINT
    text = f"{CATALOG_HEADER[category]}\n\n{CATALOG_DESCRIPTION[category]}\n\n{body}"
    markup = catalog_keyboard(items, cart, category.value, sort_desc, can_submit)

    if edit:
        await message.edit_text(text, reply_markup=markup)
    else:
        await message.answer(text, reply_markup=markup)


async def open_catalog(callback: CallbackQuery, state: FSMContext, category: str) -> None:
    await state.set_state(DepositCatalog.browsing)
    data = await _load_state(state)
    if data["category"] != category:
        data = {**DEFAULT_CATALOG_STATE, "category": category}
        await state.set_data(data)
    await _render(callback.message, state, edit=True)
    await callback.answer()


@router.callback_query(DepositTabCB.filter())
async def handle_tab(callback: CallbackQuery, callback_data: DepositTabCB, state: FSMContext) -> None:
    if callback_data.category == "stars":
        from bot.handlers.deposit.stars import open_stars_tab

        await open_stars_tab(callback, state)
        return

    await open_catalog(callback, state, category=callback_data.category)


@router.callback_query(DepositQtyCB.filter())
async def handle_qty(callback: CallbackQuery, callback_data: DepositQtyCB, state: FSMContext) -> None:
    data = await _load_state(state)
    category = DepositCategory(data["category"])
    cart: dict[int, int] = {int(k): v for k, v in data["cart"].items()}

    async with async_session() as session:
        item = await items_repo.get_item(session, callback_data.item_id)

    if item is None or item.category != category:
        await callback.answer()
        return

    new_qty = apply_delta(item, cart.get(item.id, 0), callback_data.delta)
    if new_qty:
        cart[item.id] = new_qty
    else:
        cart.pop(item.id, None)

    await state.update_data(cart=cart)
    await _render(callback.message, state, edit=True)
    await callback.answer()


@router.callback_query(DepositSortCB.filter())
async def handle_sort(callback: CallbackQuery, callback_data: DepositSortCB, state: FSMContext) -> None:
    await state.update_data(sort_desc=callback_data.direction == "desc")
    await _render(callback.message, state, edit=True)
    await callback.answer()


@router.callback_query(DepositResetFiltersCB.filter())
async def handle_reset(callback: CallbackQuery, state: FSMContext) -> None:
    data = await _load_state(state)
    await state.update_data(search=None, sort_desc=False, cart={}, category=data["category"])
    await _render(callback.message, state, edit=True)
    await callback.answer("Фильтры сброшены")


@router.callback_query(DepositSearchCB.filter())
async def handle_search_prompt(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(DepositCatalog.waiting_search)
    await callback.message.answer("Введите часть названия предмета для поиска (или /cancel):")
    await callback.answer()


@router.message(DepositCatalog.waiting_search)
async def handle_search_input(message: Message, state: FSMContext) -> None:
    query = (message.text or "").strip()
    await state.set_state(DepositCatalog.browsing)
    if query == "/cancel":
        await message.answer("Поиск отменён.")
        return
    await state.update_data(search=query or None)
    await _render(message, state, edit=False)


@router.callback_query(DepositCloseCB.filter())
async def handle_close(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(DEPOSIT_CLOSED_TEXT)
    await callback.answer()


@router.callback_query(DepositNextCB.filter())
async def handle_next(callback: CallbackQuery, state: FSMContext) -> None:
    data = await _load_state(state)
    category = DepositCategory(data["category"])
    cart: dict[int, int] = {int(k): v for k, v in data["cart"].items()}

    async with async_session() as session:
        items = await items_repo.list_items(session, category)

    if not cart_is_valid(items, cart):
        await callback.answer(CATALOG_NEED_ITEM, show_alert=True)
        return

    await state.set_state(DepositCatalog.waiting_nickname)
    await callback.message.edit_text(DEPOSIT_ASK_NICKNAME)
    await callback.answer()


@router.message(DepositCatalog.waiting_nickname)
async def handle_nickname(message: Message, state: FSMContext) -> None:
    nickname = (message.text or "").strip()
    if not (2 <= len(nickname) <= 32):
        await message.answer(DEPOSIT_NICKNAME_INVALID)
        return

    data = await _load_state(state)
    category = DepositCategory(data["category"])
    cart: dict[int, int] = {int(k): v for k, v in data["cart"].items()}
    async with async_session() as session:
        items = await items_repo.list_items(session, category)
        if not cart_is_valid(items, cart):
            await message.answer(CATALOG_NEED_ITEM)
            await state.set_state(DepositCatalog.browsing)
            return
        total = cart_total(items, cart, NO_BUFF)

    await state.update_data(nickname=nickname, total=total)
    await state.set_state(DepositCatalog.browsing)

    items_by_id = {item.id: item for item in items}
    items_text = ", ".join(f"{items_by_id[item_id].emoji} {items_by_id[item_id].name} × {qty}" for item_id, qty in cart.items())

    await message.answer(
        DEPOSIT_CONFIRM_TEXT.format(nickname=nickname, items=items_text, total=total),
        reply_markup=confirm_keyboard(),
    )


@router.callback_query(DepositConfirmCB.filter())
async def handle_confirm(callback: CallbackQuery, callback_data: DepositConfirmCB, state: FSMContext) -> None:
    if callback_data.action == "cancel":
        await callback.message.edit_text(DEPOSIT_CANCELLED_TEXT)
        await callback.answer()
        return

    data = await _load_state(state)
    category = DepositCategory(data["category"])
    cart: dict[int, int] = {int(k): v for k, v in data["cart"].items()}
    nickname = data.get("nickname")
    if not nickname or not cart:
        await callback.answer("Заявка устарела, начните заново.", show_alert=True)
        return

    async with async_session() as session:
        user = await get_or_create_user(
            session, callback.from_user.id, callback.from_user.username, callback.from_user.first_name
        )
        items = await items_repo.list_items(session, category)
        try:
            request, position = await submit_deposit(session, callback.bot, user, category, cart, nickname, items)
        except DepositAlreadyOpen as exc:
            await callback.answer(DEPOSIT_ALREADY_OPEN_TEXT.format(request_id=exc.request.id), show_alert=True)
            return

    text = (DEPOSIT_SUBMITTED_TEXT.format(request_id=request.id) if position == 1
            else DEPOSIT_QUEUED_TEXT.format(request_id=request.id, position=position))
    await callback.message.edit_text(text)
    await callback.answer()
    await state.set_data({**DEFAULT_CATALOG_STATE, "category": category.value})
