"""Рантайм краша для Mini App — состояние в памяти процесса.

Модель раунда:
  * множитель растёт как e^(k·t) (k = WEBAPP_CRASH_GROWTH_PER_SEC), до
    crash_max_multiplier; клиент рисует ту же кривую сам, сервер нужен
    только для точки взрыва — её знает только он;
  * точка взрыва — bot.services.crash_service.generate_crash_point (1/U с
    хаус-эджем), до неё раунд не обрывается ни по какому таймеру;
  * итог раунда (взрыв / кэшаут) хранится до старта следующего раунда
    игрока, так что клиент не теряет его, если какой-то опрос не дошёл.

Приз за кэшаут — не тот же брейнрот с умноженной ценностью, а лучший
реальный брейнрот из ростера, чья ценность укладывается в ставка × X
(prize_for). Чем выше X — тем дороже брейнрот.

Реестр раундов отдельный от bot/services/crash_runtime.py (чат-версия
краша): раунд из бота не виден Mini App и наоборот.
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from bot.config import config
from bot.data.brainrot_roster import ROSTER, ROSTER_BY_NAME
from bot.services.crash_service import generate_crash_point

HISTORY_LIMIT = 12


def growth_per_sec() -> float:
    return config.webapp_crash_growth_per_sec


def multiplier_at(elapsed_seconds: float) -> float:
    raw = math.exp(growth_per_sec() * max(0.0, elapsed_seconds))
    return round(min(raw, config.crash_max_multiplier), 2)


@dataclass
class CrashRound:
    tg_id: int
    item_name: str
    item_value: int
    crash_point: float
    start_time: float = field(default_factory=time.monotonic)
    outcome: str | None = None  # None — в полёте, "crashed" | "cashed"
    final_multiplier: float | None = None
    prize: tuple[str, int] | None = None

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.start_time


_rounds: dict[int, CrashRound] = {}  # последний раунд игрока (в полёте или завершённый)
_history: list[float] = []


def history() -> list[float]:
    return list(_history[-HISTORY_LIMIT:])


def history_label() -> str:
    return ", ".join(f"{p}x" for p in history()) or "—"


def prize_for(stake_name: str, stake_value: int, multiplier: float) -> tuple[str, int]:
    """Лучший брейнрот ростера с ценностью ≤ ставка × X (и не дешевле ставки).

    Если дороже ставки ничего не проходит, игрок забирает свою ставку назад.
    Ставка вне ростера (старые записи инвентаря) — та же ставка с умноженной
    ценностью: подобрать ей «соседей» не по чему.
    """
    if stake_name not in ROSTER_BY_NAME:
        return stake_name, round(stake_value * multiplier)
    budget = stake_value * multiplier
    best = max(
        (b for b in ROSTER if stake_value <= b.value <= budget),
        key=lambda b: b.value,
        default=None,
    )
    return (best.name, best.value) if best else (stake_name, stake_value)


def prize_ladder(stake_name: str, stake_value: int) -> list[dict]:
    """Ступени призов: при каком X брейнрот становится доступен."""
    if stake_name not in ROSTER_BY_NAME:
        return []
    steps = sorted(
        (b for b in ROSTER if stake_value < b.value <= stake_value * config.crash_max_multiplier),
        key=lambda b: b.value,
    )
    return [{"name": b.name, "value": b.value, "at": round(b.value / stake_value, 2)} for b in steps]


def get_round(tg_id: int) -> CrashRound | None:
    return _rounds.get(tg_id)


def is_flying(tg_id: int) -> bool:
    round_ = _rounds.get(tg_id)
    return round_ is not None and _refresh(round_) is None


def start_round(tg_id: int, item_name: str, item_value: int) -> CrashRound:
    round_ = CrashRound(tg_id=tg_id, item_name=item_name, item_value=item_value, crash_point=generate_crash_point())
    _rounds[tg_id] = round_
    _refresh(round_)  # точка 1.00 — взрыв сразу на старте
    return round_


def _finish(round_: CrashRound, outcome: str, multiplier: float) -> None:
    round_.outcome = outcome
    round_.final_multiplier = multiplier
    _history.append(round_.crash_point)
    del _history[:-HISTORY_LIMIT]


def _refresh(round_: CrashRound) -> str | None:
    """Досчитывает раунд к текущему моменту; возвращает outcome или None (летит)."""
    if round_.outcome is None and multiplier_at(round_.elapsed) >= round_.crash_point:
        _finish(round_, "crashed", round_.crash_point)
    return round_.outcome


def poll(tg_id: int) -> CrashRound | None:
    round_ = _rounds.get(tg_id)
    if round_ is not None:
        _refresh(round_)
    return round_


def cashout(tg_id: int) -> CrashRound | None:
    """Забрать раунд. None — раунда нет, он уже взорвался или уже забран."""
    round_ = _rounds.get(tg_id)
    if round_ is None or _refresh(round_) is not None:
        return None
    mult = multiplier_at(round_.elapsed)
    _finish(round_, "cashed", mult)
    round_.prize = prize_for(round_.item_name, round_.item_value, mult)
    return round_
