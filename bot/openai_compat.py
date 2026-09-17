"""Клиент для провайдеров с интерфейсом, совместимым с OpenAI.

Через него работают Google Gemini, Groq, OpenRouter, локальная Ollama и любой
другой сервер, который отдаёт `/chat/completions`. Формат сообщений внутри
бота — как у Anthropic, поэтому здесь он переводится в формат OpenAI.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from .config import Config
from .types import EMPTY_MESSAGE, REFUSAL_MESSAGE, ModelError, Reply

logger = logging.getLogger(__name__)

DeltaCallback = Callable[[str], Awaitable[None]]

MISSING_LIBRARY = (
    "Не установлена библиотека openai, без неё этот провайдер не работает. "
    "Выполни в каталоге бота: ./.venv/bin/pip install -r requirements.txt"
)


def _import_async_openai():
    """Отдельная функция, чтобы отсутствие библиотеки давало понятный текст."""
    try:
        from openai import AsyncOpenAI
    except ImportError as exc:  # pragma: no cover — зависит от окружения
        raise ModelError(MISSING_LIBRARY) from exc
    return AsyncOpenAI

# Куски текста ошибок, для которых сырое сообщение провайдера бесполезно.
KNOWN_ERRORS: tuple[tuple[str, str], ...] = (
    (
        "api key",
        "Ключ не принят провайдером. Проверь, что скопировал его целиком, без пробелов.",
    ),
    (
        "api_key_invalid",
        "Ключ не принят провайдером. Проверь, что скопировал его целиком, без пробелов.",
    ),
    ("unauthorized", "Ключ не принят провайдером. Проверь, что скопировал его целиком."),
    ("insufficient_quota", "У провайдера закончилась квота. Проверь лимиты в его панели."),
    ("quota", "Исчерпан лимит запросов у провайдера. Подожди или смени модель."),
    ("model_not_found", "Такой модели у провайдера нет. Проверь AI_MODEL."),
    ("does not exist", "Такой модели у провайдера нет. Проверь AI_MODEL."),
    ("context length", "Диалог стал слишком длинным. Отправь /reset и спроси заново."),
    ("too long", "Диалог стал слишком длинным. Отправь /reset и спроси заново."),
)


def to_openai_messages(system: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Переводит историю из формата Anthropic в формат OpenAI."""
    result: list[dict[str, Any]] = [{"role": "system", "content": system}]

    for message in messages:
        role = message.get("role", "user")
        content = message.get("content")

        if isinstance(content, str):
            result.append({"role": role, "content": content})
            continue

        parts: list[dict[str, Any]] = []
        for block in content or []:
            kind = block.get("type")
            if kind == "text":
                parts.append({"type": "text", "text": block.get("text", "")})
            elif kind == "image":
                source = block.get("source") or {}
                if source.get("type") != "base64":
                    continue
                media = source.get("media_type", "image/jpeg")
                data = source.get("data", "")
                parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{media};base64,{data}"},
                    }
                )

        if not parts:
            continue
        # Ответы модели всегда текстовые: картинки в них не отправляем.
        if role == "assistant":
            text = "\n".join(part["text"] for part in parts if part["type"] == "text")
            result.append({"role": role, "content": text})
        elif len(parts) == 1 and parts[0]["type"] == "text":
            result.append({"role": role, "content": parts[0]["text"]})
        else:
            result.append({"role": role, "content": parts})

    return result


def friendly_error(exc: Exception) -> ModelError:
    """Переводит исключение провайдера в понятное пользователю сообщение."""
    if isinstance(exc, ModelError):
        return exc
    try:
        import openai
    except ImportError:  # pragma: no cover — зависит от окружения
        return ModelError(MISSING_LIBRARY)

    if isinstance(exc, openai.AuthenticationError):
        return ModelError("Ключ провайдера отклонён. Проверь его в .env")
    if isinstance(exc, openai.PermissionDeniedError):
        return ModelError("У ключа не хватает прав. Проверь настройки в панели провайдера.")
    if isinstance(exc, openai.NotFoundError):
        return ModelError("Модель не найдена. Проверь AI_MODEL и адрес AI_BASE_URL.")
    if isinstance(exc, openai.RateLimitError):
        return ModelError(
            "Достигнут лимит бесплатного тарифа. Подожди немного и повтори.", retryable=True
        )
    if isinstance(exc, openai.APITimeoutError):
        return ModelError("Провайдер не ответил вовремя. Попробуй ещё раз.", retryable=True)
    if isinstance(exc, openai.APIConnectionError):
        return ModelError("Нет связи с провайдером. Проверь интернет.", retryable=True)
    if isinstance(exc, openai.APIStatusError):
        text = (getattr(exc, "message", "") or str(exc)).lower()
        for marker, explanation in KNOWN_ERRORS:
            if marker in text:
                return ModelError(explanation)
        if exc.status_code >= 500:
            return ModelError("У провайдера временная ошибка. Попробуй ещё раз.", retryable=True)
        return ModelError(f"Провайдер отклонил запрос: {exc.message}")
    return ModelError("Что-то пошло не так при обращении к модели.", retryable=True)


class OpenAICompatClient:
    """Тот же интерфейс, что у клиента Anthropic, поверх OpenAI-совместимого API."""

    def __init__(self, config: Config, client: Any | None = None) -> None:
        self._config = config
        if client is not None:
            self._client = client
        else:
            AsyncOpenAI = _import_async_openai()

            self._client = AsyncOpenAI(
                api_key=config.api_key or "not-needed",
                base_url=config.base_url,
                timeout=config.request_timeout,
                max_retries=2,
            )

    @property
    def tools(self) -> list[dict[str, Any]]:
        return []  # серверного веб-поиска у этих провайдеров нет

    async def complete(
        self,
        system: str,
        messages: list[dict[str, Any]],
        *,
        on_delta: DeltaCallback | None = None,
    ) -> Reply:
        payload = to_openai_messages(system, messages)
        chunks: list[str] = []
        finish_reason: str | None = None
        input_tokens = 0
        output_tokens = 0

        try:
            stream = await self._client.chat.completions.create(
                model=self._config.model,
                messages=payload,
                max_tokens=self._config.max_tokens,
                stream=True,
                stream_options={"include_usage": True},
            )
            async for chunk in stream:
                usage = getattr(chunk, "usage", None)
                if usage is not None:
                    input_tokens = getattr(usage, "prompt_tokens", 0) or input_tokens
                    output_tokens = getattr(usage, "completion_tokens", 0) or output_tokens

                choices = getattr(chunk, "choices", None) or []
                if not choices:
                    continue
                choice = choices[0]
                finish_reason = getattr(choice, "finish_reason", None) or finish_reason
                delta = getattr(choice, "delta", None)
                piece = getattr(delta, "content", None) if delta is not None else None
                if piece:
                    chunks.append(piece)
                    if on_delta is not None:
                        await on_delta(piece)
        except Exception as exc:  # noqa: BLE001 — переводим в понятный текст
            logger.exception("Ошибка запроса к провайдеру")
            raise friendly_error(exc) from exc

        text = "".join(chunks).strip()
        if finish_reason == "content_filter":
            return Reply(text=REFUSAL_MESSAGE, stop_reason="refusal", refused=True)

        return Reply(
            text=text or EMPTY_MESSAGE,
            stop_reason=finish_reason,
            truncated=finish_reason == "length",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )


async def list_models(config: Config, limit: int = 15) -> list[str]:
    """Названия доступных моделей — чтобы подсказать при опечатке в AI_MODEL."""
    AsyncOpenAI = _import_async_openai()

    client = AsyncOpenAI(
        api_key=config.api_key or "not-needed",
        base_url=config.base_url,
        timeout=20.0,
        max_retries=0,
    )
    page = await client.models.list()
    return [model.id for model in page.data][:limit]
