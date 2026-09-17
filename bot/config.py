"""Конфигурация бота: читается из переменных окружения."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_MODEL = "claude-opus-5"


@dataclass(frozen=True)
class Provider:
    """Описание источника модели."""

    name: str
    label: str
    key_env: tuple[str, ...]
    base_url: str | None = None
    default_model: str | None = None
    console_url: str = ""
    free_tier: bool = False

    @property
    def native_anthropic(self) -> bool:
        return self.name == "anthropic"


PROVIDERS: dict[str, Provider] = {
    "anthropic": Provider(
        name="anthropic",
        label="Anthropic (Claude)",
        key_env=("ANTHROPIC_API_KEY",),
        default_model=DEFAULT_MODEL,
        console_url="https://console.anthropic.com",
    ),
    "gemini": Provider(
        name="gemini",
        label="Google Gemini",
        key_env=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        default_model="gemini-2.5-flash",
        console_url="https://aistudio.google.com/apikey",
        free_tier=True,
    ),
    "groq": Provider(
        name="groq",
        label="Groq",
        key_env=("GROQ_API_KEY",),
        base_url="https://api.groq.com/openai/v1",
        default_model="llama-3.3-70b-versatile",
        console_url="https://console.groq.com/keys",
        free_tier=True,
    ),
    "openrouter": Provider(
        name="openrouter",
        label="OpenRouter",
        key_env=("OPENROUTER_API_KEY",),
        base_url="https://openrouter.ai/api/v1",
        default_model=None,  # список моделей меняется, задаётся через AI_MODEL
        console_url="https://openrouter.ai/keys",
        free_tier=True,
    ),
    "openai": Provider(
        name="openai",
        label="OpenAI",
        key_env=("OPENAI_API_KEY",),
        base_url="https://api.openai.com/v1",
        default_model="gpt-4o-mini",
        console_url="https://platform.openai.com/api-keys",
    ),
    "custom": Provider(
        name="custom",
        label="Свой сервер, совместимый с OpenAI",
        key_env=("AI_API_KEY",),
        base_url=None,  # берётся из AI_BASE_URL
        default_model=None,
    ),
}

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


# По виду ключа почти всегда понятно, чей он. Порядок важен: более
# специфичные образцы идут раньше общего "sk-".
KEY_SIGNATURES: tuple[tuple[str, str], ...] = (
    ("sk-ant-", "anthropic"),
    ("sk-or-", "openrouter"),
    ("gsk_", "groq"),
    ("AIza", "gemini"),
    ("sk-proj-", "openai"),
    ("sk-", "openai"),
)


def detect_provider(api_key: str) -> str | None:
    """Определяет провайдера по формату ключа. None, если не узнали."""
    key = (api_key or "").strip()
    for prefix, provider in KEY_SIGNATURES:
        if key.startswith(prefix):
            return provider
    return None


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
    api_key: str | None = None
    provider: str = "anthropic"
    base_url: str | None = None
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

    @property
    def provider_info(self) -> Provider:
        return PROVIDERS.get(self.provider, PROVIDERS["anthropic"])

    @property
    def native_anthropic(self) -> bool:
        return self.provider_info.native_anthropic

    @classmethod
    def from_env(cls) -> "Config":
        token = (os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
        if not token:
            raise ConfigError(
                "Не задан TELEGRAM_BOT_TOKEN. Получите токен у @BotFather "
                "и добавьте его в окружение или .env"
            )

        provider_name = (os.getenv("AI_PROVIDER") or "anthropic").strip().lower()
        if provider_name not in PROVIDERS:
            raise ConfigError(
                f"Неизвестный AI_PROVIDER: {provider_name}. "
                f"Доступны: {', '.join(sorted(PROVIDERS))}"
            )
        provider = PROVIDERS[provider_name]

        base_url = (os.getenv("AI_BASE_URL") or "").strip() or provider.base_url
        if not provider.native_anthropic and not base_url:
            raise ConfigError(
                f"Для AI_PROVIDER={provider_name} нужно указать AI_BASE_URL "
                "(адрес сервера, совместимого с OpenAI)"
            )

        # CLAUDE_MODEL относится только к Anthropic: иначе значение из шаблона
        # .env перебивало бы модель выбранного провайдера.
        candidates = [os.getenv("AI_MODEL")]
        if provider.native_anthropic:
            candidates.append(os.getenv("CLAUDE_MODEL"))
        candidates.append(provider.default_model)
        model = next((c.strip() for c in candidates if c and c.strip()), "")
        if not model:
            raise ConfigError(
                f"Для AI_PROVIDER={provider_name} нужно указать модель в AI_MODEL. "
                f"Список моделей: {provider.console_url or 'в панели провайдера'}"
            )

        api_key = ""
        for name in ("AI_API_KEY", *provider.key_env):
            api_key = (os.getenv(name) or "").strip()
            if api_key:
                break

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
        if effort is not None and (
            not provider.native_anthropic or not supports_effort(model)
        ):
            effort = None

        history_raw = (os.getenv("HISTORY_FILE") or "").strip()

        return cls(
            telegram_token=token,
            api_key=api_key or None,
            provider=provider_name,
            base_url=base_url,
            model=model,
            effort=effort,
            max_tokens=_env_int("CLAUDE_MAX_TOKENS", 8000, minimum=256),
            request_timeout=float(_env_int("CLAUDE_TIMEOUT_SECONDS", 180, minimum=10)),
            web_search=_env_flag("ENABLE_WEB_SEARCH", True) and provider.native_anthropic,
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
            f"Провайдер: <code>{self.provider_info.label}</code>",
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
