"""Тесты проверки Telegram WebApp initData (webapp/auth.py)."""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from webapp.auth import InitDataError, validate_init_data

BOT_TOKEN = "123456:FAKE_TOKEN_FOR_TEST"


def _build_init_data(tg_id: int, *, username: str = "tester", first_name: str = "Test", auth_date: int | None = None) -> str:
    user = json.dumps({"id": tg_id, "username": username, "first_name": first_name})
    data = {"auth_date": str(auth_date if auth_date is not None else int(time.time())), "user": user, "query_id": "AAABBBCCC"}
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


def test_valid_init_data_parses_correct_user() -> None:
    init_data = _build_init_data(999111, username="dimnesser")
    user = validate_init_data(init_data, BOT_TOKEN)
    assert user.tg_id == 999111
    assert user.username == "dimnesser"


def test_tampered_payload_is_rejected() -> None:
    init_data = _build_init_data(999111, first_name="Test")
    tampered = init_data.replace("Test", "Evil")
    with pytest.raises(InitDataError):
        validate_init_data(tampered, BOT_TOKEN)


def test_wrong_bot_token_is_rejected() -> None:
    init_data = _build_init_data(999111)
    with pytest.raises(InitDataError):
        validate_init_data(init_data, "999999:OTHER_TOKEN")


def test_empty_init_data_is_rejected() -> None:
    with pytest.raises(InitDataError):
        validate_init_data("", BOT_TOKEN)


def test_expired_init_data_is_rejected() -> None:
    old_init_data = _build_init_data(999111, auth_date=int(time.time()) - 200_000)
    with pytest.raises(InitDataError):
        validate_init_data(old_init_data, BOT_TOKEN, max_age_seconds=86400)
