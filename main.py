"""Точка входа Brainrot Battle бота."""
from __future__ import annotations

import asyncio
import logging

from bot.app import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Остановлено пользователем")
