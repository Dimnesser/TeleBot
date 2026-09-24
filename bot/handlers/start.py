"""Обработка /start и регистрация пользователя."""
from __future__ import annotations

from pathlib import Path

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile, Message

from bot.database.engine import async_session
from bot.database.repo.users import get_or_create_user
from bot.keyboards.main_menu import welcome_keyboard
from bot.services import settings_service
from bot.services.partner_service import PartnerError, apply_partner_code
from bot.utils.texts import PARTNER_CODE_APPLIED, START_CAPTION

WELCOME_BANNER = Path(__file__).resolve().parents[1] / "assets" / "welcome.jpg"

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
        news_url = settings_service.channel_url(await settings_service.required_channel(session))
        support_url = await settings_service.get_setting(session, settings_service.SUPPORT_URL)

    await message.answer_photo(
        FSInputFile(WELCOME_BANNER),
        caption=START_CAPTION + partner_note,
        reply_markup=welcome_keyboard(news_url, support_url),
    )
