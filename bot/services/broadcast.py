"""Рассылка всем игрокам в боте (оповещение о запуске ивента).

Идёт фоном, ~20 сообщений в секунду (лимит Telegram — 30/с), на
«слишком часто» (RetryAfter) ждёт сколько сказали; заблокировавших бота
просто пропускает.
"""
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from sqlalchemy import select

from bot.config import config
from bot.database import engine as db
from bot.database.models import User

logger = logging.getLogger(__name__)

DELAY = 0.05
_tasks: set[asyncio.Task] = set()


def play_keyboard() -> InlineKeyboardMarkup | None:
    if not config.webapp_url:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Играть", web_app=WebAppInfo(url=config.webapp_url))]])


async def recipients() -> list[int]:
    async with db.async_session() as session:
        return list((await session.execute(select(User.tg_id))).scalars().all())


async def _send_all(bot: Bot, tg_ids: list[int], text: str) -> tuple[int, int]:
    markup = play_keyboard()
    sent = failed = 0
    for tg_id in tg_ids:
        for _ in range(3):
            try:
                await bot.send_message(tg_id, text, reply_markup=markup)
                sent += 1
                break
            except TelegramRetryAfter as exc:
                await asyncio.sleep(exc.retry_after + 1)
            except Exception:  # noqa: BLE001 — заблокировал бота, удалил аккаунт и т.п.
                failed += 1
                break
        await asyncio.sleep(DELAY)
    logger.info("Рассылка: доставлено %s, не доставлено %s", sent, failed)
    return sent, failed


async def start(bot: Bot, text: str, tg_ids: list[int] | None = None) -> int:
    """Запускает рассылку фоном (всем или списку tg_ids), возвращает число получателей."""
    if tg_ids is None:
        tg_ids = await recipients()
    task = asyncio.create_task(_send_all(bot, tg_ids, text))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)
    return len(tg_ids)
