"""Сборка и запуск aiogram-приложения."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import config
from bot.database.engine import init_db
from bot.handlers import routers

logger = logging.getLogger(__name__)


def load_dotenv(path: str | Path = ".env") -> None:
    """Минимальный разбор .env без внешних зависимостей."""
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def setup_logging(level: str | None = None) -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        level=getattr(logging, (level or os.getenv("LOG_LEVEL") or "INFO").upper(), logging.INFO),
    )
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)


async def main() -> None:
    load_dotenv()
    setup_logging()

    if not config.bot_token:
        raise SystemExit("Не задан BOT_TOKEN (переменная окружения или .env)")

    await init_db()

    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    for router in routers:
        dp.include_router(router)

    me = await bot.get_me()
    logger.info("Бот @%s запущен", me.username)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
