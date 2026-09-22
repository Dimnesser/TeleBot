"""Краш: растущий множитель, кэшаут до обрыва, ставка — предмет из инвентаря."""
from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.database.engine import async_session
from bot.database.repo import inventory as inventory_repo
from bot.database.repo.users import get_or_create_user
from bot.keyboards.callbacks import CrashCashoutCB, CrashHomeCB, CrashPickItemCB, CrashPickItemsCB, CrashStartCB
from bot.keyboards.crash import crash_home_keyboard, crash_in_flight_keyboard, crash_items_keyboard
from bot.services import crash_runtime
from bot.utils.texts import (
    CRASH_ALREADY_RESOLVED,
    CRASH_ALREADY_RUNNING,
    CRASH_CASHOUT_SUCCESS,
    CRASH_HISTORY_LABEL,
    CRASH_HOME_DISCLAIMER,
    CRASH_HOME_HEADER,
    CRASH_IN_FLIGHT_TEXT,
    CRASH_ITEM_GONE,
    CRASH_NEED_ITEM_FIRST,
    CRASH_NO_ACTIVE_ROUND,
    CRASH_NO_ITEMS_TEXT,
    CRASH_SLOT_EMPTY,
    CRASH_SLOT_ITEM,
    CRASH_STAKE_LABEL,
)

router = Router(name="crash")


@router.callback_query(CrashHomeCB.filter())
async def open_crash_home(callback: CallbackQuery, state: FSMContext) -> None:
    if crash_runtime.get_active_round(callback.from_user.id):
        await callback.answer(CRASH_ALREADY_RUNNING, show_alert=True)
        return

    data = await state.get_data()
    item_name = data.get("crash_item_name")
    item_value = data.get("crash_item_value")
    stake_label = CRASH_SLOT_ITEM.format(name=item_name, value=item_value) if item_name else CRASH_SLOT_EMPTY

    lines = [
        CRASH_HOME_HEADER,
        "",
        CRASH_HOME_DISCLAIMER,
        "",
        CRASH_HISTORY_LABEL.format(history=crash_runtime.history_label()),
        "",
        f"{CRASH_STAKE_LABEL}: {stake_label}",
    ]

    await callback.message.edit_text("\n".join(lines), reply_markup=crash_home_keyboard(bool(item_name)))
    await callback.answer()


@router.callback_query(CrashPickItemsCB.filter())
async def handle_pick_items(callback: CallbackQuery, callback_data: CrashPickItemsCB, state: FSMContext) -> None:
    if crash_runtime.get_active_round(callback.from_user.id):
        await callback.answer(CRASH_ALREADY_RUNNING, show_alert=True)
        return

    async with async_session() as session:
        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        items = await inventory_repo.list_all(session, user)

    if not items:
        await callback.answer(CRASH_NO_ITEMS_TEXT, show_alert=True)
        return

    await callback.message.edit_text(
        f"{CRASH_STAKE_LABEL}:", reply_markup=crash_items_keyboard(items, callback_data.page)
    )
    await callback.answer()


@router.callback_query(CrashPickItemCB.filter())
async def handle_pick_item(callback: CallbackQuery, callback_data: CrashPickItemCB, state: FSMContext) -> None:
    async with async_session() as session:
        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        item = await inventory_repo.get_by_id(session, callback_data.item_id)

    if item is None or item.user_id != user.id:
        await callback.answer(CRASH_ITEM_GONE, show_alert=True)
        return

    await state.update_data(crash_item_id=item.id, crash_item_name=item.item_name, crash_item_value=item.value)
    await open_crash_home(callback, state)


@router.callback_query(CrashStartCB.filter())
async def handle_start(callback: CallbackQuery, state: FSMContext) -> None:
    if crash_runtime.get_active_round(callback.from_user.id):
        await callback.answer(CRASH_ALREADY_RUNNING, show_alert=True)
        return

    data = await state.get_data()
    item_id = data.get("crash_item_id")
    item_name = data.get("crash_item_name")
    item_value = data.get("crash_item_value")
    if not item_id:
        await callback.answer(CRASH_NEED_ITEM_FIRST, show_alert=True)
        return

    async with async_session() as session:
        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        item = await inventory_repo.get_by_id(session, item_id)
        if item is None or item.user_id != user.id:
            await state.update_data(crash_item_id=None, crash_item_name=None, crash_item_value=None)
            await callback.answer(CRASH_ITEM_GONE, show_alert=True)
            return
        await inventory_repo.delete(session, item)

    await state.update_data(crash_item_id=None, crash_item_name=None, crash_item_value=None)

    stake_label = CRASH_SLOT_ITEM.format(name=item_name, value=item_value)
    await callback.message.edit_text(
        CRASH_IN_FLIGHT_TEXT.format(multiplier="1.00", stake=stake_label),
        reply_markup=crash_in_flight_keyboard(1.00),
    )
    await callback.answer()

    crash_runtime.start_round(
        bot=callback.bot,
        tg_id=callback.from_user.id,
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        item_name=item_name,
        item_value=item_value,
    )


@router.callback_query(CrashCashoutCB.filter())
async def handle_cashout(callback: CallbackQuery, state: FSMContext) -> None:
    if crash_runtime.get_active_round(callback.from_user.id) is None:
        await callback.answer(CRASH_NO_ACTIVE_ROUND, show_alert=True)
        return

    result = await crash_runtime.resolve_cashout(callback.bot, callback.from_user.id)
    if result is None:
        await callback.answer(CRASH_ALREADY_RESOLVED, show_alert=True)
        return

    round_, mult = result
    winnings = round(round_.item_value * mult)

    async with async_session() as session:
        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        await inventory_repo.add_items(session, user, "Краш", [(round_.item_name, winnings)])

    stake_label = CRASH_SLOT_ITEM.format(name=round_.item_name, value=round_.item_value)
    result_label = CRASH_SLOT_ITEM.format(name=round_.item_name, value=winnings)
    await callback.message.edit_text(
        CRASH_CASHOUT_SUCCESS.format(multiplier=mult, stake=stake_label, result=result_label)
    )
    await callback.answer()
