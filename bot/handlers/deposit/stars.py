"""Пополнение баланса через Telegram Stars."""
from __future__ import annotations

import secrets
from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from sqlalchemy import select

from bot.config import config
from bot.database.engine import async_session
from bot.database.models import StarsDeposit, User
from bot.database.repo.users import get_or_create_user
from bot.keyboards.callbacks import StarsCreateInvoiceCB, StarsSkipPromoCB
from bot.keyboards.deposit import stars_amount_keyboard, stars_invoice_keyboard, stars_promo_keyboard
from bot.services.referral_service import credit_referral_commission
from bot.states.deposit import DepositStars
from bot.utils.texts import (
    STARS_AMOUNT_INVALID,
    STARS_HEADER,
    STARS_PAYMENT_SUCCESS,
    STARS_PROMO_PROMPT,
    STARS_READY_TEXT,
)

router = Router(name="deposit_stars")


async def open_stars_tab(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(DepositStars.waiting_amount)
    await callback.message.edit_text(STARS_HEADER, reply_markup=stars_amount_keyboard())
    await callback.answer()


@router.message(DepositStars.waiting_amount)
async def handle_amount(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").strip()
    if not raw.isdigit() or not (config.min_stars_amount <= int(raw) <= config.max_stars_amount):
        await message.answer(STARS_AMOUNT_INVALID.format(min=config.min_stars_amount, max=config.max_stars_amount))
        return

    await state.update_data(stars_amount=int(raw))
    await state.set_state(DepositStars.waiting_promo)
    await message.answer(STARS_PROMO_PROMPT, reply_markup=stars_promo_keyboard())


@router.callback_query(StarsSkipPromoCB.filter(), DepositStars.waiting_promo)
async def handle_promo_skip(callback: CallbackQuery, state: FSMContext) -> None:
    await _show_summary(callback.message, state, promo=None)
    await callback.answer()


@router.message(DepositStars.waiting_promo)
async def handle_promo_input(message: Message, state: FSMContext) -> None:
    await _show_summary(message, state, promo=(message.text or "").strip() or None)


async def _show_summary(message: Message, state: FSMContext, promo: str | None) -> None:
    data = await state.get_data()
    amount = data["stars_amount"]
    await state.update_data(promo=promo)
    text = STARS_READY_TEXT.format(amount=amount, promo=promo or "—", credited=amount * config.stars_to_balance_rate)
    await message.answer(text, reply_markup=stars_invoice_keyboard())


@router.callback_query(StarsCreateInvoiceCB.filter())
async def handle_create_invoice(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    amount = data.get("stars_amount")
    if not amount:
        await callback.answer("Сначала укажи количество Stars.", show_alert=True)
        return

    payload = f"stars_dep:{callback.from_user.id}:{secrets.token_hex(6)}"

    async with async_session() as session:
        user = await get_or_create_user(
            session, callback.from_user.id, callback.from_user.username, callback.from_user.first_name
        )
        session.add(
            StarsDeposit(
                user_id=user.id,
                stars_amount=amount,
                promo_code=data.get("promo"),
                payload=payload,
                status="pending",
            )
        )
        await session.commit()

    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Пополнение баланса BrainCore",
        description=f"Начисление {amount * config.stars_to_balance_rate} B на внутренний баланс",
        payload=payload,
        currency="XTR",
        prices=[LabeledPrice(label="Пополнение баланса", amount=amount)],
    )
    await callback.answer()


@router.pre_checkout_query()
async def handle_pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def handle_successful_payment(message: Message, state: FSMContext) -> None:
    payment = message.successful_payment

    async with async_session() as session:
        result = await session.execute(select(StarsDeposit).where(StarsDeposit.payload == payment.invoice_payload))
        deposit = result.scalar_one_or_none()
        if deposit is None or deposit.status == "paid":
            return

        deposit.status = "paid"
        deposit.telegram_charge_id = payment.telegram_payment_charge_id
        deposit.paid_at = datetime.utcnow()

        user = await session.get(User, deposit.user_id)
        credited = deposit.stars_amount * config.stars_to_balance_rate
        user.balance += credited
        await session.commit()
        await credit_referral_commission(session, user, credited)
        balance = user.balance

    await state.clear()
    await message.answer(STARS_PAYMENT_SUCCESS.format(credited=credited, balance=balance))
