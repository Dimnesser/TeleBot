"""Автозапуск случайных ивентов.

Админ включает в Mini App и задаёт: как часто (случайный интервал от/до в
минутах), сколько длится ивент (от/до), силу (слабые / средние / сильные),
какие ивенты участвуют и слать ли рассылку в бот. Фоновая задача раз в
полминуты смотрит, не пора ли: берёт случайный ивент из разрешённых, который
сейчас не идёт, случайную силу в выбранном диапазоне и длительность,
запускает и планирует следующий. Всё хранится в app_meta — переживает
перезапуск.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import time

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database import engine as db
from bot.services import broadcast, events_service, settings_service

logger = logging.getLogger(__name__)

KEY = "auto_events"
TICK_SECONDS = 30
# Сила: доля от диапазона ивента (min…max), из которой берётся случайное значение.
STRENGTHS = {"low": (0.0, 0.3), "mid": (0.2, 0.6), "high": (0.5, 1.0)}
DEFAULTS = {
    "enabled": False,
    "gap_min": 120, "gap_max": 360,        # пауза между ивентами, минут
    "dur_min": 30, "dur_max": 90,          # длительность ивента, минут
    "strength": "mid",
    "types": list(events_service.TYPES),
    "notify": True,
    "next_at": 0,
    "last": None,                          # последний автоивент: {type, value, minutes, at}
}

_task: asyncio.Task | None = None


async def get_config(session: AsyncSession) -> dict:
    raw = await settings_service.get_setting(session, KEY)
    cfg = dict(DEFAULTS)
    if raw:
        try:
            cfg.update(json.loads(raw))
        except ValueError:
            pass
    cfg["types"] = [t for t in cfg["types"] if t in events_service.TYPES]
    return cfg


async def save_config(session: AsyncSession, cfg: dict) -> None:
    await settings_service.set_setting(session, KEY, json.dumps(cfg, ensure_ascii=False, separators=(",", ":")))


def validate(update: dict, cfg: dict) -> dict:
    """Новые настройки поверх старых; ValueError с понятным текстом."""
    new = dict(cfg)
    for key in ("gap_min", "gap_max", "dur_min", "dur_max"):
        if key in update:
            try:
                new[key] = int(update[key])
            except (TypeError, ValueError):
                raise ValueError("Интервалы и длительность — целые минуты") from None
    if not 5 <= new["gap_min"] <= new["gap_max"] <= 60 * 24 * 7:
        raise ValueError("Пауза между ивентами: от 5 минут, «от» не больше «до»")
    if not 1 <= new["dur_min"] <= new["dur_max"] <= events_service.MAX_MINUTES:
        raise ValueError("Длительность: от 1 минуты, «от» не больше «до»")
    if "strength" in update:
        if update["strength"] not in STRENGTHS:
            raise ValueError("Сила: low, mid или high")
        new["strength"] = update["strength"]
    if "types" in update:
        types = [t for t in update["types"] if t in events_service.TYPES]
        if not types:
            raise ValueError("Выбери хотя бы один ивент")
        new["types"] = types
    for key in ("enabled", "notify"):
        if key in update:
            new[key] = bool(update[key])
    if new["enabled"] and (not cfg["enabled"] or not new.get("next_at")):
        new["next_at"] = time.time() + random.randint(new["gap_min"], new["gap_max"]) * 60
    if not new["enabled"]:
        new["next_at"] = 0
    return new


def pick_value(code: str, strength: str) -> float:
    t = events_service.TYPES[code]
    lo_f, hi_f = STRENGTHS[strength]
    frac = random.uniform(lo_f, hi_f)
    if code == "free":  # у «free» сильнее — меньший интервал
        val = t.max_value - frac * (t.max_value - t.min_value)
        return max(t.min_value, round(val / 5) * 5)
    val = t.min_value + frac * (t.max_value - t.min_value)
    return round(val, 1) if t.unit == "x" else float(round(val))


async def fire(session: AsyncSession, bot: Bot, cfg: dict, *, forced: bool = False) -> dict | None:
    """Запустить случайный ивент сейчас и запланировать следующий."""
    running = set(events_service.active())
    choices = [t for t in cfg["types"] if t not in running] or ([] if not forced else cfg["types"])
    if not choices:
        return None
    code = random.choice(choices)
    val = pick_value(code, cfg["strength"])
    minutes = random.randint(cfg["dur_min"], cfg["dur_max"])
    await events_service.start(session, code, val, minutes)
    if cfg["notify"]:
        await broadcast.start(bot, events_service.announcement(code, val, minutes))
    cfg["last"] = {"type": code, "value": val, "minutes": minutes, "at": int(time.time())}
    if cfg["enabled"]:
        cfg["next_at"] = time.time() + minutes * 60 + random.randint(cfg["gap_min"], cfg["gap_max"]) * 60
    await save_config(session, cfg)
    logger.info("Автоивент: %s %s на %s мин", code, val, minutes)
    return cfg["last"]


async def tick(bot: Bot) -> dict | None:
    async with db.async_session() as session:
        cfg = await get_config(session)
        if not cfg["enabled"] or not cfg["next_at"] or time.time() < cfg["next_at"]:
            return None
        return await fire(session, bot, cfg)


async def _loop(bot: Bot) -> None:
    while True:
        try:
            await tick(bot)
        except Exception:  # noqa: BLE001 — фоновая задача не должна падать
            logger.warning("Ошибка автоивентов", exc_info=True)
        await asyncio.sleep(TICK_SECONDS)


def start(bot: Bot) -> None:
    global _task
    if _task is None or _task.done():
        _task = asyncio.create_task(_loop(bot))
