"""Рантайм активных раундов краша (состояние в памяти процесса).

Каждый раунд — фоновая asyncio-задача, которая раз в CRASH_TICK_SECONDS
дорисовывает множитель в то же сообщение, пока не наступит точка обрыва или
игрок не заберёт выигрыш кнопкой «ЗАБРАТЬ». Один активный раунд на
пользователя (регистр в памяти, ключ — Telegram id). Раунд не переживает
перезапуск процесса — это осознанное упрощение для демо-контура: при
перезапуске бота «зависший» раунд просто исчезает вместе с уже списанной
ставкой, без персистентности незавершённых раундов.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest

from bot.config import config
from bot.keyboards.crash import crash_in_flight_keyboard
from bot.services.crash_service import generate_crash_point, multiplier_at
from bot.utils.texts import CRASH_CRASHED_TEXT, CRASH_IN_FLIGHT_TEXT, CRASH_SLOT_ITEM

HISTORY_LIMIT = 6


@dataclass
class CrashRound:
    tg_id: int
    chat_id: int
    message_id: int
    item_name: str
    item_value: int
    crash_point: float
    start_time: float = field(default_factory=time.monotonic)
    resolved: bool = False
    task: asyncio.Task | None = None
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


_active_rounds: dict[int, CrashRound] = {}
_history: list[float] = []


def get_active_round(tg_id: int) -> CrashRound | None:
    return _active_rounds.get(tg_id)


def history_label() -> str:
    if not _history:
        return "—"
    return ", ".join(f"{p}x" for p in _history[-HISTORY_LIMIT:])


def _record_history(point: float) -> None:
    _history.append(point)
    del _history[: -HISTORY_LIMIT]


def _cleanup(round_: CrashRound) -> None:
    _record_history(round_.crash_point)
    _active_rounds.pop(round_.tg_id, None)


def start_round(
    bot: Bot, tg_id: int, chat_id: int, message_id: int, item_name: str, item_value: int
) -> CrashRound:
    round_ = CrashRound(
        tg_id=tg_id,
        chat_id=chat_id,
        message_id=message_id,
        item_name=item_name,
        item_value=item_value,
        crash_point=generate_crash_point(),
    )
    _active_rounds[tg_id] = round_
    round_.task = asyncio.create_task(_run_round(bot, round_))
    return round_


async def _run_round(bot: Bot, round_: CrashRound) -> None:
    try:
        while True:
            await asyncio.sleep(config.crash_tick_seconds)
            elapsed = time.monotonic() - round_.start_time
            mult = multiplier_at(elapsed)

            if mult >= round_.crash_point or elapsed >= config.crash_max_duration_seconds:
                async with round_.lock:
                    if round_.resolved:
                        return
                    round_.resolved = True
                await _finalize_crash(bot, round_)
                return

            stake_label = CRASH_SLOT_ITEM.format(name=round_.item_name, value=round_.item_value)
            try:
                await bot.edit_message_text(
                    chat_id=round_.chat_id,
                    message_id=round_.message_id,
                    text=CRASH_IN_FLIGHT_TEXT.format(multiplier=mult, stake=stake_label),
                    reply_markup=crash_in_flight_keyboard(mult),
                )
            except TelegramBadRequest:
                pass
    except asyncio.CancelledError:
        return


async def _finalize_crash(bot: Bot, round_: CrashRound) -> None:
    _cleanup(round_)
    stake_label = CRASH_SLOT_ITEM.format(name=round_.item_name, value=round_.item_value)
    try:
        await bot.edit_message_text(
            chat_id=round_.chat_id,
            message_id=round_.message_id,
            text=CRASH_CRASHED_TEXT.format(crash_point=round_.crash_point, stake=stake_label),
        )
    except TelegramBadRequest:
        pass


async def resolve_cashout(bot: Bot, tg_id: int) -> tuple[CrashRound, float] | None:
    """Пытается забрать раунд. Возвращает (раунд, множитель) при успехе, иначе None.

    None означает либо «нет активного раунда», либо «краш наступил в тот же
    момент, раньше клика» — во втором случае раунд уже завершён и сообщение
    отредактировано на «Крах», отдельно уведомлять не нужно.
    """
    round_ = _active_rounds.get(tg_id)
    if round_ is None:
        return None

    async with round_.lock:
        if round_.resolved:
            return None
        elapsed = time.monotonic() - round_.start_time
        mult = multiplier_at(elapsed)
        if mult >= round_.crash_point:
            round_.resolved = True
            crashed_now = True
        else:
            round_.resolved = True
            crashed_now = False

    if round_.task:
        round_.task.cancel()

    if crashed_now:
        await _finalize_crash(bot, round_)
        return None

    _cleanup(round_)
    return round_, mult
