"""Тесты глобального обработчика ошибок: глушит «message is not modified»."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import EditMessageText
from aiogram.types import ErrorEvent

from bot.app import handle_message_not_modified


def make_bad_request(text: str) -> TelegramBadRequest:
    method = EditMessageText(chat_id=1, text="x")
    return TelegramBadRequest(method=method, message=text)


def make_event(exception: Exception, callback_query=None) -> ErrorEvent:
    update = SimpleNamespace(callback_query=callback_query)
    return SimpleNamespace(exception=exception, update=update)


async def test_swallows_message_not_modified_and_answers_callback():
    callback_query = SimpleNamespace(answer=AsyncMock())
    event = make_event(
        make_bad_request("Bad Request: message is not modified: specified new message content..."),
        callback_query=callback_query,
    )

    handled = await handle_message_not_modified(event)

    assert handled is True
    callback_query.answer.assert_awaited_once()


async def test_handles_missing_callback_query_gracefully():
    event = make_event(make_bad_request("Bad Request: message is not modified"), callback_query=None)

    handled = await handle_message_not_modified(event)

    assert handled is True  # не падает без callback_query, просто не отвечает


async def test_does_not_swallow_other_bad_request_errors():
    callback_query = SimpleNamespace(answer=AsyncMock())
    event = make_event(make_bad_request("Bad Request: chat not found"), callback_query=callback_query)

    handled = await handle_message_not_modified(event)

    assert handled is False
    callback_query.answer.assert_not_awaited()


async def test_does_not_swallow_non_telegram_errors():
    event = make_event(ValueError("something else"), callback_query=None)

    handled = await handle_message_not_modified(event)

    assert handled is False


async def test_answer_failure_is_also_swallowed():
    callback_query = SimpleNamespace(
        answer=AsyncMock(side_effect=make_bad_request("query is too old"))
    )
    event = make_event(make_bad_request("message is not modified"), callback_query=callback_query)

    handled = await handle_message_not_modified(event)

    assert handled is True
