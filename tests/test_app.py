import os

from bot.app import build_application, load_dotenv
from bot.config import Config


def test_load_dotenv_does_not_override_existing(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# комментарий\nTELEGRAM_BOT_TOKEN=\"из файла\"\nCLAUDE_MODEL=claude-opus-5\nBROKEN LINE\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "из окружения")
    monkeypatch.delenv("CLAUDE_MODEL", raising=False)

    load_dotenv(env_file)

    assert os.environ["TELEGRAM_BOT_TOKEN"] == "из окружения"
    assert os.environ["CLAUDE_MODEL"] == "claude-opus-5"


def test_load_dotenv_ignores_missing_file(tmp_path):
    load_dotenv(tmp_path / "нет-такого.env")


def test_application_builds_with_all_handlers(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    application = build_application(Config(telegram_token="123456:TEST", anthropic_api_key="k"))

    assert application.bot_data["runtime"].config.model == "claude-opus-5"
    registered = application.handlers[0]
    assert len(registered) >= 7
    assert application.error_handlers
