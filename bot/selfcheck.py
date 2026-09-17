"""Проверка настроек: токен Telegram, ключ Anthropic, доступ к сети.

Запускается командой `python main.py --check` и ничего не отправляет
пользователям: только опрашивает оба сервиса и печатает отчёт.
"""

from __future__ import annotations

from dataclasses import dataclass

from .claude import friendly_error
from .config import Config

OK = "✅"
FAIL = "❌"
WARN = "⚠️"


@dataclass
class CheckResult:
    ok: bool
    title: str
    detail: str = ""

    def render(self) -> str:
        mark = OK if self.ok else FAIL
        return f"{mark} {self.title}" + (f"\n   {self.detail}" if self.detail else "")


async def check_telegram(config: Config) -> CheckResult:
    """Спрашивает у Telegram, кто мы."""
    from telegram import Bot
    from telegram.error import InvalidToken, NetworkError, TelegramError

    try:
        bot = Bot(config.telegram_token)
        async with bot:
            me = await bot.get_me()
    except InvalidToken:
        return CheckResult(False, "Токен Telegram отклонён", "Проверь TELEGRAM_BOT_TOKEN в .env")
    except NetworkError as exc:
        return CheckResult(False, "Нет связи с Telegram", str(exc))
    except TelegramError as exc:
        return CheckResult(False, "Telegram вернул ошибку", str(exc))
    return CheckResult(True, f"Telegram: бот @{me.username}", f"id {me.id}")


async def check_model(config: Config) -> CheckResult:
    """Делает минимальный запрос к модели, чтобы проверить ключ и доступ."""
    if not config.api_key:
        names = " или ".join(config.provider_info.key_env)
        return CheckResult(
            False,
            f"Не задан ключ для {config.provider_info.label}",
            f"Впиши {names} в .env. Получить: {config.provider_info.console_url}",
        )

    if config.native_anthropic:
        return await _check_anthropic(config)
    return await _check_openai_compatible(config)


async def _check_anthropic(config: Config) -> CheckResult:
    import anthropic

    try:
        client = anthropic.AsyncAnthropic(
            api_key=config.api_key, timeout=30.0, max_retries=1
        )
        await client.messages.create(
            model=config.model,
            max_tokens=16,
            messages=[{"role": "user", "content": "ping"}],
        )
    except Exception as exc:  # noqa: BLE001 — переводим в понятный текст
        return CheckResult(False, "Модель недоступна", friendly_error(exc).user_message)
    return CheckResult(True, f"Модель отвечает: {config.model}")


async def _check_openai_compatible(config: Config) -> CheckResult:
    from .openai_compat import MISSING_LIBRARY, list_models
    from .openai_compat import friendly_error as openai_friendly_error

    try:
        from openai import AsyncOpenAI
    except ImportError:
        return CheckResult(False, "Не хватает зависимости", MISSING_LIBRARY)

    try:
        client = AsyncOpenAI(
            api_key=config.api_key,
            base_url=config.base_url,
            timeout=30.0,
            max_retries=1,
        )
        await client.chat.completions.create(
            model=config.model,
            max_tokens=16,
            messages=[{"role": "user", "content": "ping"}],
        )
    except Exception as exc:  # noqa: BLE001 — переводим в понятный текст
        detail = openai_friendly_error(exc).user_message
        hint = await _suggest_models(config, list_models)
        return CheckResult(False, "Модель недоступна", f"{detail}{hint}")
    return CheckResult(True, f"Модель отвечает: {config.model}")


async def _suggest_models(config: Config, list_models) -> str:
    """Подсказка со списком доступных моделей, если провайдер его отдаёт."""
    try:
        names = await list_models(config)
    except Exception:  # noqa: BLE001 — подсказка не обязана работать
        return ""
    if not names:
        return ""
    return "\n   Доступные модели: " + ", ".join(names)


def check_history(config: Config) -> CheckResult:
    """Проверяет, что каталог для истории доступен на запись."""
    if config.history_path is None:
        return CheckResult(True, "История хранится только в памяти процесса")
    try:
        config.history_path.parent.mkdir(parents=True, exist_ok=True)
        probe = config.history_path.parent / ".write-probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
    except OSError as exc:
        return CheckResult(False, "Нельзя писать историю на диск", str(exc))
    return CheckResult(True, f"История пишется в {config.history_path}")


async def run_checks(config: Config) -> int:
    """Печатает отчёт. Возвращает код выхода: 0 — всё готово."""
    print(f"Проверяю настройки… Провайдер: {config.provider_info.label}\n")

    results = [
        await check_telegram(config),
        await check_model(config),
        check_history(config),
    ]
    for result in results:
        print(result.render())

    if config.web_search:
        print(f"{OK} Веб-поиск включён")
    elif config.native_anthropic:
        print(f"{WARN} Веб-поиск выключен: бот не сможет отвечать о свежих событиях")
    else:
        print(
            f"{WARN} Веб-поиск недоступен: его умеет только Anthropic. "
            "Бот честно скажет, когда данных не хватает."
        )

    if config.allowed_user_ids:
        print(f"{WARN} Доступ открыт только для {len(config.allowed_user_ids)} пользователей")

    failed = [result for result in results if not result.ok]
    if failed:
        print(f"\n{FAIL} Не готово к запуску. Сначала почини пункты выше.")
        return 1

    print(f"\n{OK} Всё готово. Запускай: python main.py")
    return 0
