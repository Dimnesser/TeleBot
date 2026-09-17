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
    application = build_application(Config(telegram_token="123456:TEST", api_key="k"))

    assert application.bot_data["runtime"].config.model == "claude-opus-5"
    registered = application.handlers[0]
    assert len(registered) >= 7
    assert application.error_handlers


def test_selfcheck_history_probe(tmp_path):
    from bot.selfcheck import check_history

    config = Config(telegram_token="t", history_path=tmp_path / "sub" / "history.json")
    result = check_history(config)
    assert result.ok is True
    assert not (tmp_path / "sub" / ".write-probe").exists()


def test_selfcheck_history_reports_unwritable(tmp_path):
    from bot.selfcheck import check_history

    blocker = tmp_path / "file"
    blocker.write_text("не каталог", encoding="utf-8")
    config = Config(telegram_token="t", history_path=blocker / "history.json")
    assert check_history(config).ok is False


def test_selfcheck_memory_only_history():
    from bot.selfcheck import check_history

    result = check_history(Config(telegram_token="t"))
    assert result.ok is True
    assert "памяти" in result.title


async def test_selfcheck_reports_bad_anthropic_key(monkeypatch):
    import anthropic
    import httpx2 as httpx

    from bot.selfcheck import check_model

    class Boom:
        def __init__(self, **kwargs):
            self.messages = self

        async def create(self, **kwargs):
            raise anthropic.AuthenticationError(
                message="invalid key",
                response=httpx.Response(401, request=httpx.Request("POST", "https://api")),
                body=None,
            )

    monkeypatch.setattr(anthropic, "AsyncAnthropic", Boom)
    result = await check_model(Config(telegram_token="t", api_key="k"))
    assert result.ok is False
    assert "недействителен" in result.detail


async def test_selfcheck_reports_missing_key():
    from bot.selfcheck import check_model

    result = await check_model(Config(telegram_token="t", provider="gemini"))
    assert result.ok is False
    assert "GEMINI_API_KEY" in result.detail
