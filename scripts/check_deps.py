#!/usr/bin/env python3
"""Проверка, что установленные зависимости не старше нужных версий.

Возвращает 0, если всё в порядке, иначе 1 и список того, что обновить.
Используется скриптами запуска, чтобы не гонять pip на каждом старте.
"""

from __future__ import annotations

import sys
from importlib.metadata import PackageNotFoundError, version

# Пакет: минимальная версия и причина, по которой она нужна.
REQUIRED: dict[str, tuple[str, str]] = {
    "python-telegram-bot": ("22.8", "поддержка Python 3.14"),
    "anthropic": ("1.6.0", "текущий Messages API"),
    "openai": ("1.60", "потоковые ответы у сторонних провайдеров"),
}


def parse(raw: str) -> tuple[int, ...]:
    """Числовая часть версии: 22.8.1rc1 -> (22, 8, 1)."""
    parts: list[int] = []
    for chunk in raw.split("."):
        digits = ""
        for char in chunk:
            if not char.isdigit():
                break
            digits += char
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts) or (0,)


def problems() -> list[str]:
    found: list[str] = []
    for name, (minimum, reason) in REQUIRED.items():
        try:
            installed = version(name)
        except PackageNotFoundError:
            found.append(f"{name} не установлен ({reason})")
            continue
        if parse(installed) < parse(minimum):
            found.append(f"{name} {installed} старше нужного {minimum} ({reason})")
    return found


def main() -> int:
    found = problems()
    for line in found:
        print(line)
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
