"""Общие типы для всех провайдеров модели."""

from __future__ import annotations

from dataclasses import dataclass, field


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


class ModelError(RuntimeError):
    """Ошибка обращения к модели с текстом, готовым к показу пользователю."""

    def __init__(self, user_message: str, *, retryable: bool = False) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.retryable = retryable


REFUSAL_MESSAGE = (
    "Не могу ответить на этот запрос. Попробуй переформулировать или "
    "спросить о чём-то другом — я рядом."
)
EMPTY_MESSAGE = "Ответ получился пустым. Попробуй переформулировать вопрос."
