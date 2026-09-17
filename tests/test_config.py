import pytest

from bot.config import (
    Config,
    ConfigError,
    supports_effort,
    web_search_tool_type,
)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in [
        "TELEGRAM_BOT_TOKEN", "ANTHROPIC_API_KEY", "CLAUDE_MODEL", "CLAUDE_EFFORT",
        "CLAUDE_MAX_TOKENS", "CLAUDE_TIMEOUT_SECONDS", "ENABLE_WEB_SEARCH",
        "WEB_SEARCH_MAX_USES", "ENABLE_REFUSAL_FALLBACK", "HISTORY_TURNS",
        "HISTORY_MAX_CHARS", "HISTORY_FILE", "ALLOWED_USER_IDS",
        "MAX_IMAGE_BYTES", "MAX_DOCUMENT_BYTES", "AI_PROVIDER", "AI_MODEL",
        "AI_BASE_URL", "AI_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
        "GROQ_API_KEY", "OPENROUTER_API_KEY",
    ]:
        monkeypatch.delenv(name, raising=False)


def test_missing_token_is_reported(monkeypatch):
    with pytest.raises(ConfigError, match="TELEGRAM_BOT_TOKEN"):
        Config.from_env()


def test_defaults(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    config = Config.from_env()
    assert config.model == "claude-opus-5"
    assert config.effort == "medium"
    assert config.web_search is True
    assert config.history_path is None
    assert config.is_allowed(999) is True


def test_flags_and_numbers(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("ENABLE_WEB_SEARCH", "false")
    monkeypatch.setenv("CLAUDE_MAX_TOKENS", "2048")
    monkeypatch.setenv("HISTORY_FILE", "data/h.json")
    config = Config.from_env()
    assert config.web_search is False
    assert config.max_tokens == 2048
    assert str(config.history_path) == "data/h.json"


def test_invalid_number(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("CLAUDE_MAX_TOKENS", "много")
    with pytest.raises(ConfigError, match="CLAUDE_MAX_TOKENS"):
        Config.from_env()


def test_invalid_effort(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("CLAUDE_EFFORT", "turbo")
    with pytest.raises(ConfigError, match="CLAUDE_EFFORT"):
        Config.from_env()


def test_effort_dropped_for_model_without_support(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("CLAUDE_MODEL", "claude-haiku-4-5")
    monkeypatch.setenv("CLAUDE_EFFORT", "high")
    assert Config.from_env().effort is None


def test_allowed_user_ids(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("ALLOWED_USER_IDS", "10, 20;30")
    config = Config.from_env()
    assert config.allowed_user_ids == frozenset({10, 20, 30})
    assert config.is_allowed(20) is True
    assert config.is_allowed(40) is False
    assert config.is_allowed(None) is False


def test_bad_user_id(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("ALLOWED_USER_IDS", "не число")
    with pytest.raises(ConfigError, match="ALLOWED_USER_IDS"):
        Config.from_env()


def test_effort_support_matrix():
    assert supports_effort("claude-opus-5") is True
    assert supports_effort("claude-sonnet-5") is True
    assert supports_effort("claude-haiku-4-5") is False


def test_web_search_tool_version():
    assert web_search_tool_type("claude-opus-5") == "web_search_20260209"
    assert web_search_tool_type("claude-haiku-4-5") == "web_search_20250305"


def test_describe_mentions_model():
    config = Config(telegram_token="t", model="claude-opus-5")
    assert "claude-opus-5" in config.describe()


def test_gemini_provider_from_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "g-key")
    config = Config.from_env()
    assert config.provider == "gemini"
    assert config.api_key == "g-key"
    assert config.model == "gemini-2.5-flash"
    assert config.base_url.startswith("https://generativelanguage.googleapis.com")
    assert config.native_anthropic is False


def test_web_search_and_effort_are_off_for_other_providers(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "g")
    monkeypatch.setenv("ENABLE_WEB_SEARCH", "true")
    monkeypatch.setenv("CLAUDE_EFFORT", "high")
    config = Config.from_env()
    assert config.web_search is False
    assert config.effort is None


def test_unknown_provider_is_rejected(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("AI_PROVIDER", "скайнет")
    with pytest.raises(ConfigError, match="AI_PROVIDER"):
        Config.from_env()


def test_openrouter_requires_model(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("AI_PROVIDER", "openrouter")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k")
    with pytest.raises(ConfigError, match="AI_MODEL"):
        Config.from_env()


def test_custom_provider_requires_base_url(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("AI_PROVIDER", "custom")
    monkeypatch.setenv("AI_MODEL", "llama3")
    with pytest.raises(ConfigError, match="AI_BASE_URL"):
        Config.from_env()


def test_ai_model_overrides_default(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("AI_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setenv("AI_MODEL", "своя-модель")
    assert Config.from_env().model == "своя-модель"


def test_generic_key_wins_over_provider_key(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("AI_API_KEY", "общий")
    monkeypatch.setenv("GEMINI_API_KEY", "частный")
    assert Config.from_env().api_key == "общий"


def test_describe_mentions_provider():
    from bot.config import PROVIDERS

    config = Config(telegram_token="t", provider="gemini")
    assert PROVIDERS["gemini"].label in config.describe()


def test_build_client_picks_provider():
    from bot.claude import ClaudeClient
    from bot.model_client import build_client
    from bot.openai_compat import OpenAICompatClient
    from bot.config import PROVIDERS

    anthropic_client = build_client(Config(telegram_token="t", api_key="k"))
    assert isinstance(anthropic_client, ClaudeClient)

    other = build_client(
        Config(
            telegram_token="t",
            api_key="k",
            provider="gemini",
            base_url=PROVIDERS["gemini"].base_url,
            model="gemini-2.5-flash",
        )
    )
    assert isinstance(other, OpenAICompatClient)


def test_claude_model_does_not_leak_into_other_providers(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("CLAUDE_MODEL", "claude-opus-5")
    monkeypatch.setenv("AI_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    assert Config.from_env().model == "gemini-2.5-flash"


def test_claude_model_still_works_for_anthropic(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:abc")
    monkeypatch.setenv("CLAUDE_MODEL", "claude-sonnet-5")
    assert Config.from_env().model == "claude-sonnet-5"
