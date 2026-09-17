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


async def check_anthropic(config: Config) -> CheckResult:
    """Делает минимальный запрос к модели, чтобы проверить ключ."""
    import anthropic

    try:
        client = anthropic.AsyncAnthropic(
            api_key=config.anthropic_api_key, timeout=30.0, max_retries=1
        )
        await client.messages.create(
            model=config.model,
            max_tokens=16,
            messages=[{"role": "user", "content": "ping"}],
        )
    except Exception as exc:  # noqa: BLE001 — переводим в понятный текст
        return CheckResult(False, "Модель недоступна", friendly_error(exc).user_message)
    return CheckResult(True, f"Модель отвечает: {config.model}")


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
    print("Проверяю настройки…\n")

    results = [
        await check_telegram(config),
        await check_anthropic(config),
        check_history(config),
    ]
    for result in results:
        print(result.render())

    if config.web_search:
        print(f"{OK} Веб-поиск включён")
    else:
        print(f"{WARN} Веб-поиск выключен: бот не сможет отвечать о свежих событиях")

    if config.allowed_user_ids:
        print(f"{WARN} Доступ открыт только для {len(config.allowed_user_ids)} пользователей")

    failed = [result for result in results if not result.ok]
    if failed:
        print(f"\n{FAIL} Не готово к запуску. Сначала почини пункты выше.")
        return 1

    print(f"\n{OK} Всё готово. Запускай: python main.py")
    return 0
