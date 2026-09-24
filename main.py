"""Точка входа BrainCore бота."""
from __future__ import annotations

import asyncio
import logging

from bot.env_loader import load_dotenv

load_dotenv()  # должно отработать раньше первого импорта bot.config

from bot.app import main  # noqa: E402 — сознательно после load_dotenv()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Остановлено пользователем")
