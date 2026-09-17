#!/usr/bin/env python3
"""Диалог настройки .env: провайдер модели, ключи, модель.

Запускается через scripts/termux-keys.sh, но работает и сам по себе:
    python scripts/setup_keys.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bot.config import PROVIDERS  # noqa: E402

MENU = [
    ("gemini", "Google Gemini", "бесплатный тариф, лучший выбор без оплаты"),
    ("groq", "Groq", "бесплатный тариф, очень быстрые ответы"),
    ("anthropic", "Anthropic (Claude)", "самое высокое качество, нужны платные кредиты"),
    ("openrouter", "OpenRouter", "много моделей, есть бесплатные"),
]


def read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip()
    return values


def write_env(path: Path, updates: dict[str, str]) -> None:
    """Меняет значения, сохраняя порядок строк и комментарии."""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    seen: set[str] = set()
    result: list[str] = []
    for line in lines:
        name = line.split("=", 1)[0].strip() if "=" in line and not line.strip().startswith("#") else ""
        if name in updates:
            result.append(f"{name}={updates[name]}")
            seen.add(name)
        else:
            result.append(line)
    extra = [f"{name}={value}" for name, value in updates.items() if name not in seen]
    if extra:
        result.append("")
        result.extend(extra)
    path.write_text("\n".join(result).rstrip("\n") + "\n", encoding="utf-8")
    path.chmod(0o600)


def ask(prompt: str, current: str = "") -> str:
    suffix = " [сейчас задано, Enter чтобы оставить]" if current else ""
    print(f"{prompt}{suffix}: ", end="", flush=True)
    return input().strip()


def choose_provider(current: str) -> str:
    print("Откуда брать модель?\n")
    for index, (name, label, note) in enumerate(MENU, start=1):
        mark = " ← сейчас" if name == current else ""
        print(f"  {index}. {label} — {note}{mark}")
    print("  0. Оставить как есть\n")

    while True:
        print("Номер: ", end="", flush=True)
        choice = input().strip()
        if choice in ("", "0"):
            return current
        if choice.isdigit() and 1 <= int(choice) <= len(MENU):
            return MENU[int(choice) - 1][0]
        print("Не понял. Введи номер из списка.")


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    env_path = root / ".env"
    if not env_path.exists():
        example = root / ".env.example"
        if not example.exists():
            print("Нет файла .env.example, запусти установку заново.")
            return 1
        env_path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")

    current = read_env(env_path)
    updates: dict[str, str] = {}

    provider_name = choose_provider(current.get("AI_PROVIDER", "anthropic"))
    provider = PROVIDERS[provider_name]
    updates["AI_PROVIDER"] = provider_name
    print(f"\nВыбрано: {provider.label}\n")

    token = ask("Токен бота от @BotFather", current.get("TELEGRAM_BOT_TOKEN", ""))
    if token:
        updates["TELEGRAM_BOT_TOKEN"] = token

    key_var = provider.key_env[0]
    if provider.console_url:
        print(f"Ключ можно получить здесь: {provider.console_url}")
    key = ask(f"Ключ ({key_var})", current.get(key_var, ""))
    if key:
        updates[key_var] = key
        updates["AI_API_KEY"] = ""  # общий ключ не должен перебивать выбранный

    if provider.default_model:
        model = ask(f"Модель [по умолчанию {provider.default_model}]", current.get("AI_MODEL", ""))
    else:
        print("У этого провайдера нужно указать модель явно.")
        model = ask("Модель", current.get("AI_MODEL", ""))
    if not model:
        model = current.get("AI_MODEL", "") or (provider.default_model or "")
    if not model:
        print("\nБез модели бот не запустится. Запусти настройку ещё раз.")
        return 1
    # Пишем модель явно, чтобы в .env было видно, что именно используется.
    updates["AI_MODEL"] = model

    write_env(env_path, updates)
    print("\nЗаписано в .env")

    final = read_env(env_path)
    missing = []
    if not final.get("TELEGRAM_BOT_TOKEN"):
        missing.append("TELEGRAM_BOT_TOKEN")
    if not final.get(key_var):
        missing.append(key_var)
    if missing:
        print(f"Ещё не заполнено: {', '.join(missing)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
