"""Бонусы: реферальная программа и стейкинг реального баланса B."""
from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.data.referral_tiers import next_tier_for_count, tier_for_count
from bot.database.engine import async_session
from bot.database.models import StakeStatus
from bot.database.repo import staking as staking_repo
from bot.database.repo.users import count_referrals, get_or_create_user
from bot.keyboards.bonuses import (
    referral_keyboard,
    staking_active_keyboard,
    staking_confirm_keyboard,
    staking_tiers_keyboard,
)
from bot.keyboards.callbacks import (
    BonusesHomeCB,
    BonusesTabCB,
    StakeCancelCB,
    StakeClaimCB,
    StakeConfirmCB,
    StakeStartCB,
)
from bot.services.staking_service import MIN_STAKE_AMOUNT, is_matured, payout_amount, tier_by_term
from bot.states.staking import StakingStates
from bot.utils.texts import (
    REFERRAL_CODE_LINE,
    REFERRAL_HEADER,
    REFERRAL_LINK_LINE,
    REFERRAL_MAX_TIER_LINE,
    REFERRAL_NEXT_TIER_LINE,
    REFERRAL_STATS,
    REFERRAL_TIER_LINE,
    STAKING_ACTIVE_INFO,
    STAKING_ALREADY_ACTIVE,
    STAKING_AMOUNT_INVALID,
    STAKING_ASK_AMOUNT,
    STAKING_CLAIMED_TEXT,
    STAKING_CONFIRM_TEXT,
    STAKING_DESCRIPTION,
    STAKING_HEADER,
    STAKING_MY_STATS,
    STAKING_NOT_MATURED_ALERT,
    STAKING_NO_ACTIVE,
    STAKING_STARTED_TEXT,
    STAKING_TIER_LABEL,
)

router = Router(name="bonuses")


@router.callback_query(BonusesHomeCB.filter())
async def open_bonuses_home(callback: CallbackQuery, state: FSMContext) -> None:
    await open_referral_tab(callback, state)


@router.callback_query(BonusesTabCB.filter())
async def handle_tab(callback: CallbackQuery, callback_data: BonusesTabCB, state: FSMContext) -> None:
    if callback_data.tab == "staking":
        await open_staking_tab(callback, state)
    else:
        await open_referral_tab(callback, state)


async def open_referral_tab(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session() as session:
        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        referral_count = await count_referrals(session, user)

    tier = tier_for_count(referral_count)
    next_tier = next_tier_for_count(referral_count)

    me = await callback.bot.get_me()
    link = f"https://t.me/{me.username}?start=ref_{user.referral_code}"

    lines = [
        REFERRAL_HEADER,
        "",
        REFERRAL_CODE_LINE.format(code=user.referral_code),
        REFERRAL_LINK_LINE.format(link=link),
        "",
        REFERRAL_TIER_LINE.format(tier=tier.name, commission=tier.commission_percent),
    ]
    if next_tier:
        lines.append(REFERRAL_NEXT_TIER_LINE.format(next_tier=next_tier.name, remaining=next_tier.min_referrals - referral_count))
    else:
        lines.append(REFERRAL_MAX_TIER_LINE)
    lines.append("")
    lines.append(
        REFERRAL_STATS.format(count=referral_count, earned=user.referral_earned_total, commission=tier.commission_percent)
    )

    await callback.message.edit_text("\n".join(lines), reply_markup=referral_keyboard())
    await callback.answer()


async def open_staking_tab(callback: CallbackQuery, state: FSMContext) -> None:
    async with async_session() as session:
        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        active = await staking_repo.get_active_position(session, user)
        completed = await staking_repo.list_completed(session, user)
        all_positions = await staking_repo.list_all_for_user(session, user)

    total_frozen = sum(p.amount for p in all_positions)
    total_bonus = sum(payout_amount(p) - p.amount for p in completed)
    stats_text = STAKING_MY_STATS.format(
        total_frozen=total_frozen, total_bonus=total_bonus, completed_count=len(completed)
    )

    if active is None:
        lines = [
            STAKING_HEADER,
            "",
            STAKING_DESCRIPTION.format(min_amount=MIN_STAKE_AMOUNT),
            "",
            stats_text,
        ]
        await callback.message.edit_text("\n".join(lines), reply_markup=staking_tiers_keyboard())
    else:
        matured = is_matured(active)
        lines = [
            STAKING_HEADER,
            "",
            STAKING_ACTIVE_INFO.format(
                amount=active.amount,
                days=active.term_days,
                bonus=active.bonus_percent,
                matures_at=active.matures_at.strftime("%d.%m.%Y %H:%M UTC"),
                payout=payout_amount(active),
            ),
            "",
            stats_text,
        ]
        await callback.message.edit_text(
            "\n".join(lines), reply_markup=staking_active_keyboard(matured, active.id)
        )
    await callback.answer()


@router.callback_query(StakeStartCB.filter())
async def handle_stake_start(callback: CallbackQuery, callback_data: StakeStartCB, state: FSMContext) -> None:
    tier = tier_by_term(callback_data.term_days)
    if tier is None:
        await callback.answer("Такого тарифа нет.", show_alert=True)
        return

    async with async_session() as session:
        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        active = await staking_repo.get_active_position(session, user)
        if active is not None:
            await callback.answer(STAKING_ALREADY_ACTIVE, show_alert=True)
            return
        balance = user.balance

    if balance < MIN_STAKE_AMOUNT:
        await callback.answer(
            STAKING_AMOUNT_INVALID.format(min_amount=MIN_STAKE_AMOUNT, balance=balance), show_alert=True
        )
        return

    await state.update_data(stake_term_days=tier.term_days, stake_bonus_percent=tier.bonus_percent)
    await state.set_state(StakingStates.waiting_amount)
    await callback.message.edit_text(STAKING_ASK_AMOUNT.format(min_amount=MIN_STAKE_AMOUNT, balance=balance))
    await callback.answer()


@router.message(StakingStates.waiting_amount)
async def handle_amount_input(message: Message, state: FSMContext) -> None:
    async with async_session() as session:
        user = await get_or_create_user(session, message.from_user.id, message.from_user.username, message.from_user.first_name)
        balance = user.balance

    raw = (message.text or "").strip()
    if not raw.isdigit() or not (MIN_STAKE_AMOUNT <= int(raw) <= balance):
        await message.answer(STAKING_AMOUNT_INVALID.format(min_amount=MIN_STAKE_AMOUNT, balance=balance))
        return

    amount = int(raw)
    data = await state.get_data()
    term_days = data["stake_term_days"]
    bonus_percent = data["stake_bonus_percent"]
    payout = amount + round(amount * bonus_percent / 100)

    await state.update_data(stake_amount=amount)
    await message.answer(
        STAKING_CONFIRM_TEXT.format(amount=amount, days=term_days, bonus=bonus_percent, payout=payout),
        reply_markup=staking_confirm_keyboard(),
    )


@router.callback_query(StakeCancelCB.filter())
async def handle_stake_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(stake_term_days=None, stake_bonus_percent=None, stake_amount=None)
    await state.set_state(None)
    await open_staking_tab(callback, state)


@router.callback_query(StakeConfirmCB.filter())
async def handle_stake_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    term_days = data.get("stake_term_days")
    bonus_percent = data.get("stake_bonus_percent")
    amount = data.get("stake_amount")

    if not term_days or not amount:
        await callback.answer("Заявка устарела, начните заново.", show_alert=True)
        return

    async with async_session() as session:
        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)

        active = await staking_repo.get_active_position(session, user)
        if active is not None:
            await callback.answer(STAKING_ALREADY_ACTIVE, show_alert=True)
            return
        if user.balance < amount:
            await callback.answer(STAKING_AMOUNT_INVALID.format(min_amount=MIN_STAKE_AMOUNT, balance=user.balance), show_alert=True)
            return

        user.balance -= amount
        await session.commit()
        position = await staking_repo.create_position(session, user, amount, term_days, bonus_percent)

    await state.update_data(stake_term_days=None, stake_bonus_percent=None, stake_amount=None)
    await state.set_state(None)

    await callback.message.edit_text(
        STAKING_STARTED_TEXT.format(
            amount=amount, days=term_days, matures_at=position.matures_at.strftime("%d.%m.%Y %H:%M UTC")
        )
    )
    await callback.answer()


@router.callback_query(StakeClaimCB.filter())
async def handle_stake_claim(callback: CallbackQuery, callback_data: StakeClaimCB, state: FSMContext) -> None:
    async with async_session() as session:
        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        position = await staking_repo.get_position(session, callback_data.stake_id)

        if position is None or position.user_id != user.id or position.status != StakeStatus.ACTIVE:
            await callback.answer(STAKING_NO_ACTIVE, show_alert=True)
            return
        if not is_matured(position):
            await callback.answer(
                STAKING_NOT_MATURED_ALERT.format(matures_at=position.matures_at.strftime("%d.%m.%Y %H:%M UTC")),
                show_alert=True,
            )
            return

        payout = payout_amount(position)
        bonus = payout - position.amount
        user.balance += payout
        position.status = StakeStatus.COMPLETED
        await session.commit()

    await callback.message.edit_text(STAKING_CLAIMED_TEXT.format(payout=payout, amount=position.amount, bonus=bonus))
    await callback.answer()
