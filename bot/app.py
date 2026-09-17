"""Сборка и запуск приложения Telegram."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from telegram import BotCommand
from telegram.ext import AIORateLimiter, Application, ApplicationBuilder

from . import handlers
from .config import Config
from .history import HistoryStore
from .model_client import build_client

logger = logging.getLogger(__name__)

COMMANDS = [
    BotCommand("start", "Начать работу"),
    BotCommand("help", "Что я умею"),
    BotCommand("reset", "Очистить контекст диалога"),
    BotCommand("about", "Настройки бота"),
]


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
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpx2").setLevel(logging.WARNING)
    logging.getLogger("telegram.ext.Application").setLevel(logging.INFO)


def build_application(config: Config) -> Application:
    """Собирает приложение со всеми обработчиками."""
    history = HistoryStore(
        max_messages=config.history_turns,
        max_chars=config.history_max_chars,
        path=config.history_path,
    )
    runtime = handlers.BotRuntime(config, build_client(config), history)

    async def post_init(application: Application) -> None:
        await history.load()
        try:
            await application.bot.set_my_commands(COMMANDS)
        except Exception:  # noqa: BLE001 — не критично для запуска
            logger.warning("Не удалось обновить список команд", exc_info=True)
        me = await application.bot.get_me()
        logger.info(
            "Бот @%s запущен, %s, модель %s",
            me.username,
            config.provider_info.label,
            config.model,
        )

    application = (
        ApplicationBuilder()
        .token(config.telegram_token)
        .rate_limiter(AIORateLimiter())
        .concurrent_updates(True)
        .post_init(post_init)
        .build()
    )
    handlers.register(application, runtime)
    return application


def main() -> None:
    load_dotenv()
    setup_logging()
    config = Config.from_env()
    application = build_application(config)
    application.run_polling(drop_pending_updates=True)
