"""Батл: 1×1 против бота-соперника на демо-фишках (см. bot.services.battle_service)."""
from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.database.engine import async_session
from bot.database.models import CaseCategory
from bot.database.repo import cases as cases_repo
from bot.database.repo import inventory as inventory_repo
from bot.database.repo.users import add_game_tokens, get_or_create_user
from bot.keyboards.battle import battle_cases_keyboard, battle_result_keyboard
from bot.keyboards.callbacks import BattleHomeCB, BattleStartCB
from bot.services.battle_service import run_battle
from bot.utils.texts import (
    BATTLE_HOME_DISCLAIMER,
    BATTLE_HOME_HEADER,
    BATTLE_NO_CASES,
    BATTLE_NOT_ENOUGH_TOKENS,
    BATTLE_PICK_CASE_HINT,
    BATTLE_RESULT_BOT_LINE,
    BATTLE_RESULT_HEADER,
    BATTLE_RESULT_LOSS,
    BATTLE_RESULT_PLAYER_LINE,
    BATTLE_RESULT_TIE,
    BATTLE_RESULT_WIN,
)

router = Router(name="battle")


@router.callback_query(BattleHomeCB.filter())
async def open_battle_home(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session() as session:
        openable_cases = []
        for category in CaseCategory:
            cases = await cases_repo.list_cases(session, category)
            openable_cases.extend(c for c in cases if c.is_openable and c.price_tokens is not None)

    if openable_cases:
        lines = [BATTLE_HOME_HEADER, "", BATTLE_HOME_DISCLAIMER, "", BATTLE_PICK_CASE_HINT]
    else:
        lines = [BATTLE_HOME_HEADER, "", BATTLE_NO_CASES]

    await callback.message.edit_text("\n".join(lines), reply_markup=battle_cases_keyboard(openable_cases))
    await callback.answer()


@router.callback_query(BattleStartCB.filter())
async def handle_battle_start(callback: CallbackQuery, callback_data: BattleStartCB, state: FSMContext) -> None:
    async with async_session() as session:
        case = await cases_repo.get_case(session, callback_data.case_id)
        if case is None or not case.is_openable or case.price_tokens is None:
            await callback.answer("Этот кейс недоступен для батла.", show_alert=True)
            return

        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        cost = case.price_tokens
        if user.game_tokens < cost:
            await callback.answer(
                BATTLE_NOT_ENOUGH_TOKENS.format(cost=cost, balance=user.game_tokens), show_alert=True
            )
            return

        user.game_tokens -= cost
        await session.commit()

        items = await cases_repo.list_case_items(session, case.id)
        result = run_battle(items)

        if result.winner == "player":
            await inventory_repo.add_items(
                session,
                user,
                f"Батл: {case.name}",
                [
                    (result.player_item.name, result.player_item.value),
                    (result.bot_item.name, result.bot_item.value),
                ],
                case_id=case.id,
            )
        elif result.winner == "tie":
            await add_game_tokens(session, user, cost)

        case_name = case.name

    lines = [
        BATTLE_RESULT_HEADER.format(case_name=case_name),
        BATTLE_RESULT_PLAYER_LINE.format(name=result.player_item.name, value=result.player_item.value),
        BATTLE_RESULT_BOT_LINE.format(name=result.bot_item.name, value=result.bot_item.value),
        "",
    ]
    if result.winner == "player":
        lines.append(BATTLE_RESULT_WIN)
    elif result.winner == "bot":
        lines.append(BATTLE_RESULT_LOSS)
    else:
        lines.append(BATTLE_RESULT_TIE)

    await callback.message.edit_text("\n".join(lines), reply_markup=battle_result_keyboard())
    await callback.answer()
