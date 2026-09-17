"""Обёртка над Messages API: потоковый ответ, веб-поиск, обработка ошибок."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Iterable

import anthropic

from .config import Config, web_search_tool_type

logger = logging.getLogger(__name__)

DeltaCallback = Callable[[str], Awaitable[None]]

FALLBACK_BETA = "server-side-fallback-2026-07-01"
MAX_PAUSE_RESUMES = 4

REFUSAL_MESSAGE = (
    "Не могу ответить на этот запрос. Попробуй переформулировать или "
    "спросить о чём-то другом — я рядом."
)
EMPTY_MESSAGE = "Ответ получился пустым. Попробуй переформулировать вопрос."


@dataclass
class Reply:
    """Результат одного обращения к модели."""

    text: str
    stop_reason: str | None = None
    refused: bool = False
    truncated: bool = False
    search_queries: list[str] = field(default_factory=list)
    sources: list[tuple[str, str]] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def used_search(self) -> bool:
        return bool(self.search_queries)


class ClaudeError(RuntimeError):
    """Ошибка обращения к API с текстом, готовым к показу пользователю."""

    def __init__(self, user_message: str, *, retryable: bool = False) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.retryable = retryable


def friendly_error(exc: Exception) -> ClaudeError:
    """Переводит исключение SDK в понятное пользователю сообщение."""
    if isinstance(exc, anthropic.AuthenticationError):
        return ClaudeError("Ключ доступа к модели недействителен. Нужно проверить настройки бота.")
    if isinstance(exc, anthropic.PermissionDeniedError):
        return ClaudeError("У ключа доступа не хватает прав для этой модели.")
    if isinstance(exc, anthropic.NotFoundError):
        return ClaudeError("Указанная модель недоступна. Проверь настройку CLAUDE_MODEL.")
    if isinstance(exc, anthropic.RateLimitError):
        return ClaudeError(
            "Слишком много запросов к модели. Подожди минуту и повтори.", retryable=True
        )
    if isinstance(exc, anthropic.BadRequestError):
        return ClaudeError(f"Запрос отклонён API: {exc.message}")
    if isinstance(exc, anthropic.APITimeoutError):
        return ClaudeError("Модель не ответила вовремя. Попробуй ещё раз.", retryable=True)
    if isinstance(exc, anthropic.APIConnectionError):
        return ClaudeError("Нет связи с сервером модели. Попробуй чуть позже.", retryable=True)
    if isinstance(exc, anthropic.APIStatusError):
        if exc.status_code >= 500:
            return ClaudeError("На стороне модели временная ошибка. Попробуй ещё раз.", retryable=True)
        return ClaudeError(f"Ошибка API ({exc.status_code}): {exc.message}")
    return ClaudeError("Что-то пошло не так при обращении к модели. Попробуй ещё раз.", retryable=True)


class ClaudeClient:
    """Асинхронный клиент, который умеет отдавать ответ по мере генерации."""

    def __init__(self, config: Config, client: Any | None = None) -> None:
        self._config = config
        self._client = client or anthropic.AsyncAnthropic(
            api_key=config.anthropic_api_key,
            timeout=config.request_timeout,
            max_retries=2,
        )
        # Отключается автоматически, если API не знает про бету фолбэков.
        self._use_fallbacks = config.refusal_fallback

    @property
    def tools(self) -> list[dict[str, Any]]:
        if not self._config.web_search:
            return []
        return [
            {
                "type": web_search_tool_type(self._config.model),
                "name": "web_search",
                "max_uses": self._config.web_search_max_uses,
            }
        ]

    def _request_kwargs(self, system: str, messages: list[dict[str, Any]]) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self._config.model,
            "max_tokens": self._config.max_tokens,
            "system": [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            "messages": messages,
        }
        if self._config.effort:
            kwargs["output_config"] = {"effort": self._config.effort}
        tools = self.tools
        if tools:
            kwargs["tools"] = tools
        return kwargs

    async def _stream_once(
        self,
        system: str,
        messages: list[dict[str, Any]],
        on_delta: DeltaCallback | None,
    ) -> Any:
        """Один запрос к API. Возвращает финальное сообщение."""
        kwargs = self._request_kwargs(system, messages)
        if self._use_fallbacks:
            streamer = self._client.beta.messages.stream
            kwargs["betas"] = [FALLBACK_BETA]
            kwargs["fallbacks"] = "default"
        else:
            streamer = self._client.messages.stream

        try:
            async with streamer(**kwargs) as stream:
                async for event in stream:
                    if event.type == "text" and on_delta is not None:
                        await on_delta(event.text)
                return await stream.get_final_message()
        except anthropic.BadRequestError as exc:
            if self._use_fallbacks and _looks_like_fallback_rejection(exc):
                logger.warning("Серверные фолбэки недоступны, отключаю их: %s", exc.message)
                self._use_fallbacks = False
                return await self._stream_once(system, messages, on_delta)
            raise

    async def complete(
        self,
        system: str,
        messages: list[dict[str, Any]],
        *,
        on_delta: DeltaCallback | None = None,
    ) -> Reply:
        """Полный ответ модели с учётом пауз серверных инструментов."""
        conversation = list(messages)
        queries: list[str] = []
        sources: list[tuple[str, str]] = []
        chunks: list[str] = []
        input_tokens = 0
        output_tokens = 0

        for _ in range(MAX_PAUSE_RESUMES + 1):
            try:
                final = await self._stream_once(system, conversation, on_delta)
            except Exception as exc:  # noqa: BLE001 — переводим в понятный текст
                logger.exception("Ошибка запроса к модели")
                raise friendly_error(exc) from exc

            usage = getattr(final, "usage", None)
            input_tokens += getattr(usage, "input_tokens", 0) or 0
            output_tokens += getattr(usage, "output_tokens", 0) or 0

            queries.extend(extract_search_queries(final.content))
            sources.extend(extract_sources(final.content))
            chunks.append(collect_text(final.content))

            if final.stop_reason == "refusal":
                return Reply(
                    text=REFUSAL_MESSAGE,
                    stop_reason="refusal",
                    refused=True,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )

            if final.stop_reason == "pause_turn":
                # Серверный инструмент взял паузу — продолжаем ту же реплику.
                conversation = conversation + [
                    {"role": "assistant", "content": _as_params(final.content)}
                ]
                continue

            text = "\n".join(part for part in chunks if part).strip()
            return Reply(
                text=text or EMPTY_MESSAGE,
                stop_reason=final.stop_reason,
                truncated=final.stop_reason == "max_tokens",
                search_queries=_unique(queries),
                sources=_unique(sources),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        text = "\n".join(part for part in chunks if part).strip()
        return Reply(
            text=text or EMPTY_MESSAGE,
            stop_reason="pause_turn",
            truncated=True,
            search_queries=_unique(queries),
            sources=_unique(sources),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )


def _looks_like_fallback_rejection(exc: anthropic.BadRequestError) -> bool:
    message = (getattr(exc, "message", "") or str(exc)).lower()
    return "fallback" in message or "beta" in message


def _unique(items: Iterable[Any]) -> list[Any]:
    seen: set[Any] = set()
    result: list[Any] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _as_params(content: Any) -> list[dict[str, Any]]:
    """Приводит блоки ответа к словарям, пригодным для следующего запроса."""
    params: list[dict[str, Any]] = []
    for block in content or []:
        if isinstance(block, dict):
            params.append(block)
        elif hasattr(block, "model_dump"):
            params.append(block.model_dump(exclude_none=True))
    return params


def _block_type(block: Any) -> str | None:
    if isinstance(block, dict):
        return block.get("type")
    return getattr(block, "type", None)


def _block_get(block: Any, name: str, default: Any = None) -> Any:
    if isinstance(block, dict):
        return block.get(name, default)
    return getattr(block, name, default)


def collect_text(content: Any) -> str:
    """Склеивает текстовые блоки ответа."""
    parts = [
        _block_get(block, "text", "") or ""
        for block in content or []
        if _block_type(block) == "text"
    ]
    return "".join(parts).strip()


def extract_search_queries(content: Any) -> list[str]:
    """Поисковые запросы, которые модель отправила в веб-поиск."""
    queries: list[str] = []
    for block in content or []:
        if _block_type(block) != "server_tool_use":
            continue
        if _block_get(block, "name") != "web_search":
            continue
        payload = _block_get(block, "input") or {}
        query = payload.get("query") if isinstance(payload, dict) else None
        if query:
            queries.append(str(query))
    return queries


def extract_sources(content: Any) -> list[tuple[str, str]]:
    """Ссылки из результатов веб-поиска: (заголовок, url)."""
    sources: list[tuple[str, str]] = []
    for block in content or []:
        if _block_type(block) != "web_search_tool_result":
            continue
        results = _block_get(block, "content")
        if not isinstance(results, list):
            continue  # ошибка инструмента приходит объектом, а не списком
        for item in results:
            url = _block_get(item, "url")
            if not url:
                continue
            title = _block_get(item, "title") or url
            sources.append((str(title), str(url)))
    return sources
