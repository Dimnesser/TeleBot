"""Поддержка прямо в боте.

Игрок пишет боту (текст, фото, скрин, видео…) — бот пересылает это админам
под шапкой «от кого». Отдельный бот поддержки (токен в админке) шлёт каждому
из ADMIN_IDS в личку; основной бот — в админ-чат (ADMIN_CHAT_ID), если он есть. Админ отвечает реплаем на шапку или на само сообщение —
бот отправляет ответ игроку. Связь «сообщение у админов → игрок» хранится в
SupportMessage, поэтому переживает перезапуск бота.
"""
from __future__ import annotations

import html
import logging

from aiogram import Bot
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import all_admin_ids, config
from bot.database.models import SupportMessage, User

logger = logging.getLogger(__name__)


def admin_targets(*, standalone: bool = False) -> list[int]:
    if standalone or not config.admin_chat_id:
        return all_admin_ids()
    return [config.admin_chat_id]


async def relay_to_admins(
    session: AsyncSession, bot: Bot, message: Message, user: User | None, *, standalone: bool = False,
) -> int:
    """Переслать сообщение игрока админам. Возвращает, скольким доставлено."""
    who = message.from_user
    name = f"@{who.username}" if who.username else html.escape(who.first_name or "игрок")
    balance = f" · баланс {user.balance} B" if user is not None else ""
    header_text = (f"🆘 <b>Поддержка</b> · {name} (ID <code>{who.id}</code>){balance}\n"
                   f"<i>Ответь реплаем — ответ уйдёт игроку.</i>")
    delivered = 0
    for chat_id in admin_targets(standalone=standalone):
        try:
            header = await bot.send_message(chat_id, header_text)
            copy = await message.copy_to(chat_id, reply_to_message_id=header.message_id)
        except Exception:  # noqa: BLE001 — админ мог не начать чат с ботом
            logger.warning("Не удалось переслать обращение в %s", chat_id, exc_info=True)
            continue
        for mid in (header.message_id, copy.message_id):
            session.add(SupportMessage(bot_id=bot.id, chat_id=chat_id, message_id=mid, user_tg_id=who.id))
        delivered += 1
    await session.commit()
    return delivered


async def user_for_reply(session: AsyncSession, message: Message) -> int | None:
    """Игрок, которому адресован реплай админа (или None — это не поддержка)."""
    reply = message.reply_to_message
    if reply is None:
        return None
    return (await session.execute(
        select(SupportMessage.user_tg_id)
        .where(SupportMessage.bot_id == message.bot.id, SupportMessage.chat_id == message.chat.id,
               SupportMessage.message_id == reply.message_id)
        .order_by(SupportMessage.id.desc()).limit(1)
    )).scalar_one_or_none()


async def send_answer(bot: Bot, user_tg_id: int, message: Message) -> None:
    """Ответ админа игроку: текст — с подписью «Поддержка», остальное — копией."""
    if message.text:
        await bot.send_message(user_tg_id, f"💬 <b>Поддержка:</b>\n{html.escape(message.text)}")
    else:
        await bot.send_message(user_tg_id, "💬 <b>Поддержка:</b>")
        await message.copy_to(user_tg_id)
