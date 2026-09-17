import openai
import pytest

from bot.config import Config, PROVIDERS
from bot.openai_compat import (
    OpenAICompatClient,
    friendly_error,
    to_openai_messages,
)
from bot.types import EMPTY_MESSAGE, ModelError, REFUSAL_MESSAGE
from fakes import collector


# --- перевод формата сообщений -----------------------------------------


def test_system_prompt_becomes_first_message():
    result = to_openai_messages("будь полезным", [])
    assert result == [{"role": "system", "content": "будь полезным"}]


def test_plain_text_turns():
    history = [
        {"role": "user", "content": [{"type": "text", "text": "привет"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "здравствуй"}]},
    ]
    result = to_openai_messages("s", history)
    assert result[1] == {"role": "user", "content": "привет"}
    assert result[2] == {"role": "assistant", "content": "здравствуй"}


def test_image_becomes_data_url():
    history = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png", "data": "QUJD"},
                },
                {"type": "text", "text": "что тут?"},
            ],
        }
    ]
    parts = to_openai_messages("s", history)[1]["content"]
    assert parts[0]["image_url"]["url"] == "data:image/png;base64,QUJD"
    assert parts[1] == {"type": "text", "text": "что тут?"}


def test_assistant_images_are_flattened_to_text():
    history = [
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "вот"},
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "x"}},
            ],
        }
    ]
    assert to_openai_messages("s", history)[1] == {"role": "assistant", "content": "вот"}


def test_string_content_passes_through():
    assert to_openai_messages("s", [{"role": "user", "content": "текст"}])[1] == {
        "role": "user",
        "content": "текст",
    }


def test_empty_blocks_are_skipped():
    assert to_openai_messages("s", [{"role": "user", "content": []}]) == [
        {"role": "system", "content": "s"}
    ]


# --- потоковый ответ ----------------------------------------------------


class FakeDelta:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content=None, finish_reason=None):
        self.delta = FakeDelta(content)
        self.finish_reason = finish_reason


class FakeUsage:
    def __init__(self, prompt_tokens=7, completion_tokens=3):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class FakeChunk:
    def __init__(self, content=None, finish_reason=None, usage=None):
        self.choices = [FakeChoice(content, finish_reason)] if content or finish_reason else []
        self.usage = usage


class FakeCompletions:
    def __init__(self, owner):
        self._owner = owner

    async def create(self, **kwargs):
        self._owner.calls.append(kwargs)
        if self._owner.error is not None:
            raise self._owner.error

        async def generator():
            for chunk in self._owner.chunks:
                yield chunk

        return generator()


class FakeOpenAI:
    def __init__(self, chunks=None, error=None):
        self.chunks = list(chunks or [])
        self.error = error
        self.calls = []
        self.chat = type("Chat", (), {"completions": FakeCompletions(self)})()


def make_config(**overrides) -> Config:
    base = dict(
        telegram_token="t",
        api_key="k",
        provider="gemini",
        base_url=PROVIDERS["gemini"].base_url,
        model="gemini-2.5-flash",
        web_search=False,
    )
    base.update(overrides)
    return Config(**base)


async def test_streaming_reply():
    fake = FakeOpenAI([
        FakeChunk("При"),
        FakeChunk("вет"),
        FakeChunk(finish_reason="stop"),
        FakeChunk(usage=FakeUsage()),
    ])
    client = OpenAICompatClient(make_config(), client=fake)
    seen: list[str] = []

    reply = await client.complete("s", [{"role": "user", "content": "хай"}], on_delta=collector(seen))

    assert reply.text == "Привет"
    assert "".join(seen) == "Привет"
    assert reply.input_tokens == 7 and reply.output_tokens == 3
    assert fake.calls[0]["model"] == "gemini-2.5-flash"
    assert fake.calls[0]["stream"] is True


async def test_length_finish_is_truncated():
    fake = FakeOpenAI([FakeChunk("долгий"), FakeChunk(finish_reason="length")])
    reply = await OpenAICompatClient(make_config(), client=fake).complete("s", [])
    assert reply.truncated is True


async def test_content_filter_becomes_refusal():
    fake = FakeOpenAI([FakeChunk(finish_reason="content_filter")])
    reply = await OpenAICompatClient(make_config(), client=fake).complete("s", [])
    assert reply.refused is True
    assert reply.text == REFUSAL_MESSAGE


async def test_empty_stream_gets_placeholder():
    reply = await OpenAICompatClient(make_config(), client=FakeOpenAI([])).complete("s", [])
    assert reply.text == EMPTY_MESSAGE


async def test_no_tools_declared():
    assert OpenAICompatClient(make_config(), client=FakeOpenAI()).tools == []


async def test_errors_are_translated():
    import httpx

    error = openai.RateLimitError(
        message="rate limit",
        response=httpx.Response(429, request=httpx.Request("POST", "https://api")),
        body=None,
    )
    client = OpenAICompatClient(make_config(), client=FakeOpenAI(error=error))
    with pytest.raises(ModelError) as info:
        await client.complete("s", [{"role": "user", "content": "?"}])
    assert "лимит" in info.value.user_message.lower()
    assert info.value.retryable is True


def test_missing_model_message():
    import httpx

    error = openai.NotFoundError(
        message="model not found",
        response=httpx.Response(404, request=httpx.Request("POST", "https://api")),
        body=None,
    )
    assert "AI_MODEL" in friendly_error(error).user_message


def test_quota_error_is_explained():
    import httpx

    error = openai.APIStatusError(
        message="insufficient_quota: you exceeded your quota",
        response=httpx.Response(400, request=httpx.Request("POST", "https://api")),
        body=None,
    )
    assert "квота" in friendly_error(error).user_message.lower()
