"""Конфигурация из переменных окружения."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _parse_admin_ids(raw: str) -> list[int]:
    return [int(x) for x in raw.split(",") if x.strip().isdigit()]


@dataclass(frozen=True)
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    admin_ids: list[int] = field(default_factory=lambda: _parse_admin_ids(os.getenv("ADMIN_IDS", "")))
    admin_chat_id: int = int(os.getenv("ADMIN_CHAT_ID", "0") or 0)
    database_url: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/brainrot_battle.db")
    # Пополнение Stars — от 1 ⭐ (минимума нет); MIN_STARS_AMOUNT в .env больше не читается.
    min_stars_amount: int = 1
    # Апгрейдер: шанс всегда режется в этот диапазон, чтобы не было 0%/100% исходов.
    upgrader_min_chance_percent: int = int(os.getenv("UPGRADER_MIN_CHANCE_PERCENT", "1"))
    # Mini App: в список целей апгрейдера попадают только брейнроты, для
    # которых честный шанс (вклад / цель) — от этого порога вниз до 1%.
    upgrader_max_target_chance_percent: int = int(os.getenv("UPGRADER_MAX_TARGET_CHANCE_PERCENT", "75"))
    upgrader_max_chance_percent: int = int(os.getenv("UPGRADER_MAX_CHANCE_PERCENT", "95"))
    # Краш: интервал тика анимации, скорость роста множителя, safety-cap по времени.
    crash_tick_seconds: float = float(os.getenv("CRASH_TICK_SECONDS", "1.2"))
    crash_growth_rate: float = float(os.getenv("CRASH_GROWTH_RATE", "0.07"))
    crash_max_duration_seconds: float = float(os.getenv("CRASH_MAX_DURATION_SECONDS", "30"))
    crash_house_edge: float = float(os.getenv("CRASH_HOUSE_EDGE", "0.97"))
    crash_max_multiplier: float = float(os.getenv("CRASH_MAX_MULTIPLIER", "100"))
    # Краш в Mini App: множитель = e^(k·t); k=0.1 → ×2 за ~7с, ×10 за ~23с.
    webapp_crash_growth_per_sec: float = float(os.getenv("WEBAPP_CRASH_GROWTH_PER_SEC", "0.1"))
    # Дайсы: шанс отдельного бонус-события (rainbow) поверх таблицы совпадений.
    dice_bonus_chance_percent: float = float(os.getenv("DICE_BONUS_CHANCE_PERCENT", "3"))
    dice_bonus_multiplier: float = float(os.getenv("DICE_BONUS_MULTIPLIER", "10"))
    # Mini App: публичный HTTPS-адрес (см. webapp/README.md), на котором
    # запущен webapp/server.py — по нему бот отправляет кнопку web_app.
    webapp_url: str = os.getenv("WEBAPP_URL", "")
    webapp_host: str = os.getenv("WEBAPP_HOST", "0.0.0.0")
    webapp_port: int = int(os.getenv("WEBAPP_PORT", "8080"))
    # Небезопасный обход проверки initData для локальной отладки в обычном
    # браузере (Telegram WebView не нужен) — ?dev_tg_id=... в query string.
    # По умолчанию выключен: включать только на localhost, никогда на
    # адресе, пробрасываемом наружу (ngrok и т.п.).
    webapp_allow_dev_auth: bool = os.getenv("WEBAPP_ALLOW_DEV_AUTH", "false").lower() == "true"


config = Config()


# Админы, которым владелец выдал панель из Mini App (таблица admin_grants).
# Держим копию в памяти: is_admin зовётся синхронно из хендлеров и API.
_granted_admins: set[int] = set()


def set_granted_admins(ids) -> None:
    _granted_admins.clear()
    _granted_admins.update(int(i) for i in ids)


def is_owner(user_id: int) -> bool:
    """Владелец — из ADMIN_IDS в .env: только он выдаёт и снимает админку."""
    return user_id in config.admin_ids


def is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids or user_id in _granted_admins


def all_admin_ids() -> list[int]:
    return list(dict.fromkeys([*config.admin_ids, *_granted_admins]))
