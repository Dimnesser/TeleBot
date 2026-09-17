import json

import pytest

from bot.history import HistoryStore, IMAGE_PLACEHOLDER, image_block, text_block


async def test_append_and_get():
    store = HistoryStore()
    await store.append(1, "user", "привет")
    await store.append(1, "assistant", "здравствуй")
    messages = await store.get(1)
    assert [m["role"] for m in messages] == ["user", "assistant"]
    assert messages[0]["content"] == [text_block("привет")]


async def test_chats_are_isolated():
    store = HistoryStore()
    await store.append(1, "user", "первый")
    await store.append(2, "user", "второй")
    assert len(await store.get(1)) == 1
    assert (await store.get(2))[0]["content"][0]["text"] == "второй"


async def test_reset():
    store = HistoryStore()
    await store.append(7, "user", "вопрос")
    assert await store.reset(7) is True
    assert await store.get(7) == []
    assert await store.reset(7) is False


async def test_trim_by_message_count_starts_with_user():
    store = HistoryStore(max_messages=4)
    for index in range(10):
        await store.append(1, "user", f"вопрос {index}")
        await store.append(1, "assistant", f"ответ {index}")
    messages = await store.get(1)
    assert len(messages) <= 4
    assert messages[0]["role"] == "user"


async def test_trim_by_char_budget():
    store = HistoryStore(max_messages=50, max_chars=1000)
    for index in range(20):
        await store.append(1, "user", "я" * 300)
        await store.append(1, "assistant", "о" * 300)
    messages = await store.get(1)
    total = sum(len(block["text"]) for m in messages for block in m["content"])
    assert total <= 1000 + 300


async def test_old_images_are_replaced_with_placeholder():
    store = HistoryStore(max_messages=20)
    for index in range(4):
        await store.append(1, "user", [image_block("image/jpeg", "AAAA"), text_block(f"фото {index}")])
        await store.append(1, "assistant", f"ответ {index}")
    messages = await store.get(1)
    images = [b for m in messages for b in m["content"] if b.get("type") == "image"]
    placeholders = [
        b for m in messages for b in m["content"]
        if b.get("type") == "text" and b["text"] == IMAGE_PLACEHOLDER
    ]
    assert len(images) <= 2
    assert placeholders


async def test_persistence_roundtrip(tmp_path):
    path = tmp_path / "nested" / "history.json"
    store = HistoryStore(path=path)
    await store.append(42, "user", "запомни это")
    await store.append(42, "assistant", "запомнил")

    assert path.exists()
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert "42" in saved["chats"]

    restored = HistoryStore(path=path)
    await restored.load()
    messages = await restored.get(42)
    assert messages[1]["content"][0]["text"] == "запомнил"


async def test_broken_history_file_does_not_crash(tmp_path):
    path = tmp_path / "history.json"
    path.write_text("{ это не json", encoding="utf-8")
    store = HistoryStore(path=path)
    await store.load()
    assert await store.get(1) == []


async def test_stats():
    store = HistoryStore()
    await store.append(1, "user", "а")
    await store.append(2, "user", "б")
    assert await store.stats() == (2, 2)


@pytest.mark.parametrize("role", ["user", "assistant"])
async def test_string_content_is_normalized(role):
    store = HistoryStore()
    await store.append(1, "user", "старт")
    await store.append(1, role, "текст")
    assert (await store.get(1))[-1]["content"] == [text_block("текст")]
