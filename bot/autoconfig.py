"""Автоподбор рабочей модели у провайдера.

Нужен, чтобы пользователю хватало одного действия: вставить ключ. Если
модель по умолчанию у провайдера называется иначе или недоступна на его
тарифе, бот спросит список моделей и выберет подходящую сам.
"""

from __future__ import annotations

import logging

from .config import Config

logger = logging.getLogger(__name__)

# Что предпочитать и чего избегать при автоподборе, по провайдерам.
PREFERENCES: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "gemini": (
        ("2.5-flash", "2.0-flash", "flash", "pro"),
        ("vision", "embedding", "aqa", "tts", "image", "live", "thinking-exp"),
    ),
    "groq": (
        ("llama-3.3-70b", "versatile", "llama-3.1-8b", "instant", "llama"),
        ("whisper", "guard", "tts", "vision", "prompt"),
    ),
    "openrouter": (
        (":free",),
        ("vision", "embed"),
    ),
    "openai": (
        ("gpt-4o-mini", "gpt-4.1-mini", "gpt-4o", "gpt-4.1"),
        ("audio", "realtime", "embedding", "tts", "whisper", "image", "moderation"),
    ),
}


def score_model(name: str, prefer: tuple[str, ...], avoid: tuple[str, ...]) -> int:
    """Чем меньше число, тем лучше модель подходит. -1 означает «не годится»."""
    lowered = name.lower()
    if any(bad in lowered for bad in avoid):
        return -1
    for index, good in enumerate(prefer):
        if good in lowered:
            return index
    return len(prefer)


def choose_model(names: list[str], provider: str) -> str | None:
    """Выбирает лучшую модель из списка по правилам провайдера."""
    prefer, avoid = PREFERENCES.get(provider, ((), ()))
    ranked: list[tuple[int, int, str]] = []
    for position, name in enumerate(names):
        rank = score_model(name, prefer, avoid)
        if rank >= 0:
            ranked.append((rank, position, name))
    if not ranked:
        return None
    ranked.sort()
    return ranked[0][2]


async def probe(config: Config) -> str | None:
    """Проверяет модель из настроек. Возвращает текст ошибки или None."""
    if config.native_anthropic:
        import anthropic

        from .claude import friendly_error

        try:
            client = anthropic.AsyncAnthropic(
                api_key=config.api_key, timeout=30.0, max_retries=1
            )
            await client.messages.create(
                model=config.model,
                max_tokens=16,
                messages=[{"role": "user", "content": "ping"}],
            )
        except Exception as exc:  # noqa: BLE001 — переводим в текст
            return friendly_error(exc).user_message
        return None

    from .openai_compat import _import_async_openai
    from .openai_compat import friendly_error as openai_friendly_error

    try:
        AsyncOpenAI = _import_async_openai()
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
    except Exception as exc:  # noqa: BLE001 — переводим в текст
        return openai_friendly_error(exc).user_message
    return None


async def find_working_model(config: Config) -> tuple[str | None, str | None]:
    """Возвращает (рабочая модель, текст ошибки).

    Сначала пробует модель из настроек. Если не вышло, спрашивает у
    провайдера список моделей и подбирает подходящую.
    """
    error = await probe(config)
    if error is None:
        return config.model, None
    if config.native_anthropic:
        return None, error  # у Anthropic подбирать нечего, дело в ключе или балансе

    from dataclasses import replace

    from .openai_compat import list_models

    try:
        names = await list_models(config, limit=200)
    except Exception:  # noqa: BLE001 — список моделей не обязателен
        return None, error

    candidate = choose_model(names, config.provider)
    if candidate is None or candidate == config.model:
        return None, error

    logger.info("Пробую модель %s вместо %s", candidate, config.model)
    retry_error = await probe(replace(config, model=candidate))
    if retry_error is None:
        return candidate, None
    return None, retry_error
