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
        "MAX_IMAGE_BYTES", "MAX_DOCUMENT_BYTES",
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
