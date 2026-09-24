"""Обработка /start и регистрация пользователя."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.database.engine import async_session
from bot.database.repo.users import get_or_create_user
from bot.keyboards.main_menu import main_menu_keyboard
from bot.services.partner_service import PartnerError, apply_partner_code
from bot.utils.texts import PARTNER_CODE_APPLIED, WELCOME_TEXT

router = Router(name="start")


@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext) -> None:
    await state.clear()

    payload = message.text.split(maxsplit=1)[1] if message.text and " " in message.text else None
    referral_code = payload.removeprefix("ref_") if payload and payload.startswith("ref_") else None

    partner_note = ""
    async with async_session() as session:
        user = await get_or_create_user(
            session,
            tg_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            referral_code=referral_code,
        )
        # Любой другой payload — возможно, личный код партнёра (t.me/bot?start=CODE).
        if payload and referral_code is None:
            try:
                pc = await apply_partner_code(session, user, payload)
                partner_note = PARTNER_CODE_APPLIED.format(bonus=pc.deposit_bonus_percent, cases=pc.case_amount)
            except PartnerError:
                pass

    await message.answer(
        WELCOME_TEXT.format(name=message.from_user.first_name or "игрок", balance=user.balance) + partner_note,
        reply_markup=main_menu_keyboard(),
    )
