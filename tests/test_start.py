"""/start: баннер-приветствие с кнопками «Играть!», «Новости», «Поддержка»."""
from __future__ import annotations

from types import SimpleNamespace

import pytest

from bot.handlers import start as start_module
from bot.keyboards.main_menu import welcome_keyboard
from bot.services import settings_service


class FakeState:
    async def clear(self):
        pass


class FakeMessage:
    def __init__(self, text: str):
        self.text = text
        self.from_user = SimpleNamespace(id=5550001, username="newbie", first_name="New")
        self.sent: list[dict] = []

    async def answer_photo(self, photo, caption=None, reply_markup=None):
        self.sent.append({"photo": photo, "caption": caption, "markup": reply_markup})


def _buttons(markup):
    return [(b.text, b.url) for row in markup.inline_keyboard for b in row]


async def test_start_sends_banner_with_news_and_support(in_memory_db, monkeypatch) -> None:
    monkeypatch.setattr(start_module, "async_session", in_memory_db)
    async with in_memory_db() as session:
        await settings_service.set_setting(session, settings_service.REQUIRED_CHANNEL, "@braincore_news")
        await settings_service.set_setting(session, settings_service.SUPPORT_URL, "https://t.me/braincore_help")

    message = FakeMessage("/start")
    await start_module.handle_start(message, FakeState())

    (sent,) = message.sent
    assert sent["photo"].path == start_module.WELCOME_BANNER and start_module.WELCOME_BANNER.exists()
    assert "Добро пожаловать в <b>BrainCore</b>" in sent["caption"] and "<blockquote>" in sent["caption"]
    assert ("Новости", "https://t.me/braincore_news") in _buttons(sent["markup"])
    assert ("Поддержка", "https://t.me/braincore_help") in _buttons(sent["markup"])


def test_welcome_keyboard_skips_unset_links() -> None:
    assert [t for t, _ in _buttons(welcome_keyboard(None, None))] in ([], ["🚀 Играть!"])


@pytest.mark.parametrize("raw, url", [
    ("@braincore_help", "https://t.me/braincore_help"),
    ("t.me/braincore_help", "https://t.me/braincore_help"),
    ("https://example.com/help", "https://example.com/help"),
    ("", None),
])
def test_normalize_link(raw, url) -> None:
    assert settings_service.normalize_link(raw) == url
