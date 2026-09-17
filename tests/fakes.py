"""Заглушки Anthropic SDK для тестов."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeUsage:
    input_tokens: int = 10
    output_tokens: int = 20


@dataclass
class FakeMessage:
    content: list[Any]
    stop_reason: str | None = "end_turn"
    usage: FakeUsage = field(default_factory=FakeUsage)


@dataclass
class FakeTextEvent:
    text: str
    type: str = "text"


class FakeStream:
    def __init__(self, message: FakeMessage, deltas: list[str]) -> None:
        self._message = message
        self._deltas = deltas

    async def __aenter__(self) -> "FakeStream":
        return self

    async def __aexit__(self, *args: Any) -> bool:
        return False

    def __aiter__(self):
        async def generator():
            for delta in self._deltas:
                yield FakeTextEvent(text=delta)

        return generator()

    async def get_final_message(self) -> FakeMessage:
        return self._message


class FakeMessages:
    def __init__(self, owner: "FakeAnthropic", beta: bool) -> None:
        self._owner = owner
        self._beta = beta

    def stream(self, **kwargs: Any) -> FakeStream:
        self._owner.calls.append({"beta": self._beta, **kwargs})
        if self._owner.errors:
            raise self._owner.errors.pop(0)
        message, deltas = (
            self._owner.turns.pop(0) if self._owner.turns else (FakeMessage([]), [])
        )
        return FakeStream(message, deltas)


class FakeBeta:
    def __init__(self, owner: "FakeAnthropic") -> None:
        self.messages = FakeMessages(owner, beta=True)


class FakeAnthropic:
    """Очередь ответов и ошибок вместо реального клиента."""

    def __init__(
        self,
        turns: list[tuple[FakeMessage, list[str]]] | None = None,
        errors: list[Exception] | None = None,
    ) -> None:
        self.turns = list(turns or [])
        self.errors = list(errors or [])
        self.calls: list[dict[str, Any]] = []
        self.messages = FakeMessages(self, beta=False)
        self.beta = FakeBeta(self)


def text_block_obj(text: str) -> dict[str, Any]:
    return {"type": "text", "text": text}


def collector(target: list[str]):
    """Асинхронный колбэк, складывающий куски ответа в список."""

    async def on_delta(delta: str) -> None:
        target.append(delta)

    return on_delta
