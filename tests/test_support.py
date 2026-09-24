"""Поддержка: сообщение игрока уходит админам, реплай админа — игроку."""
from __future__ import annotations

from types import SimpleNamespace

import dataclasses

import bot.config as config_module
from bot.services import support_service
from bot.handlers import support as support_module
from bot.states.support import Support


def _patch_config(monkeypatch) -> None:
    cfg = dataclasses.replace(config_module.config, admin_chat_id=-1001, admin_ids=[42])
    monkeypatch.setattr(config_module, "config", cfg)
    monkeypatch.setattr(support_service, "config", cfg)


class FakeBot:
    id = 1

    def __init__(self):
        self.sent: list[tuple[int, str]] = []
        self._id = 100

    async def send_message(self, chat_id, text, **kwargs):
        self._id += 1
        self.sent.append((chat_id, text))
        return SimpleNamespace(message_id=self._id)


class FakeState:
    def __init__(self, state=None):
        self.state = state

    async def get_state(self):
        return self.state

    async def set_state(self, state):
        self.state = state.state if hasattr(state, "state") else state

    async def clear(self):
        self.state = None


class FakeMessage:
    def __init__(self, bot, chat_id, from_id, text, reply_to=None, chat_type="private"):
        self.bot = bot
        self.chat = SimpleNamespace(id=chat_id, type=chat_type)
        self.from_user = SimpleNamespace(id=from_id, username="player", first_name="P")
        self.text = text
        self.reply_to_message = reply_to
        self.answers: list[str] = []
        self.replies: list[str] = []
        self.copies: list[int] = []

    async def copy_to(self, chat_id, **kwargs):
        self.copies.append(chat_id)
        self.bot._id += 1
        return SimpleNamespace(message_id=self.bot._id)

    async def answer(self, text, **kwargs):
        self.answers.append(text)

    async def reply(self, text, **kwargs):
        self.replies.append(text)


async def test_player_message_relayed_and_admin_reply_delivered(in_memory_db, monkeypatch) -> None:
    monkeypatch.setattr(support_module, "async_session", in_memory_db)
    _patch_config(monkeypatch)
    support_module._last_sent.clear()
    bot = FakeBot()

    msg = FakeMessage(bot, 777, 777, "не пришёл трейд")
    state = FakeState()
    await support_module.player_message(msg, state)
    assert msg.copies == [-1001] and "Поддержка" in bot.sent[0][1] and "777" in bot.sent[0][1]
    assert state.state == Support.chatting.state and "передано" in msg.answers[-1]
    header_id = 101

    # админ отвечает реплаем на шапку в админ-чате
    admin_msg = FakeMessage(bot, -1001, 42, "трейд кинули, проверь", reply_to=SimpleNamespace(message_id=header_id),
                            chat_type="supergroup")
    await support_module.admin_reply(admin_msg, FakeState())
    assert bot.sent[-1] == (777, "💬 <b>Поддержка:</b>\nтрейд кинули, проверь")
    assert admin_msg.replies == ["✅ Ответ отправлен игроку"]

    # реплай на постороннее сообщение в админ-чате — игнор
    other = FakeMessage(bot, -1001, 42, "ок", reply_to=SimpleNamespace(message_id=9999), chat_type="supergroup")
    n = len(bot.sent)
    await support_module.admin_reply(other, FakeState())
    assert len(bot.sent) == n and other.replies == []


async def test_flood_guard_and_admin_private_ignored(in_memory_db, monkeypatch) -> None:
    monkeypatch.setattr(support_module, "async_session", in_memory_db)
    _patch_config(monkeypatch)
    support_module._last_sent.clear()
    bot = FakeBot()
    first, second = FakeMessage(bot, 5, 5, "a"), FakeMessage(bot, 5, 5, "b")
    await support_module.player_message(first, FakeState())
    await support_module.player_message(second, FakeState())
    assert first.copies == [-1001] and second.copies == [] and "Не так быстро" in second.answers[-1]

    admin = FakeMessage(bot, 42, 42, "привет")
    await support_module.player_message(admin, FakeState())
    assert admin.copies == [] and admin.answers == []


async def test_standalone_support_bot_goes_to_admin_dms(in_memory_db, monkeypatch) -> None:
    """Отдельный бот поддержки шлёт обращения админам в личку, даже если есть админ-чат."""
    monkeypatch.setattr(support_module, "async_session", in_memory_db)
    _patch_config(monkeypatch)
    support_module._last_sent.clear()
    bot = FakeBot()
    bot.id = 2
    msg = FakeMessage(bot, 777, 777, "помогите")
    await support_module.player_message(msg, FakeState(), standalone=True)
    assert msg.copies == [42]
    # реплай админа в личке бота поддержки доходит игроку
    reply = FakeMessage(bot, 42, 42, "уже смотрим", reply_to=SimpleNamespace(message_id=101))
    await support_module.admin_reply(reply, FakeState(), standalone=True)
    assert bot.sent[-1] == (777, "💬 <b>Поддержка:</b>\nуже смотрим")
    # тот же message_id у другого бота — не наш реплай
    other_bot = FakeBot()
    stray = FakeMessage(other_bot, 42, 42, "?", reply_to=SimpleNamespace(message_id=101))
    await support_module.admin_reply(stray, FakeState())
    assert other_bot.sent == [] and stray.replies == []

