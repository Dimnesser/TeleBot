"""Проверка Telegram WebApp initData.

Алгоритм — ровно тот, что описан в официальной документации Telegram
(Validating data received via the Mini App):
  secret_key = HMAC_SHA256(key="WebAppData", msg=bot_token)
  data_check_string = отсортированные по ключу "k=v" через "\n", без hash
  ожидаемый hash = HMAC_SHA256(key=secret_key, msg=data_check_string).hexdigest()
"""
from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl


class InitDataError(ValueError):
    pass


@dataclass(frozen=True)
class WebAppUser:
    tg_id: int
    username: str | None
    first_name: str | None


def _secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def validate_init_data(init_data: str, bot_token: str, *, max_age_seconds: int = 86400) -> WebAppUser:
    """Проверяет подпись initData и возвращает пользователя. Бросает InitDataError."""
    if not init_data:
        raise InitDataError("empty init_data")

    pairs = parse_qsl(init_data, strict_parsing=True)
    data = dict(pairs)
    received_hash = data.pop("hash", None)
    if not received_hash:
        raise InitDataError("missing hash")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(data.items()))
    expected_hash = hmac.new(_secret_key(bot_token), data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        raise InitDataError("signature mismatch")

    auth_date = data.get("auth_date")
    if auth_date and time.time() - int(auth_date) > max_age_seconds:
        raise InitDataError("init_data expired")

    user_raw = data.get("user")
    if not user_raw:
        raise InitDataError("missing user")

    try:
        user_obj = json.loads(user_raw)
        tg_id = int(user_obj["id"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        raise InitDataError("malformed user field") from exc

    return WebAppUser(tg_id=tg_id, username=user_obj.get("username"), first_name=user_obj.get("first_name"))
