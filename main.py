#!/usr/bin/env python3
"""Точка входа.

    python main.py           запустить бота
    python main.py --check   проверить настройки и связь, ничего не запуская
"""

from __future__ import annotations

import asyncio
import sys

from bot.app import load_dotenv, main, setup_logging
from bot.config import Config, ConfigError


def run_selfcheck() -> int:
    from bot.selfcheck import run_checks

    load_dotenv()
    setup_logging("WARNING")
    return asyncio.run(run_checks(Config.from_env()))


if __name__ == "__main__":
    try:
        if "--check" in sys.argv[1:]:
            sys.exit(run_selfcheck())
        main()
    except ConfigError as exc:
        print(f"Ошибка конфигурации: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nОстановлено пользователем.")
