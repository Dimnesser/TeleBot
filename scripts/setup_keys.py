#!/usr/bin/env python3
"""Настройка бота в два вопроса: токен Telegram и любой ключ AI.

Провайдер определяется по виду ключа, модель подбирается автоматически.

    python scripts/setup_keys.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bot.config import PROVIDERS, Config, detect_provider  # noqa: E402

WHERE_TO_GET = """Ключ можно получить бесплатно:
  Google Gemini  https://aistudio.google.com/apikey    ключ начинается с AIza
  Groq           https://console.groq.com/keys         ключ начинается с gsk_
Платные:
  Anthropic      https://console.anthropic.com         ключ начинается с sk-ant-
  OpenAI         https://platform.openai.com/api-keys  ключ начинается с sk-
  OpenRouter     https://openrouter.ai/keys            ключ начинается с sk-or-"""


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
        is_setting = "=" in line and not line.strip().startswith("#")
        name = line.split("=", 1)[0].strip() if is_setting else ""
        if name and name in updates:
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
    suffix = " [задано, Enter чтобы оставить]" if current else ""
    print(f"{prompt}{suffix}: ", end="", flush=True)
    try:
        return input().strip()
    except EOFError:
        return ""


def ensure_env_file(env_path: Path) -> bool:
    if env_path.exists():
        return True
    example = ROOT / ".env.example"
    if not example.exists():
        print("Нет файла .env.example, запусти установку заново.")
        return False
    env_path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    return True


def main() -> int:
    env_path = ROOT / ".env"
    if not ensure_env_file(env_path):
        return 1

    current = read_env(env_path)
    updates: dict[str, str] = {}

    token = ask("Токен бота от @BotFather", current.get("TELEGRAM_BOT_TOKEN", ""))
    if token:
        updates["TELEGRAM_BOT_TOKEN"] = token
    elif not current.get("TELEGRAM_BOT_TOKEN"):
        print("\nБез токена бот не запустится. Возьми его у @BotFather и повтори.")
        return 1

    print()
    print(WHERE_TO_GET)
    print()

    known_key = next(
        (current[name] for provider in PROVIDERS.values() for name in provider.key_env
         if current.get(name)),
        "",
    )
    key = ask("Вставь ключ", known_key)

    if key:
        provider_name = detect_provider(key)
        if provider_name is None:
            print("\nНе узнал формат ключа. Проверь, что скопировал его целиком.")
            return 1
        provider = PROVIDERS[provider_name]
        print(f"\nЭто ключ {provider.label}.")
        updates["AI_PROVIDER"] = provider_name
        updates[provider.key_env[0]] = key
        updates["AI_API_KEY"] = ""
        updates["AI_MODEL"] = provider.default_model or ""
    elif not known_key:
        print("\nБез ключа бот отвечать не сможет.")
        return 1
    else:
        provider_name = current.get("AI_PROVIDER", "anthropic")

    write_env(env_path, updates)

    print("Подбираю модель…")
    config = load_config(env_path)
    if config is None:
        return 1

    model, error = asyncio.run(find_model(config))
    if model is None:
        print(f"\n❌ {error}")
        return 1

    if model != config.model:
        write_env(env_path, {"AI_MODEL": model})
        print(f"Модель по умолчанию не подошла, выбрал другую: {model}")

    print(f"\n✅ Готово. Провайдер: {config.provider_info.label}, модель: {model}")
    print("Запускай бота:  bash scripts/termux-run.sh")
    return 0


def load_config(env_path: Path) -> Config | None:
    import os

    for name, value in read_env(env_path).items():
        os.environ[name] = value
    try:
        return Config.from_env()
    except Exception as exc:  # noqa: BLE001 — показываем текст пользователю
        print(f"\n❌ {exc}")
        return None


async def find_model(config: Config):
    from bot.autoconfig import find_working_model

    return await find_working_model(config)


if __name__ == "__main__":
    sys.exit(main())
