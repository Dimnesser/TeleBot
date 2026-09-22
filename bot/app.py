"""Сборка и запуск aiogram-приложения."""
from __future__ import annotations

import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import ErrorEvent

from bot.config import config
from bot.database.engine import init_db
from bot.env_loader import load_dotenv
from bot.handlers import routers
from webapp.server import run_webapp

logger = logging.getLogger(__name__)


def setup_logging(level: str | None = None) -> None:
    logging.basicConfig(
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
        level=getattr(logging, (level or os.getenv("LOG_LEVEL") or "INFO").upper(), logging.INFO),
    )
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)


async def handle_message_not_modified(event: ErrorEvent) -> bool:
    """Глушит безобидную ошибку Telegram «message is not modified».

    Почти каждый обработчик в проекте перерисовывает экран через edit_text
    после действия — если действие не поменяло текст/клавиатуру (повторное
    нажатие уже открытой кнопки, «Назад» на неизменившийся экран и т.п.),
    Telegram отвечает 400 "message is not modified". Это не ошибка
    приложения, поэтому вместо падения хендлера просто закрываем «часики»
    у кнопки, если событие — callback_query.
    """
    if not isinstance(event.exception, TelegramBadRequest):
        return False
    if "message is not modified" not in str(event.exception):
        return False

    callback_query = event.update.callback_query
    if callback_query is not None:
        try:
            await callback_query.answer()
        except TelegramBadRequest:
            pass
    return True


async def main() -> None:
    load_dotenv()
    setup_logging()

    if not config.bot_token:
        raise SystemExit("Не задан BOT_TOKEN (переменная окружения или .env)")

    await init_db()

    bot = Bot(token=config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.errors.register(handle_message_not_modified)
    for router in routers:
        dp.include_router(router)

    me = await bot.get_me()
    logger.info("Бот @%s запущен", me.username)

    await bot.delete_webhook(drop_pending_updates=True)
    await run_webapp(bot)
    await dp.start_polling(bot)
