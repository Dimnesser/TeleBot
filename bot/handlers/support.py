"""Поддержка: игрок пишет — админы получают, админ отвечает реплаем.

Работает в двух местах одним кодом (make_router):
  * отдельный бот поддержки (standalone=True, токен задаёт админ в Mini App,
    см. bot.support_bot): игрок пишет туда, обращения приходят админам в
    личку этого бота, ответ — реплаем там же;
  * основной бот (запасной вариант, пока отдельного нет): кнопка
    «🆘 Поддержка», /support, t.me/<бот>?start=support или любое сообщение.
"""
from __future__ import annotations

import time

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import is_admin
from bot.database.engine import async_session
from bot.database.repo.users import get_user_by_tg_id
from bot.keyboards.callbacks import SupportCB
from bot.keyboards.support import support_keyboard
from bot.services import support_service
from bot.states.support import Support
from bot.utils.texts import (
    FAQ_ENTRIES,
    SUPPORT_ADMIN_HELLO,
    SUPPORT_CLOSED,
    SUPPORT_FAILED,
    SUPPORT_SENT,
    SUPPORT_SLOW_DOWN,
    SUPPORT_WELCOME,
)

MIN_INTERVAL = 1.5  # не чаще раза в полторы секунды — от флуда админам
_last_sent: dict[int, float] = {}


async def open_support(message: Message, state: FSMContext) -> None:
    await state.set_state(Support.chatting)
    await message.answer(SUPPORT_WELCOME, reply_markup=support_keyboard())


async def cb_open(callback: CallbackQuery, state: FSMContext) -> None:
    await open_support(callback.message, state)
    await callback.answer()


async def cb_faq(callback: CallbackQuery, callback_data: SupportCB) -> None:
    if not 0 <= callback_data.idx < len(FAQ_ENTRIES):
        await callback.answer()
        return
    question, answer = FAQ_ENTRIES[callback_data.idx]
    await callback.message.answer(f"❓ <b>{question}</b>\n{answer}\n\n<i>Не помогло — просто напиши сюда свой вопрос.</i>")
    await callback.answer()


async def cb_close(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer(SUPPORT_CLOSED)
    await callback.answer()


async def admin_reply(message: Message, state: FSMContext, standalone: bool = False) -> None:
    """Реплай админа на обращение → ответ игроку. Иначе — обычное сообщение."""
    async with async_session() as session:
        user_tg_id = await support_service.user_for_reply(session, message)
    if user_tg_id is None:
        if message.chat.type == "private" and not is_admin(message.from_user.id):
            await player_message(message, state, standalone)  # игрок ответил реплаем в своём чате
        return
    try:
        await support_service.send_answer(message.bot, user_tg_id, message)
    except Exception:  # noqa: BLE001 — игрок мог заблокировать бота
        await message.reply("⚠️ Не доставлено: игрок заблокировал бота или удалил чат.")
        return
    await message.reply("✅ Ответ отправлен игроку")


async def player_message(message: Message, state: FSMContext, standalone: bool = False) -> None:
    if is_admin(message.from_user.id) and (standalone or await state.get_state() is None):
        return  # сообщения админов самим себе не пересылаем
    now = time.monotonic()
    if now - _last_sent.get(message.from_user.id, 0) < MIN_INTERVAL:
        await message.answer(SUPPORT_SLOW_DOWN)
        return
    _last_sent[message.from_user.id] = now
    async with async_session() as session:
        user = await get_user_by_tg_id(session, message.from_user.id)
        delivered = await support_service.relay_to_admins(session, message.bot, message, user, standalone=standalone)
    await state.set_state(Support.chatting)
    await message.answer(SUPPORT_SENT if delivered else SUPPORT_FAILED)


def make_router(*, standalone: bool) -> Router:
    router = Router(name="support_bot" if standalone else "support")
    if standalone:
        @router.message(CommandStart())
        async def start(message: Message, state: FSMContext) -> None:
            if is_admin(message.from_user.id):
                await message.answer(SUPPORT_ADMIN_HELLO)
                return
            await open_support(message, state)

    router.message(Command("support"))(open_support)
    router.callback_query(SupportCB.filter(F.action == "open"))(cb_open)
    router.callback_query(SupportCB.filter(F.action == "faq"))(cb_faq)
    router.callback_query(SupportCB.filter(F.action == "close"))(cb_close)

    @router.message(F.reply_to_message, ~F.text.startswith("/"))
    async def on_reply(message: Message, state: FSMContext) -> None:
        await admin_reply(message, state, standalone)

    # в боте поддержки любое сообщение — обращение; в основном — в режиме
    # поддержки или без другого активного сценария
    states = (StateFilter("*"),) if standalone else (StateFilter(Support.chatting, None),)

    @router.message(F.chat.type == "private", *states, ~F.text.startswith("/"), ~F.successful_payment)
    async def on_message(message: Message, state: FSMContext) -> None:
        await player_message(message, state, standalone)

    return router


router = make_router(standalone=False)
