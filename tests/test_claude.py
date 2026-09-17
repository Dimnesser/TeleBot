import anthropic
import pytest

from bot.claude import (
    ClaudeClient,
    ClaudeError,
    REFUSAL_MESSAGE,
    collect_text,
    extract_search_queries,
    extract_sources,
    friendly_error,
)
from bot.config import Config, web_search_tool_type

from fakes import FakeAnthropic, FakeMessage, collector, text_block_obj


def make_config(**overrides) -> Config:
    base = dict(
        telegram_token="t",
        anthropic_api_key="k",
        model="claude-opus-5",
        web_search=False,
        refusal_fallback=False,
    )
    base.update(overrides)
    return Config(**base)


def make_client(turns=None, errors=None, **config_overrides):
    fake = FakeAnthropic(turns=turns, errors=errors)
    return ClaudeClient(make_config(**config_overrides), client=fake), fake


async def test_simple_reply_streams_deltas():
    client, _ = make_client([(FakeMessage([text_block_obj("Привет!")]), ["При", "вет!"])])
    seen: list[str] = []

    reply = await client.complete(
        "system", [{"role": "user", "content": "хай"}], on_delta=collector(seen)
    )

    assert reply.text == "Привет!"
    assert "".join(seen) == "Привет!"
    assert reply.input_tokens == 10 and reply.output_tokens == 20


async def test_refusal_returns_friendly_text():
    client, _ = make_client([(FakeMessage([], stop_reason="refusal"), [])])
    reply = await client.complete("system", [{"role": "user", "content": "..."}])
    assert reply.refused is True
    assert reply.text == REFUSAL_MESSAGE


async def test_pause_turn_is_resumed():
    first = FakeMessage([text_block_obj("Ищу…")], stop_reason="pause_turn")
    second = FakeMessage([text_block_obj("Готово.")], stop_reason="end_turn")
    client, fake = make_client([(first, []), (second, [])])

    reply = await client.complete("system", [{"role": "user", "content": "погода"}])

    assert len(fake.calls) == 2
    assert reply.text == "Ищу…\nГотово."
    assert reply.stop_reason == "end_turn"
    assert fake.calls[1]["messages"][-1]["role"] == "assistant"


async def test_truncated_reply_is_flagged():
    client, _ = make_client([(FakeMessage([text_block_obj("длинно")], stop_reason="max_tokens"), [])])
    reply = await client.complete("system", [{"role": "user", "content": "?"}])
    assert reply.truncated is True


async def test_web_search_tool_is_declared_when_enabled():
    client, fake = make_client([(FakeMessage([text_block_obj("ok")]), [])], web_search=True)
    await client.complete("system", [{"role": "user", "content": "новости"}])
    tools = fake.calls[0]["tools"]
    assert tools[0]["type"] == web_search_tool_type("claude-opus-5")
    assert tools[0]["name"] == "web_search"


async def test_no_tools_when_search_disabled():
    client, fake = make_client([(FakeMessage([text_block_obj("ok")]), [])])
    await client.complete("system", [{"role": "user", "content": "?"}])
    assert "tools" not in fake.calls[0]


async def test_effort_is_passed_for_supported_model():
    client, fake = make_client([(FakeMessage([text_block_obj("ok")]), [])], effort="high")
    await client.complete("system", [{"role": "user", "content": "?"}])
    assert fake.calls[0]["output_config"] == {"effort": "high"}


async def test_system_prompt_is_cached():
    client, fake = make_client([(FakeMessage([text_block_obj("ok")]), [])])
    await client.complete("подсказка", [{"role": "user", "content": "?"}])
    system = fake.calls[0]["system"]
    assert system[0]["text"] == "подсказка"
    assert system[0]["cache_control"] == {"type": "ephemeral"}


async def test_fallbacks_use_beta_endpoint():
    client, fake = make_client(
        [(FakeMessage([text_block_obj("ok")]), [])], refusal_fallback=True
    )
    await client.complete("system", [{"role": "user", "content": "?"}])
    assert fake.calls[0]["beta"] is True
    assert fake.calls[0]["fallbacks"] == "default"


async def test_fallbacks_are_disabled_after_rejection():
    error = anthropic.BadRequestError(
        message="fallbacks is not supported",
        response=_fake_response(400),
        body=None,
    )
    turns = [(FakeMessage([text_block_obj("ok")]), [])]
    fake = FakeAnthropic(turns=turns, errors=[error])
    client = ClaudeClient(make_config(refusal_fallback=True), client=fake)

    reply = await client.complete("system", [{"role": "user", "content": "?"}])

    assert reply.text == "ok"
    assert fake.calls[0]["beta"] is True
    assert fake.calls[1]["beta"] is False


async def test_api_error_becomes_claude_error():
    error = anthropic.NotFoundError(
        message="model not found", response=_fake_response(404), body=None
    )
    client, _ = make_client(errors=[error])
    with pytest.raises(ClaudeError) as info:
        await client.complete("system", [{"role": "user", "content": "?"}])
    assert "модель" in info.value.user_message.lower()


def _fake_response(status: int):
    import httpx2 as httpx

    return httpx.Response(status_code=status, request=httpx.Request("POST", "https://api"))


def test_friendly_error_marks_retryable():
    error = anthropic.APIConnectionError(request=_fake_response(500).request)
    assert friendly_error(error).retryable is True


def test_collect_text_joins_blocks():
    content = [text_block_obj("раз "), {"type": "thinking", "thinking": "..."}, text_block_obj("два")]
    assert collect_text(content) == "раз два"


def test_extract_search_queries():
    content = [
        {"type": "server_tool_use", "name": "web_search", "input": {"query": "курс евро"}},
        {"type": "server_tool_use", "name": "other", "input": {"query": "нет"}},
    ]
    assert extract_search_queries(content) == ["курс евро"]


def test_extract_sources_skips_tool_errors():
    ok = {
        "type": "web_search_tool_result",
        "content": [{"url": "https://a.tld", "title": "А"}],
    }
    failed = {"type": "web_search_tool_result", "content": {"error_code": "max_uses_exceeded"}}
    assert extract_sources([ok, failed]) == [("А", "https://a.tld")]


def test_low_credit_balance_gets_actionable_message():
    error = anthropic.BadRequestError(
        message=(
            "Your credit balance is too low to access the Anthropic API. "
            "Please go to Plans & Billing to upgrade or purchase credits."
        ),
        response=_fake_response(400),
        body=None,
    )
    result = friendly_error(error)
    assert "Пополни баланс" in result.user_message
    assert "credit balance" not in result.user_message


def test_prompt_too_long_suggests_reset():
    error = anthropic.BadRequestError(
        message="prompt is too long: 1200000 tokens > 1000000 maximum",
        response=_fake_response(400),
        body=None,
    )
    assert "/reset" in friendly_error(error).user_message


def test_unknown_bad_request_keeps_original_text():
    error = anthropic.BadRequestError(
        message="something unusual happened",
        response=_fake_response(400),
        body=None,
    )
    assert "something unusual happened" in friendly_error(error).user_message
