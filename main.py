#!/usr/bin/env python3
"""Точка входа: python main.py"""

from __future__ import annotations

import sys

from bot.app import main
from bot.config import ConfigError

if __name__ == "__main__":
    try:
        main()
    except ConfigError as exc:
        print(f"Ошибка конфигурации: {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nОстановлено пользователем.")
