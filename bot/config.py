"""Конфигурация бота: читается из переменных окружения."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_MODEL = "claude-opus-5"

# Модели, которые принимают output_config.effort.
_EFFORT_MODELS = (
    "claude-fable-5",
    "claude-mythos-5",
    "claude-opus-5",
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-sonnet-5",
    "claude-sonnet-4-6",
)

# Модели с веб-поиском новой ревизии (динамическая фильтрация).
_MODERN_SEARCH_MODELS = (
    "claude-fable-5",
    "claude-mythos-5",
    "claude-opus-5",
    "claude-opus-4-8",
    "claude-opus-4-7",
    "claude-opus-4-6",
    "claude-sonnet-5",
    "claude-sonnet-4-6",
)

VALID_EFFORTS = ("low", "medium", "high", "xhigh", "max")


class ConfigError(RuntimeError):
    """Некорректная или неполная конфигурация."""


def supports_effort(model: str) -> bool:
    """True, если модель принимает output_config.effort."""
    return model.startswith(_EFFORT_MODELS)


def web_search_tool_type(model: str) -> str:
    """Версия серверного инструмента веб-поиска для конкретной модели."""
    if model.startswith(_MODERN_SEARCH_MODELS):
        return "web_search_20260209"
    return "web_search_20250305"


def _env_flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "да"}


def _env_int(name: str, default: int, *, minimum: int | None = None) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} должен быть целым числом, получено: {raw!r}") from exc
    if minimum is not None and value < minimum:
        raise ConfigError(f"{name} не может быть меньше {minimum}, получено: {value}")
    return value


def _env_ids(name: str) -> frozenset[int]:
    raw = os.getenv(name, "")
    ids: set[int] = set()
    for chunk in raw.replace(";", ",").split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            ids.add(int(chunk))
        except ValueError as exc:
            raise ConfigError(f"{name}: {chunk!r} не является Telegram ID") from exc
    return frozenset(ids)


@dataclass(frozen=True)
class Config:
    """Все настройки рантайма в одном объекте."""

    telegram_token: str
    anthropic_api_key: str | None = None
    model: str = DEFAULT_MODEL
    effort: str | None = "medium"
    max_tokens: int = 8000
    request_timeout: float = 180.0

    web_search: bool = True
    web_search_max_uses: int = 5
    refusal_fallback: bool = True

    history_turns: int = 20
    history_max_chars: int = 40_000
    history_path: Path | None = None

    allowed_user_ids: frozenset[int] = field(default_factory=frozenset)
    stream_edit_interval: float = 1.5
    max_image_bytes: int = 5 * 1024 * 1024
    max_document_bytes: int = 200 * 1024

    @classmethod
    def from_env(cls) -> "Config":
        token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
        if not token:
            raise ConfigError(
                "Не задан TELEGRAM_BOT_TOKEN. Получите токен у @BotFather "
                "и добавьте его в окружение или .env"
            )

        model = (os.getenv("CLAUDE_MODEL") or DEFAULT_MODEL).strip()

        effort_raw = os.getenv("CLAUDE_EFFORT")
        effort: str | None
        if effort_raw is None:
            effort = "medium"
        elif effort_raw.strip() == "" or effort_raw.strip().lower() == "none":
            effort = None
        else:
            effort = effort_raw.strip().lower()
            if effort not in VALID_EFFORTS:
                raise ConfigError(
                    f"CLAUDE_EFFORT должен быть одним из {', '.join(VALID_EFFORTS)}"
                )
        if effort is not None and not supports_effort(model):
            effort = None

        history_raw = (os.getenv("HISTORY_FILE") or "").strip()

        return cls(
            telegram_token=token,
            anthropic_api_key=(os.getenv("ANTHROPIC_API_KEY") or "").strip() or None,
            model=model,
            effort=effort,
            max_tokens=_env_int("CLAUDE_MAX_TOKENS", 8000, minimum=256),
            request_timeout=float(_env_int("CLAUDE_TIMEOUT_SECONDS", 180, minimum=10)),
            web_search=_env_flag("ENABLE_WEB_SEARCH", True),
            web_search_max_uses=_env_int("WEB_SEARCH_MAX_USES", 5, minimum=1),
            refusal_fallback=_env_flag("ENABLE_REFUSAL_FALLBACK", True),
            history_turns=_env_int("HISTORY_TURNS", 20, minimum=2),
            history_max_chars=_env_int("HISTORY_MAX_CHARS", 40_000, minimum=1000),
            history_path=Path(history_raw) if history_raw else None,
            allowed_user_ids=_env_ids("ALLOWED_USER_IDS"),
            max_image_bytes=_env_int("MAX_IMAGE_BYTES", 5 * 1024 * 1024, minimum=1024),
            max_document_bytes=_env_int("MAX_DOCUMENT_BYTES", 200 * 1024, minimum=1024),
        )

    def is_allowed(self, user_id: int | None) -> bool:
        """Пустой список ALLOWED_USER_IDS означает «доступ для всех»."""
        if not self.allowed_user_ids:
            return True
        return user_id is not None and user_id in self.allowed_user_ids

    def describe(self) -> str:
        """Короткая сводка настроек для команды /about."""
        lines = [
            f"Модель: <code>{self.model}</code>",
            f"Глубина рассуждений: <code>{self.effort or 'по умолчанию'}</code>",
            f"Лимит ответа: <code>{self.max_tokens}</code> токенов",
            f"Веб-поиск: <code>{'включён' if self.web_search else 'выключен'}</code>",
            f"Память диалога: <code>{self.history_turns}</code> сообщений",
            f"История на диске: <code>{'да' if self.history_path else 'нет'}</code>",
        ]
        if self.allowed_user_ids:
            lines.append(f"Доступ ограничен: <code>{len(self.allowed_user_ids)}</code> пользователей")
        return "\n".join(lines)
