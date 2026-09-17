"""Хранилище истории диалогов по чатам.

Держит сообщения в формате Messages API (роль + список блоков), обрезает
контекст по количеству сообщений и по объёму символов, при желании
сохраняет состояние на диск, чтобы перезапуск бота не терял контекст.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

Block = dict[str, Any]
Message = dict[str, Any]

# Во сколько «символов» оцениваем картинку при подсчёте бюджета контекста.
IMAGE_WEIGHT = 1500
# Сколько последних сообщений пользователя сохраняют приложенные картинки.
IMAGE_MEMORY = 2

IMAGE_PLACEHOLDER = "[изображение из более раннего сообщения]"


def text_block(text: str) -> Block:
    return {"type": "text", "text": text}


def image_block(media_type: str, data_b64: str) -> Block:
    return {
        "type": "image",
        "source": {"type": "base64", "media_type": media_type, "data": data_b64},
    }


def message_size(message: Message) -> int:
    """Приблизительный «вес» сообщения в символах."""
    content = message.get("content")
    if isinstance(content, str):
        return len(content)
    total = 0
    for block in content or []:
        if block.get("type") == "text":
            total += len(block.get("text", ""))
        elif block.get("type") == "image":
            total += IMAGE_WEIGHT
        else:
            total += 200
    return total


def normalize(content: str | list[Block]) -> list[Block]:
    return [text_block(content)] if isinstance(content, str) else list(content)


class HistoryStore:
    """Потокобезопасная (в рамках event loop) память диалогов."""

    def __init__(
        self,
        *,
        max_messages: int = 20,
        max_chars: int = 40_000,
        path: Path | None = None,
    ) -> None:
        self._max_messages = max(2, max_messages)
        self._max_chars = max_chars
        self._path = path
        self._lock = asyncio.Lock()
        self._chats: dict[int, list[Message]] = {}

    async def load(self) -> None:
        """Читает сохранённое состояние. Битый файл не роняет бота."""
        if self._path is None or not self._path.exists():
            return
        try:
            raw = await asyncio.to_thread(self._path.read_text, "utf-8")
            data = json.loads(raw)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Не удалось прочитать историю из %s: %s", self._path, exc)
            return
        chats: dict[int, list[Message]] = {}
        for key, messages in (data.get("chats") or {}).items():
            try:
                chats[int(key)] = list(messages)
            except (TypeError, ValueError):
                continue
        async with self._lock:
            self._chats = chats
        logger.info("История загружена: %d чатов", len(chats))

    async def get(self, chat_id: int) -> list[Message]:
        async with self._lock:
            return [dict(message) for message in self._chats.get(chat_id, [])]

    async def append(self, chat_id: int, role: str, content: str | list[Block]) -> None:
        async with self._lock:
            messages = self._chats.setdefault(chat_id, [])
            messages.append({"role": role, "content": normalize(content)})
            self._chats[chat_id] = self._trim(messages)
        await self._persist()

    async def replace(self, chat_id: int, messages: list[Message]) -> None:
        async with self._lock:
            self._chats[chat_id] = self._trim([dict(m) for m in messages])
        await self._persist()

    async def reset(self, chat_id: int) -> bool:
        async with self._lock:
            existed = bool(self._chats.pop(chat_id, None))
        await self._persist()
        return existed

    async def stats(self) -> tuple[int, int]:
        async with self._lock:
            chats = len(self._chats)
            messages = sum(len(items) for items in self._chats.values())
        return chats, messages

    # --- внутреннее ---------------------------------------------------

    def _trim(self, messages: list[Message]) -> list[Message]:
        trimmed = self._drop_old_images(messages)

        if len(trimmed) > self._max_messages:
            trimmed = trimmed[-self._max_messages :]

        total = sum(message_size(message) for message in trimmed)
        while len(trimmed) > 1 and total > self._max_chars:
            total -= message_size(trimmed[0])
            trimmed = trimmed[1:]

        # Messages API требует, чтобы диалог начинался с реплики пользователя.
        while trimmed and trimmed[0].get("role") != "user":
            trimmed = trimmed[1:]
        return trimmed

    @staticmethod
    def _drop_old_images(messages: list[Message]) -> list[Message]:
        """Оставляет картинки только у последних пользовательских сообщений."""
        user_indexes = [i for i, m in enumerate(messages) if m.get("role") == "user"]
        keep_from = user_indexes[-IMAGE_MEMORY] if len(user_indexes) > IMAGE_MEMORY else 0

        result: list[Message] = []
        for index, message in enumerate(messages):
            content = message.get("content")
            if index >= keep_from or not isinstance(content, list):
                result.append(message)
                continue
            if not any(block.get("type") == "image" for block in content):
                result.append(message)
                continue
            cleaned = [
                text_block(IMAGE_PLACEHOLDER) if block.get("type") == "image" else block
                for block in content
            ]
            result.append({**message, "content": cleaned})
        return result

    async def _persist(self) -> None:
        if self._path is None:
            return
        async with self._lock:
            snapshot = {"chats": {str(k): v for k, v in self._chats.items() if v}}
        try:
            await asyncio.to_thread(self._write, snapshot)
        except OSError as exc:
            logger.warning("Не удалось сохранить историю в %s: %s", self._path, exc)

    def _write(self, snapshot: dict[str, Any]) -> None:
        assert self._path is not None
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self._path)
