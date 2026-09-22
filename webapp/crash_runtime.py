"""Рантайм краша для Mini App — состояние в памяти процесса, без фоновой
задачи: фронтенд опрашивает GET /api/crash/state раз в ~1с, множитель
считается на лету из времени старта (bot.services.crash_service.multiplier_at),
как и в bot/services/crash_runtime.py, но без привязки к Telegram-сообщению.

Отдельный от bot/services/crash_runtime.py реестр раундов (ключ тот же —
tg_id, но разные словари): раунд, начатый в боте, не виден Mini App и
наоборот. Ставка (предмет инвентаря) списывается сразу при старте в обоих
случаях, так что дублирующего списания одной и той же ставки быть не может —
просто два независимых раунда, если запустить оба интерфейса одновременно.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from bot.config import config
from bot.services.crash_service import generate_crash_point, multiplier_at

HISTORY_LIMIT = 6


@dataclass
class CrashRound:
    tg_id: int
    item_name: str
    item_value: int
    crash_point: float
    start_time: float = field(default_factory=time.monotonic)
    resolved: bool = False


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
    del _history[:-HISTORY_LIMIT]


def start_round(tg_id: int, item_name: str, item_value: int) -> CrashRound:
    round_ = CrashRound(tg_id=tg_id, item_name=item_name, item_value=item_value, crash_point=generate_crash_point())
    _active_rounds[tg_id] = round_
    return round_


def _finish(round_: CrashRound) -> None:
    round_.resolved = True
    _record_history(round_.crash_point)
    _active_rounds.pop(round_.tg_id, None)


def poll_state(tg_id: int) -> tuple[CrashRound, float, bool] | None:
    """Возвращает (раунд, текущий множитель, обрушился_ли) или None, если раунда нет."""
    round_ = _active_rounds.get(tg_id)
    if round_ is None or round_.resolved:
        return None

    elapsed = time.monotonic() - round_.start_time
    mult = multiplier_at(elapsed)
    crashed = mult >= round_.crash_point or elapsed >= config.crash_max_duration_seconds
    if crashed:
        _finish(round_)
        return round_, round_.crash_point, True
    return round_, mult, False


def cashout(tg_id: int) -> tuple[CrashRound, float] | None:
    """Пытается забрать раунд. None — раунда нет или он уже успел обрушиться."""
    state = poll_state(tg_id)
    if state is None:
        return None
    round_, mult, crashed = state
    if crashed:
        return None

    _finish(round_)
    return round_, mult
