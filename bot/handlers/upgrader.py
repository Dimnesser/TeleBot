"""Апгрейдер: риск предметом из инвентаря ради более дорогого предмета.

Работает поверх того же инвентаря, что и кейсы (bot.database.models.InventoryItem):
ставка — брейнрот, а не баланс B.
"""
from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.database.engine import async_session
from bot.database.repo import inventory as inventory_repo
from bot.services import drops
from bot.database.repo.known_items import list_known_items
from bot.database.repo.users import get_or_create_user
from bot.keyboards.callbacks import (
    UpgraderConfirmCB,
    UpgraderHomeCB,
    UpgraderMyItemsCB,
    UpgraderPickContributionCB,
    UpgraderPickTargetCB,
    UpgraderPresetCB,
    UpgraderResetCB,
    UpgraderTargetsCB,
)
from bot.keyboards.upgrader import my_items_keyboard, targets_keyboard, upgrader_home_keyboard
from bot.services import quest_service
from bot.services.upgrader_service import (
    chance_percent,
    find_nearest_target,
    lucky_chance,
    roll_success,
    target_value_for_chance,
    target_value_for_multiplier,
)
from bot.utils.texts import (
    UPGRADER_CHANCE_LINE,
    UPGRADER_CONFIRM_ITEM_GONE,
    UPGRADER_CONFIRM_NEED_BOTH,
    UPGRADER_CONTRIBUTION_LABEL,
    UPGRADER_HOME_DISCLAIMER,
    UPGRADER_HOME_HEADER,
    UPGRADER_MY_ITEMS_HEADER,
    UPGRADER_NEED_CONTRIBUTION_FIRST,
    UPGRADER_NO_ITEMS_TEXT,
    UPGRADER_NO_TARGET_FOUND,
    UPGRADER_RESULT_CHANCE_LINE,
    UPGRADER_RESULT_FAIL,
    UPGRADER_RESULT_SUCCESS,
    UPGRADER_SLOT_EMPTY,
    UPGRADER_SLOT_ITEM,
    UPGRADER_TARGET_LABEL,
    UPGRADER_TARGETS_HEADER,
)

router = Router(name="upgrader")


def _chance_bar(chance: int) -> str:
    filled = round(chance / 10)
    return "🟩" * filled + "⬛" * (10 - filled)


@router.callback_query(UpgraderHomeCB.filter())
async def open_upgrader_home(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    contribution_id = data.get("upgrader_contribution_id")
    contribution_name = data.get("upgrader_contribution_name")
    contribution_value = data.get("upgrader_contribution_value")
    target_name = data.get("upgrader_target_name")
    target_value = data.get("upgrader_target_value")

    contribution_label = (
        UPGRADER_SLOT_ITEM.format(name=contribution_name, value=contribution_value)
        if contribution_id
        else UPGRADER_SLOT_EMPTY
    )
    target_label = (
        UPGRADER_SLOT_ITEM.format(name=target_name, value=target_value) if target_name else UPGRADER_SLOT_EMPTY
    )

    lines = [
        UPGRADER_HOME_HEADER,
        "",
        UPGRADER_HOME_DISCLAIMER,
        "",
        f"{UPGRADER_CONTRIBUTION_LABEL}: {contribution_label}",
        f"{UPGRADER_TARGET_LABEL}: {target_label}",
    ]
    if contribution_id and target_name:
        chance = chance_percent(contribution_value, target_value)
        lines.append("")
        lines.append(_chance_bar(chance))
        lines.append(UPGRADER_CHANCE_LINE.format(chance=chance))

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=upgrader_home_keyboard(
            bool(contribution_id), bool(target_name), UPGRADER_CONTRIBUTION_LABEL, UPGRADER_TARGET_LABEL
        ),
    )
    await callback.answer()


@router.callback_query(UpgraderMyItemsCB.filter())
async def handle_my_items(callback: CallbackQuery, callback_data: UpgraderMyItemsCB, state: FSMContext) -> None:
    async with async_session() as session:
        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        items = await inventory_repo.list_all(session, user)

    if not items:
        await callback.answer(UPGRADER_NO_ITEMS_TEXT, show_alert=True)
        return

    await callback.message.edit_text(
        UPGRADER_MY_ITEMS_HEADER, reply_markup=my_items_keyboard(items, callback_data.page)
    )
    await callback.answer()


@router.callback_query(UpgraderPickContributionCB.filter())
async def handle_pick_contribution(
    callback: CallbackQuery, callback_data: UpgraderPickContributionCB, state: FSMContext
) -> None:
    async with async_session() as session:
        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        item = await inventory_repo.get_by_id(session, callback_data.item_id)

    if item is None or item.user_id != user.id:
        await callback.answer(UPGRADER_CONFIRM_ITEM_GONE, show_alert=True)
        return

    await state.update_data(
        upgrader_contribution_id=item.id,
        upgrader_contribution_name=item.item_name,
        upgrader_contribution_value=item.value,
    )
    await open_upgrader_home(callback, state)


@router.callback_query(UpgraderTargetsCB.filter())
async def handle_targets(callback: CallbackQuery, callback_data: UpgraderTargetsCB, state: FSMContext) -> None:
    data = await state.get_data()
    contribution_value = data.get("upgrader_contribution_value")
    contribution_name = data.get("upgrader_contribution_name")
    if not contribution_value:
        await callback.answer(UPGRADER_NEED_CONTRIBUTION_FIRST, show_alert=True)
        return

    async with async_session() as session:
        known_items = await list_known_items(session)

    # апгрейдер увеличивает ценность, поэтому целью может быть только то,
    # что дороже вклада — иначе это не «апгрейд», а произвольный обмен
    eligible = [item for item in known_items if item.value > contribution_value and item.name != contribution_name]

    await state.update_data(upgrader_known_items=[[item.name, item.value] for item in eligible])
    await callback.message.edit_text(
        UPGRADER_TARGETS_HEADER, reply_markup=targets_keyboard(eligible, callback_data.page)
    )
    await callback.answer()


@router.callback_query(UpgraderPickTargetCB.filter())
async def handle_pick_target(callback: CallbackQuery, callback_data: UpgraderPickTargetCB, state: FSMContext) -> None:
    data = await state.get_data()
    snapshot = data.get("upgrader_known_items", [])
    if callback_data.index >= len(snapshot):
        await callback.answer(UPGRADER_NO_TARGET_FOUND, show_alert=True)
        return

    name, value = snapshot[callback_data.index]
    await state.update_data(upgrader_target_name=name, upgrader_target_value=value)
    await open_upgrader_home(callback, state)


@router.callback_query(UpgraderPresetCB.filter())
async def handle_preset(callback: CallbackQuery, callback_data: UpgraderPresetCB, state: FSMContext) -> None:
    data = await state.get_data()
    contribution_value = data.get("upgrader_contribution_value")
    contribution_name = data.get("upgrader_contribution_name")
    if not contribution_value:
        await callback.answer(UPGRADER_NEED_CONTRIBUTION_FIRST, show_alert=True)
        return

    if callback_data.kind == "mult":
        target_value = target_value_for_multiplier(contribution_value, callback_data.value)
    else:
        target_value = target_value_for_chance(contribution_value, callback_data.value)

    async with async_session() as session:
        known_items = await list_known_items(session)

    nearest = find_nearest_target(known_items, target_value, exclude_name=contribution_name)
    if nearest is None:
        await callback.answer(UPGRADER_NO_TARGET_FOUND, show_alert=True)
        return

    await state.update_data(upgrader_target_name=nearest.name, upgrader_target_value=nearest.value)
    await open_upgrader_home(callback, state)


@router.callback_query(UpgraderResetCB.filter())
async def handle_reset(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(
        upgrader_contribution_id=None,
        upgrader_contribution_name=None,
        upgrader_contribution_value=None,
        upgrader_target_name=None,
        upgrader_target_value=None,
    )
    await open_upgrader_home(callback, state)


@router.callback_query(UpgraderConfirmCB.filter())
async def handle_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    contribution_id = data.get("upgrader_contribution_id")
    contribution_name = data.get("upgrader_contribution_name")
    contribution_value = data.get("upgrader_contribution_value")
    target_name = data.get("upgrader_target_name")
    target_value = data.get("upgrader_target_value")

    if not contribution_id or not target_name:
        await callback.answer(UPGRADER_CONFIRM_NEED_BOTH, show_alert=True)
        return

    async with async_session() as session:
        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        item = await inventory_repo.get_by_id(session, contribution_id)
        if item is None or item.user_id != user.id:
            await state.update_data(
                upgrader_contribution_id=None, upgrader_contribution_name=None, upgrader_contribution_value=None
            )
            await callback.answer(UPGRADER_CONFIRM_ITEM_GONE, show_alert=True)
            return

        chance = chance_percent(contribution_value, target_value)
        success = roll_success(lucky_chance(chance, user.luck))

        await inventory_repo.delete(session, item)
        if success:
            await drops.grant(session, user, "Апгрейдер", [(target_name, target_value)])
        await quest_service.record_progress(session, user, "upgrader_spin")

    await state.update_data(
        upgrader_contribution_id=None,
        upgrader_contribution_name=None,
        upgrader_contribution_value=None,
        upgrader_target_name=None,
        upgrader_target_value=None,
    )

    contribution_label = UPGRADER_SLOT_ITEM.format(name=contribution_name, value=contribution_value)
    target_label = UPGRADER_SLOT_ITEM.format(name=target_name, value=target_value)
    if success:
        result_text = UPGRADER_RESULT_SUCCESS.format(contribution=contribution_label, target=target_label)
    else:
        result_text = UPGRADER_RESULT_FAIL.format(contribution=contribution_label)
    result_text += "\n" + UPGRADER_RESULT_CHANCE_LINE.format(chance=chance)

    await callback.message.edit_text(
        result_text,
        reply_markup=upgrader_home_keyboard(False, False, UPGRADER_CONTRIBUTION_LABEL, UPGRADER_TARGET_LABEL),
    )
    await callback.answer()
