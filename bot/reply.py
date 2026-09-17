"""Отправка ответа в Telegram: индикатор набора и постепенное обновление."""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import time
from html import unescape

from telegram import Bot, Message
from telegram.constants import ChatAction
from telegram.error import BadRequest, Forbidden, TelegramError

from .telegram_format import TELEGRAM_LIMIT, render, render_chunks

logger = logging.getLogger(__name__)

THINKING_TEXT = "⏳ Думаю…"
PREVIEW_LIMIT = 3500
MIN_DELTA_CHARS = 60


async def keep_typing(bot: Bot, chat_id: int, stop: asyncio.Event) -> None:
    """Держит статус «печатает», пока не выставлен флаг остановки."""
    while not stop.is_set():
        try:
            await bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        except TelegramError as exc:
            logger.debug("Не удалось отправить chat action: %s", exc)
            return
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=4.0)


class ReplyStreamer:
    """Создаёт сообщение-заглушку и обновляет его по мере генерации."""

    def __init__(
        self,
        bot: Bot,
        chat_id: int,
        *,
        reply_to_message_id: int | None = None,
        interval: float = 1.5,
    ) -> None:
        self._bot = bot
        self._chat_id = chat_id
        self._reply_to = reply_to_message_id
        self._interval = interval
        self._message: Message | None = None
        self._buffer: list[str] = []
        self._shown = ""
        self._last_edit = 0.0

    @property
    def text(self) -> str:
        return "".join(self._buffer)

    async def start(self) -> None:
        self._message = await self._bot.send_message(
            chat_id=self._chat_id,
            text=THINKING_TEXT,
            reply_to_message_id=self._reply_to,
        )
        self._last_edit = time.monotonic()

    async def push(self, delta: str) -> None:
        """Принимает кусок ответа и при необходимости обновляет сообщение."""
        self._buffer.append(delta)
        now = time.monotonic()
        if now - self._last_edit < self._interval:
            return
        text = self.text
        if len(text) - len(self._shown) < MIN_DELTA_CHARS:
            return
        self._last_edit = now
        preview = text[:PREVIEW_LIMIT]
        if len(text) > PREVIEW_LIMIT:
            preview += "\n…"
        if await self._edit(preview):
            self._shown = text

    async def finalize(self, text: str, *, footer: str = "") -> None:
        """Показывает финальный ответ, разбивая его на сообщения Telegram."""
        body = text if not footer else f"{text}\n\n{footer}"
        chunks = render_chunks(body) or [render(text) or "…"]

        if self._message is None:
            await self._send_new(chunks[0])
        elif not await self._edit(chunks[0], rendered=True):
            await self._send_new(chunks[0])

        for chunk in chunks[1:]:
            await self._send_new(chunk)

    async def fail(self, text: str) -> None:
        """Заменяет заглушку сообщением об ошибке."""
        if self._message is not None and await self._edit(text, rendered=True):
            return
        await self._send_new(text)

    # --- внутреннее ---------------------------------------------------

    async def _edit(self, text: str, *, rendered: bool = False) -> bool:
        if self._message is None or not text.strip():
            return False
        payload = text if rendered else render(text)
        payload = payload[:TELEGRAM_LIMIT]
        try:
            await self._message.edit_text(
                payload, parse_mode="HTML", disable_web_page_preview=True
            )
            return True
        except BadRequest as exc:
            note = str(exc).lower()
            if "not modified" in note:
                return True
            logger.debug("Правка сообщения не прошла (%s), пробую без разметки", exc)
            try:
                await self._message.edit_text(_strip_tags(payload)[:TELEGRAM_LIMIT])
                return True
            except TelegramError:
                return False
        except (Forbidden, TelegramError) as exc:
            logger.warning("Не удалось обновить сообщение: %s", exc)
            return False

    async def _send_new(self, text: str) -> None:
        try:
            self._message = await self._bot.send_message(
                chat_id=self._chat_id,
                text=text[:TELEGRAM_LIMIT],
                parse_mode="HTML",
                disable_web_page_preview=True,
                reply_to_message_id=self._reply_to if self._message is None else None,
            )
        except BadRequest as exc:
            logger.warning("Отправка с разметкой не прошла (%s), шлю обычным текстом", exc)
            self._message = await self._bot.send_message(
                chat_id=self._chat_id,
                text=_strip_tags(text)[:TELEGRAM_LIMIT],
            )


def _strip_tags(text: str) -> str:
    """Грубое удаление HTML-тегов для аварийной отправки."""
    return unescape(re.sub(r"<[^>]+>", "", text))
