"""Квесты: прогресс по дневным/недельным заданиям и получение наград."""
from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.database.engine import async_session
from bot.database.models import Quest, QuestScope
from bot.database.repo import quests as quests_repo
from bot.database.repo.users import add_balance, get_or_create_user
from bot.keyboards.callbacks import QuestClaimCB, QuestsHomeCB
from bot.keyboards.quests import quests_keyboard
from bot.services.quest_service import format_timedelta, period_key, time_until_reset
from bot.utils.texts import (
    QUEST_ALREADY_CLAIMED_ALERT,
    QUEST_CLAIMED_ALERT,
    QUEST_CLAIMED_ROW,
    QUEST_NOT_READY_ALERT,
    QUEST_ROW,
    QUESTS_BALANCE_LINE,
    QUESTS_HEADER,
    QUESTS_SCOPE_DAILY,
    QUESTS_SCOPE_WEEKLY,
)

router = Router(name="quests")


@router.callback_query(QuestsHomeCB.filter())
async def open_quests_home(callback: CallbackQuery, state: FSMContext, *, answer: bool = True) -> None:
    async with async_session() as session:
        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        all_quests = await quests_repo.list_quests(session)

        rows_by_scope: dict[QuestScope, list[str]] = {QuestScope.DAILY: [], QuestScope.WEEKLY: []}
        claimable: list[Quest] = []
        for quest in all_quests:
            key = period_key(quest.scope)
            progress = await quests_repo.get_progress(session, user, quest, key)
            progress_count = progress.progress_count if progress else 0
            claimed = progress.claimed if progress else False

            if claimed:
                rows_by_scope[quest.scope].append(QUEST_CLAIMED_ROW.format(title=quest.title))
                continue

            reset_label = format_timedelta(time_until_reset(quest.scope))
            rows_by_scope[quest.scope].append(
                QUEST_ROW.format(
                    title=quest.title,
                    description=quest.description,
                    progress=progress_count,
                    target=quest.target_count,
                    reset=reset_label,
                    reward=quest.reward_tokens,
                )
            )
            if progress_count >= quest.target_count:
                claimable.append(quest)

        tokens = user.balance

    lines = [QUESTS_HEADER, "", QUESTS_BALANCE_LINE.format(tokens=tokens)]
    if rows_by_scope[QuestScope.DAILY]:
        lines.append("")
        lines.append(QUESTS_SCOPE_DAILY)
        for row in rows_by_scope[QuestScope.DAILY]:
            lines.append("")
            lines.append(row)
    if rows_by_scope[QuestScope.WEEKLY]:
        lines.append("")
        lines.append(QUESTS_SCOPE_WEEKLY)
        for row in rows_by_scope[QuestScope.WEEKLY]:
            lines.append("")
            lines.append(row)

    await callback.message.edit_text("\n".join(lines), reply_markup=quests_keyboard(claimable))
    if answer:
        await callback.answer()


@router.callback_query(QuestClaimCB.filter())
async def handle_claim(callback: CallbackQuery, callback_data: QuestClaimCB, state: FSMContext) -> None:
    reward = 0
    async with async_session() as session:
        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)

        quest = await session.get(Quest, callback_data.quest_id)
        if quest is None:
            await callback.answer("Квест не найден.", show_alert=True)
            return

        key = period_key(quest.scope)
        progress = await quests_repo.get_progress(session, user, quest, key)
        if progress is None or progress.progress_count < quest.target_count:
            await callback.answer(QUEST_NOT_READY_ALERT, show_alert=True)
            return
        if progress.claimed:
            await callback.answer(QUEST_ALREADY_CLAIMED_ALERT, show_alert=True)
            return

        progress.claimed = True
        await session.commit()
        await add_balance(session, user, quest.reward_tokens)
        reward = quest.reward_tokens

    await callback.answer(QUEST_CLAIMED_ALERT.format(reward=reward), show_alert=True)
    await open_quests_home(callback, state, answer=False)
