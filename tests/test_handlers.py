from types import SimpleNamespace

from bot import handlers
from bot.claude import ClaudeClient, Reply
from bot.config import Config
from bot.history import HistoryStore
from bot.prompts import build_system_prompt
from fakes import FakeAnthropic, FakeMessage, text_block_obj


# --- вспомогательные заглушки Telegram ---------------------------------


class FakeSentMessage:
    def __init__(self, bot, chat_id, text, message_id):
        self.bot = bot
        self.chat_id = chat_id
        self.text = text
        self.message_id = message_id
        self.edits: list[str] = []

    async def edit_text(self, text, **kwargs):
        self.text = text
        self.edits.append(text)
        return self


class FakeBot:
    def __init__(self, username="assistant_bot"):
        self.username = username
        self.sent: list[FakeSentMessage] = []
        self.actions = 0

    async def send_message(self, chat_id, text, **kwargs):
        message = FakeSentMessage(self, chat_id, text, len(self.sent) + 100)
        self.sent.append(message)
        return message

    async def send_chat_action(self, chat_id, action):
        self.actions += 1


class FakeIncoming:
    def __init__(self, chat_id=1, text="вопрос", chat_type="private"):
        self.chat = SimpleNamespace(id=chat_id, type=chat_type)
        self.chat_id = chat_id
        self.message_id = 5
        self.text = text
        self.caption = None
        self.photo = None
        self.document = None
        self.reply_to_message = None
        self.replies: list[str] = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)
        return text


def make_update(message: FakeIncoming) -> SimpleNamespace:
    return SimpleNamespace(
        effective_chat=message.chat,
        effective_message=message,
        effective_user=SimpleNamespace(id=777),
    )


def make_context(bot: FakeBot, runtime) -> SimpleNamespace:
    return SimpleNamespace(
        bot=bot,
        application=SimpleNamespace(bot_data={"runtime": runtime}),
    )


def make_runtime(turns=None, **config_overrides):
    base = dict(
        telegram_token="t",
        api_key="k",
        web_search=False,
        refusal_fallback=False,
        stream_edit_interval=0.0,
    )
    base.update(config_overrides)
    config = Config(**base)
    fake = FakeAnthropic(turns=turns)
    runtime = handlers.BotRuntime(config, ClaudeClient(config, client=fake), HistoryStore())
    return runtime, fake


# --- правила ответа в группах ------------------------------------------


def test_private_chat_always_answered():
    assert handlers.should_answer(FakeIncoming(), "assistant_bot") is True


def test_group_requires_mention():
    message = FakeIncoming(text="привет всем", chat_type="group")
    assert handlers.should_answer(message, "assistant_bot") is False


def test_group_mention_is_answered():
    message = FakeIncoming(text="@assistant_bot помоги", chat_type="group")
    assert handlers.should_answer(message, "assistant_bot") is True


def test_group_reply_to_bot_is_answered():
    message = FakeIncoming(text="а подробнее?", chat_type="group")
    message.reply_to_message = SimpleNamespace(
        from_user=SimpleNamespace(is_bot=True, username="assistant_bot")
    )
    assert handlers.should_answer(message, "assistant_bot") is True


def test_group_reply_to_other_user_is_ignored():
    message = FakeIncoming(text="а подробнее?", chat_type="group")
    message.reply_to_message = SimpleNamespace(
        from_user=SimpleNamespace(is_bot=False, username="vasya")
    )
    assert handlers.should_answer(message, "assistant_bot") is False


def test_strip_mention():
    assert handlers.strip_mention("@assistant_bot   что такое python?", "assistant_bot") == (
        "что такое python?"
    )
    assert handlers.strip_mention("просто текст", None) == "просто текст"


# --- подпись под ответом ------------------------------------------------


def test_footer_lists_sources():
    reply = Reply(text="…", search_queries=["курс"], sources=[("Банк", "https://b.tld")])
    footer = handlers.build_footer(reply)
    assert "[Банк](https://b.tld)" in footer


def test_footer_notes_search_without_sources():
    assert "веб-поиск" in handlers.build_footer(Reply(text="…", search_queries=["q"]))


def test_footer_notes_truncation():
    assert "обрезан" in handlers.build_footer(Reply(text="…", truncated=True))


def test_footer_empty_for_plain_reply():
    assert handlers.build_footer(Reply(text="…")) == ""


# --- сквозной путь текстового сообщения ---------------------------------


async def test_text_message_answers_and_remembers():
    runtime, fake = make_runtime([(FakeMessage([text_block_obj("**Ответ**")]), ["Отв", "ет"])])
    bot = FakeBot()
    message = FakeIncoming(text="как дела?")

    await handlers.on_text(make_update(message), make_context(bot, runtime))

    assert bot.sent, "бот должен отправить сообщение"
    assert "<b>Ответ</b>" in bot.sent[0].text
    history = await runtime.history.get(1)
    assert [m["role"] for m in history] == ["user", "assistant"]
    assert history[0]["content"][0]["text"] == "как дела?"
    assert fake.calls[0]["system"][0]["text"].startswith("Ты — умный универсальный AI-ассистент")


async def test_empty_text_gets_hint():
    runtime, _ = make_runtime()
    bot = FakeBot()
    message = FakeIncoming(text="@assistant_bot", chat_type="private")

    await handlers.on_text(make_update(message), make_context(bot, runtime))

    assert message.replies == [handlers.EMPTY_QUESTION]
    assert not bot.sent


async def test_refusal_is_not_stored_in_history():
    runtime, _ = make_runtime([(FakeMessage([], stop_reason="refusal"), [])])
    bot = FakeBot()

    await handlers.on_text(make_update(FakeIncoming()), make_context(bot, runtime))

    assert await runtime.history.get(1) == []


async def test_api_error_is_reported_to_user():
    import anthropic
    import httpx2 as httpx

    error = anthropic.RateLimitError(
        message="slow down",
        response=httpx.Response(429, request=httpx.Request("POST", "https://api")),
        body=None,
    )
    config = Config(telegram_token="t", web_search=False, refusal_fallback=False)
    fake = FakeAnthropic(errors=[error])
    runtime = handlers.BotRuntime(config, ClaudeClient(config, client=fake), HistoryStore())
    bot = FakeBot()

    await handlers.on_text(make_update(FakeIncoming()), make_context(bot, runtime))

    assert "Слишком много запросов" in bot.sent[0].text
    assert await runtime.history.get(1) == []


async def test_long_answer_is_split_into_messages():
    long_text = "Пункт списка. " * 900
    runtime, _ = make_runtime([(FakeMessage([text_block_obj(long_text)]), [])])
    bot = FakeBot()

    await handlers.on_text(make_update(FakeIncoming()), make_context(bot, runtime))

    assert len(bot.sent) > 1
    assert all(len(message.text) <= 4096 for message in bot.sent)


async def test_denied_user_gets_refusal():
    config = Config(telegram_token="t", allowed_user_ids=frozenset({1}))
    fake = FakeAnthropic()
    runtime = handlers.BotRuntime(config, ClaudeClient(config, client=fake), HistoryStore())
    bot = FakeBot()
    message = FakeIncoming()

    await handlers.on_text(make_update(message), make_context(bot, runtime))

    assert message.replies == [handlers.DENIED_MESSAGE]
    assert not fake.calls


async def test_reset_command_clears_history():
    runtime, _ = make_runtime()
    await runtime.history.append(1, "user", "старое")
    bot = FakeBot()
    message = FakeIncoming()

    await handlers.cmd_reset(make_update(message), make_context(bot, runtime))

    assert await runtime.history.get(1) == []
    assert "очищен" in message.replies[0]


def test_system_prompt_mentions_search_state():
    assert "поиск в интернете сейчас НЕ подключён" in build_system_prompt(web_search_enabled=False)
    assert "доступен веб-поиск" in build_system_prompt(web_search_enabled=True)
