"""Настройки, которые админ меняет из Mini App (хранятся в app_meta).

  * required_channel — канал обязательной подписки для бесплатного кейса
    (@username или ссылка t.me/...; пусто — подписка не нужна);
  * free_case_cooldown_hours — раз во сколько часов бесплатный кейс;
  * support_url — кнопка «Поддержка» в приветствии (@username или ссылка).
Кнопка «Новости» в приветствии ведёт на канал обязательной подписки.
"""
from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import AppMeta

REQUIRED_CHANNEL = "required_channel"
FREE_CASE_COOLDOWN_HOURS = "free_case_cooldown_hours"
SUPPORT_URL = "support_url"
SUPPORT_BOT_TOKEN = "support_bot_token"
UI_DESIGN = "ui_design"  # v3 (по умолчанию) | v2 «Neon Glass» | classic (самый первый)
UI_DESIGNS = ("v3", "v2", "classic")
SUPPORT_BOT_USERNAME = "support_bot_username"
UPGRADER_RTP = "upgrader_rtp"  # отдача апгрейдера, % (см. upgrader_service)
DEFAULT_FREE_CASE_COOLDOWN_HOURS = 12

# Статусы getChatMember, при которых пользователь считается подписанным.
SUBSCRIBED_STATUSES = {"creator", "administrator", "member"}


async def get_setting(session: AsyncSession, key: str) -> str | None:
    return (await session.execute(select(AppMeta.value).where(AppMeta.key == key))).scalar_one_or_none()


async def set_setting(session: AsyncSession, key: str, value: str | None) -> None:
    row = await session.get(AppMeta, key)
    if value is None or value == "":
        if row is not None:
            await session.delete(row)
    elif row is None:
        session.add(AppMeta(key=key, value=value))
    else:
        row.value = value
    await session.commit()


def normalize_channel(raw: str) -> str | None:
    """«@name», «name», «t.me/name», «https://t.me/name» → «@name». Пусто → None."""
    raw = (raw or "").strip()
    if not raw:
        return None
    m = re.fullmatch(r"(?:https?://)?(?:t\.me|telegram\.me)/([A-Za-z0-9_]{4,64})/?", raw)
    name = m.group(1) if m else raw.lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9_]{4,64}", name):
        raise ValueError("bad_channel")
    return "@" + name


def normalize_link(raw: str) -> str | None:
    """«@name» / «t.me/name» / https-ссылка → https-ссылка. Пусто → None."""
    raw = (raw or "").strip()
    if not raw:
        return None
    if re.fullmatch(r"https://\S+", raw):
        return raw
    return "https://t.me/" + normalize_channel(raw).lstrip("@")


def channel_url(channel: str | None) -> str | None:
    return f"https://t.me/{channel.lstrip('@')}" if channel else None


async def required_channel(session: AsyncSession) -> str | None:
    return await get_setting(session, REQUIRED_CHANNEL)


async def free_case_cooldown_hours(session: AsyncSession) -> float:
    raw = await get_setting(session, FREE_CASE_COOLDOWN_HOURS)
    try:
        return float(raw) if raw else DEFAULT_FREE_CASE_COOLDOWN_HOURS
    except ValueError:
        return DEFAULT_FREE_CASE_COOLDOWN_HOURS


async def is_subscribed(bot, channel: str, tg_id: int) -> bool:
    """Проверка подписки через getChatMember. Бот должен быть админом канала;
    если Telegram вернул ошибку (бот не в канале, канал не найден) — считаем,
    что подписки нет, чтобы не раздавать кейсы в обход."""
    try:
        member = await bot.get_chat_member(channel, tg_id)
    except Exception:  # noqa: BLE001 — любая ошибка Telegram API = не подтверждено
        return False
    status = getattr(member.status, "value", member.status)
    if status == "restricted":
        return bool(getattr(member, "is_member", False))
    return status in SUBSCRIBED_STATUSES


async def ui_design(session: AsyncSession) -> str:
    value = await get_setting(session, UI_DESIGN)
    return value if value in UI_DESIGNS else "v3"
