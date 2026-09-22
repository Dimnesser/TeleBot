"""Дайсы: бросок 4 кубиков против выбранного цвета, ставка — предмет из инвентаря."""
from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.config import config
from bot.database.engine import async_session
from bot.database.repo import inventory as inventory_repo
from bot.database.repo.users import get_or_create_user
from bot.keyboards.callbacks import (
    DiceHomeCB,
    DicePickColorCB,
    DicePickItemCB,
    DicePickItemsCB,
    DiceResetCB,
    DiceRollCB,
)
from bot.keyboards.dice import dice_home_keyboard, dice_items_keyboard
from bot.services.dice_service import MATCH_PAYOUT_TABLE, resolve_roll
from bot.utils.texts import (
    DICE_COLOR_LABEL,
    DICE_HOME_DISCLAIMER,
    DICE_HOME_HEADER,
    DICE_ITEM_GONE,
    DICE_NEED_BOTH,
    DICE_NO_ITEMS_TEXT,
    DICE_RESULT_BONUS,
    DICE_RESULT_HEADER,
    DICE_RESULT_LOSS,
    DICE_RESULT_MATCHES,
    DICE_RESULT_WIN,
    DICE_RULES_BONUS_ROW,
    DICE_RULES_HEADER,
    DICE_RULES_ROW_LOSS,
    DICE_RULES_ROW_WIN,
    DICE_SLOT_EMPTY,
    DICE_SLOT_ITEM,
    DICE_STAKE_LABEL,
)

router = Router(name="dice")


def _fmt_mult(value: float) -> str:
    return str(int(value)) if value == int(value) else str(value)


def _rules_text() -> str:
    lines = [DICE_RULES_HEADER]
    for count in sorted(MATCH_PAYOUT_TABLE):
        multiplier = MATCH_PAYOUT_TABLE[count]
        if multiplier is None:
            lines.append(DICE_RULES_ROW_LOSS.format(count=count))
        else:
            lines.append(DICE_RULES_ROW_WIN.format(count=count, multiplier=_fmt_mult(multiplier)))
    lines.append(DICE_RULES_BONUS_ROW.format(multiplier=_fmt_mult(config.dice_bonus_multiplier)))
    return "\n".join(lines)


@router.callback_query(DiceHomeCB.filter())
async def open_dice_home(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    item_name = data.get("dice_item_name")
    item_value = data.get("dice_item_value")
    color = data.get("dice_color")

    stake_label = DICE_SLOT_ITEM.format(name=item_name, value=item_value) if item_name else DICE_SLOT_EMPTY
    color_label = color or DICE_SLOT_EMPTY

    lines = [
        DICE_HOME_HEADER,
        "",
        DICE_HOME_DISCLAIMER,
        "",
        f"{DICE_STAKE_LABEL}: {stake_label}",
        f"{DICE_COLOR_LABEL}: {color_label}",
        "",
        _rules_text(),
    ]

    await callback.message.edit_text("\n".join(lines), reply_markup=dice_home_keyboard(bool(item_name), color))
    await callback.answer()


@router.callback_query(DicePickItemsCB.filter())
async def handle_pick_items(callback: CallbackQuery, callback_data: DicePickItemsCB, state: FSMContext) -> None:
    async with async_session() as session:
        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        items = await inventory_repo.list_all(session, user)

    if not items:
        await callback.answer(DICE_NO_ITEMS_TEXT, show_alert=True)
        return

    await callback.message.edit_text(
        f"{DICE_STAKE_LABEL}:", reply_markup=dice_items_keyboard(items, callback_data.page)
    )
    await callback.answer()


@router.callback_query(DicePickItemCB.filter())
async def handle_pick_item(callback: CallbackQuery, callback_data: DicePickItemCB, state: FSMContext) -> None:
    async with async_session() as session:
        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        item = await inventory_repo.get_by_id(session, callback_data.item_id)

    if item is None or item.user_id != user.id:
        await callback.answer(DICE_ITEM_GONE, show_alert=True)
        return

    await state.update_data(dice_item_id=item.id, dice_item_name=item.item_name, dice_item_value=item.value)
    await open_dice_home(callback, state)


@router.callback_query(DicePickColorCB.filter())
async def handle_pick_color(callback: CallbackQuery, callback_data: DicePickColorCB, state: FSMContext) -> None:
    await state.update_data(dice_color=callback_data.color)
    await open_dice_home(callback, state)


@router.callback_query(DiceResetCB.filter())
async def handle_reset(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(dice_item_id=None, dice_item_name=None, dice_item_value=None, dice_color=None)
    await open_dice_home(callback, state)


@router.callback_query(DiceRollCB.filter())
async def handle_roll(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    item_id = data.get("dice_item_id")
    item_name = data.get("dice_item_name")
    item_value = data.get("dice_item_value")
    color = data.get("dice_color")

    if not item_id or not color:
        await callback.answer(DICE_NEED_BOTH, show_alert=True)
        return

    async with async_session() as session:
        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        item = await inventory_repo.get_by_id(session, item_id)
        if item is None or item.user_id != user.id:
            await state.update_data(dice_item_id=None, dice_item_name=None, dice_item_value=None)
            await callback.answer(DICE_ITEM_GONE, show_alert=True)
            return

        result = resolve_roll(color)

        await inventory_repo.delete(session, item)
        winnings = None
        if result.is_win:
            winnings = round(item_value * result.multiplier)
            await inventory_repo.add_items(session, user, "Дайсы", [(item_name, winnings)])

    stake_label = DICE_SLOT_ITEM.format(name=item_name, value=item_value)
    lines = [
        DICE_RESULT_HEADER.format(dice=" ".join(result.dice)),
        DICE_RESULT_MATCHES.format(color=color, count=result.match_count),
    ]
    if result.bonus:
        lines.append(DICE_RESULT_BONUS)
    lines.append("")
    if result.is_win:
        result_label = DICE_SLOT_ITEM.format(name=item_name, value=winnings)
        lines.append(
            DICE_RESULT_WIN.format(multiplier=_fmt_mult(result.multiplier), stake=stake_label, result=result_label)
        )
    else:
        lines.append(DICE_RESULT_LOSS.format(stake=stake_label))

    await state.update_data(dice_item_id=None, dice_item_name=None, dice_item_value=None, dice_color=None)
    await callback.message.edit_text("\n".join(lines), reply_markup=dice_home_keyboard(False, None))
    await callback.answer()
