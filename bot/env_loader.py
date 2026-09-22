"""Загрузка .env — вынесено в модуль без других bot.*-импортов.

Должна вызываться раньше первого импорта bot.config: Config строит
значения через os.getenv(...) прямо в определении полей, то есть один раз,
в момент импорта модуля. Если .env загрузить позже (как раньше делалось
внутри bot.app.main()), переменные из файла в os.environ уже опоздают —
Config к тому моменту успеет собраться с пустыми значениями по умолчанию.
"""
from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: str | Path = ".env") -> None:
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
