"""FAQ: статичный список вопрос-ответ.

[НЕИЗВЕСТНО] Интерфейс раздела ни разу не был на скриншотах — сделано по
собственному усмотрению, см. bot.utils.texts.FAQ_ENTRIES.
"""
from __future__ import annotations

from aiogram import Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.keyboards.callbacks import FaqHomeCB
from bot.keyboards.faq import faq_keyboard
from bot.utils.texts import FAQ_ENTRIES, FAQ_HEADER

router = Router(name="faq")


@router.callback_query(FaqHomeCB.filter())
async def open_faq_home(callback: CallbackQuery, state: FSMContext) -> None:
    lines = [FAQ_HEADER]
    for question, answer in FAQ_ENTRIES:
        lines.append("")
        lines.append(f"<b>{question}</b>\n{answer}")

    await callback.message.edit_text("\n".join(lines), reply_markup=faq_keyboard())
    await callback.answer()
