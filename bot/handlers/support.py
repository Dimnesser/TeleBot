"""Поддержка в боте: игрок пишет — админы получают, админ отвечает реплаем.

Вход: кнопка «🆘 Поддержка» под приветствием, /support, ссылка
t.me/<бот>?start=support (из Mini App) или просто любое сообщение боту.
"""
from __future__ import annotations

import time

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
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
    SUPPORT_CLOSED,
    SUPPORT_FAILED,
    SUPPORT_SENT,
    SUPPORT_SLOW_DOWN,
    SUPPORT_WELCOME,
)

router = Router(name="support")

MIN_INTERVAL = 1.5  # не чаще раза в полторы секунды — от флуда в админ-чат
_last_sent: dict[int, float] = {}


async def open_support(message: Message, state: FSMContext) -> None:
    await state.set_state(Support.chatting)
    await message.answer(SUPPORT_WELCOME, reply_markup=support_keyboard())


@router.message(Command("support"))
async def cmd_support(message: Message, state: FSMContext) -> None:
    await open_support(message, state)


@router.callback_query(SupportCB.filter(F.action == "open"))
async def cb_open(callback: CallbackQuery, state: FSMContext) -> None:
    await open_support(callback.message, state)
    await callback.answer()


@router.callback_query(SupportCB.filter(F.action == "faq"))
async def cb_faq(callback: CallbackQuery, callback_data: SupportCB) -> None:
    if not 0 <= callback_data.idx < len(FAQ_ENTRIES):
        await callback.answer()
        return
    question, answer = FAQ_ENTRIES[callback_data.idx]
    await callback.message.answer(f"❓ <b>{question}</b>\n{answer}\n\n<i>Не помогло — просто напиши сюда свой вопрос.</i>")
    await callback.answer()


@router.callback_query(SupportCB.filter(F.action == "close"))
async def cb_close(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.answer(SUPPORT_CLOSED)
    await callback.answer()


# --- ответ админа: реплай на обращение (в админ-чате или в личке админа)
@router.message(F.reply_to_message, ~F.text.startswith("/"))
async def admin_reply(message: Message, state: FSMContext) -> None:
    async with async_session() as session:
        user_tg_id = await support_service.user_for_reply(session, message)
    if user_tg_id is None:
        if message.chat.type == "private" and not is_admin(message.from_user.id):
            await player_message(message, state)  # игрок ответил реплаем на что-то в своём чате
        return
    try:
        await support_service.send_answer(message.bot, user_tg_id, message)
    except Exception:  # noqa: BLE001 — игрок мог заблокировать бота
        await message.reply("⚠️ Не доставлено: игрок заблокировал бота или удалил чат.")
        return
    await message.reply("✅ Ответ отправлен игроку")


# --- сообщение игрока: в режиме поддержки или просто любое сообщение боту
@router.message(F.chat.type == "private", StateFilter(Support.chatting, None), ~F.text.startswith("/"),
                ~F.successful_payment, ~F.web_app_data)
async def player_message(message: Message, state: FSMContext) -> None:
    if is_admin(message.from_user.id) and await state.get_state() is None:
        return  # у админов личка с ботом — рабочая, не шлём их сообщения самим себе
    now = time.monotonic()
    if now - _last_sent.get(message.from_user.id, 0) < MIN_INTERVAL:
        await message.answer(SUPPORT_SLOW_DOWN)
        return
    _last_sent[message.from_user.id] = now
    async with async_session() as session:
        user = await get_user_by_tg_id(session, message.from_user.id)
        delivered = await support_service.relay_to_admins(session, message.bot, message, user)
    await state.set_state(Support.chatting)
    await message.answer(SUPPORT_SENT if delivered else SUPPORT_FAILED)
