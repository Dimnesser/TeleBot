"""Сборка и запуск aiogram-приложения."""
from __future__ import annotations

import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import config
from bot.database.engine import init_db
from bot.env_loader import load_dotenv
from bot.handlers import routers

logger = logging.getLogger(__name__)


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
