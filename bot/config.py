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
    stars_to_balance_rate: int = int(os.getenv("STARS_TO_BALANCE_RATE", "1"))
    min_stars_amount: int = int(os.getenv("MIN_STARS_AMOUNT", "50"))
    max_stars_amount: int = int(os.getenv("MAX_STARS_AMOUNT", "100000"))
    max_concurrent_trades: int = int(os.getenv("MAX_CONCURRENT_TRADES", "5"))
    avg_trade_minutes: int = int(os.getenv("AVG_TRADE_MINUTES", "8"))


config = Config()


def is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids
