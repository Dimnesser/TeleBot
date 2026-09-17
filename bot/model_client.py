"""Выбор клиента модели по настройке AI_PROVIDER."""

from __future__ import annotations

from typing import Any

from .config import Config


def build_client(config: Config) -> Any:
    """Возвращает клиента Anthropic или OpenAI-совместимого провайдера."""
    if config.native_anthropic:
        from .claude import ClaudeClient

        return ClaudeClient(config)

    from .openai_compat import OpenAICompatClient

    return OpenAICompatClient(config)
