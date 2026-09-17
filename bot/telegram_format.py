"""Преобразование Markdown-ответов модели в HTML-разметку Telegram.

Telegram понимает лишь небольшое подмножество HTML, а MarkdownV2 требует
экранировать почти каждый символ. Поэтому модель отвечает обычным Markdown,
а бот переводит его в безопасный HTML и режет на сообщения по 4096 символов.
"""

from __future__ import annotations

import html
import re

TELEGRAM_LIMIT = 4096

_FENCE_RE = re.compile(r"```([^\n`]*)\n?(.*?)(?:```|\Z)", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)
_BULLET_RE = re.compile(r"^(\s*)[-*+]\s+", re.MULTILINE)
_RULE_RE = re.compile(r"^\s{0,3}(?:-{3,}|\*{3,}|_{3,})\s*$", re.MULTILINE)
_BOLD_RE = re.compile(r"\*\*(?=\S)(.+?)(?<=\S)\*\*", re.DOTALL)
_BOLD_ALT_RE = re.compile(r"(?<![\w*])__(?=\S)(.+?)(?<=\S)__(?![\w*])", re.DOTALL)
_ITALIC_RE = re.compile(r"(?<![\w*\\])\*(?=[^\s*])([^*\n]+?)(?<=\S)\*(?![\w*])")
_ITALIC_ALT_RE = re.compile(r"(?<![\w_\\])_(?=[^\s_])([^_\n]+?)(?<=\S)_(?![\w_])")
_STRIKE_RE = re.compile(r"~~(?=\S)(.+?)(?<=\S)~~", re.DOTALL)
_LINK_RE = re.compile(r"\[([^\]\n]+)\]\((https?://[^\s()]+|tg://[^\s()]+)\)")
_PLACEHOLDER_RE = re.compile("\x00(\\d+)\x00")


def _placeholder(index: int) -> str:
    return f"\x00{index}\x00"


def render(text: str) -> str:
    """Переводит Markdown в HTML, который принимает Telegram."""
    if not text:
        return ""

    source = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks: list[str] = []

    def stash_fence(match: re.Match[str]) -> str:
        language = match.group(1).strip()
        code = match.group(2)
        code = code[:-1] if code.endswith("\n") else code
        escaped = html.escape(code, quote=False)
        if language and re.fullmatch(r"[\w+#.-]+", language):
            opening = f'<pre><code class="language-{html.escape(language, quote=True)}">'
        else:
            opening = "<pre><code>"
        blocks.append(f"{opening}{escaped}</code></pre>")
        return _placeholder(len(blocks) - 1)

    def stash_inline(match: re.Match[str]) -> str:
        escaped = html.escape(match.group(1), quote=False)
        blocks.append(f"<code>{escaped}</code>")
        return _placeholder(len(blocks) - 1)

    source = _FENCE_RE.sub(stash_fence, source)
    source = _INLINE_CODE_RE.sub(stash_inline, source)

    source = html.escape(source, quote=False)

    source = _RULE_RE.sub("————————", source)
    source = _HEADING_RE.sub(lambda m: f"<b>{m.group(1)}</b>", source)
    source = _BULLET_RE.sub(lambda m: f"{m.group(1)}• ", source)

    source = _LINK_RE.sub(
        lambda m: f'<a href="{html.escape(m.group(2), quote=True)}">{m.group(1)}</a>',
        source,
    )
    source = _BOLD_RE.sub(lambda m: f"<b>{m.group(1)}</b>", source)
    source = _BOLD_ALT_RE.sub(lambda m: f"<b>{m.group(1)}</b>", source)
    source = _STRIKE_RE.sub(lambda m: f"<s>{m.group(1)}</s>", source)
    source = _ITALIC_RE.sub(lambda m: f"<i>{m.group(1)}</i>", source)
    source = _ITALIC_ALT_RE.sub(lambda m: f"<i>{m.group(1)}</i>", source)

    source = _PLACEHOLDER_RE.sub(lambda m: blocks[int(m.group(1))], source)
    return source.strip("\n")


def _split_long_line(line: str, limit: int) -> list[str]:
    """Режет строку длиннее лимита, по возможности по пробелу."""
    pieces: list[str] = []
    rest = line
    while len(rest) > limit:
        cut = rest.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        pieces.append(rest[:cut])
        rest = rest[cut:].lstrip()
    if rest:
        pieces.append(rest)
    return pieces


def split_markdown(text: str, limit: int = 3000) -> list[str]:
    """Делит Markdown на части, не разрывая блоки кода некорректно."""
    if len(text) <= limit:
        return [text] if text else []

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    fence: str | None = None

    def flush(open_fence: str | None) -> None:
        nonlocal current, current_len
        if not current:
            return
        chunk = "\n".join(current)
        if open_fence is not None:
            chunk += "\n```"
        chunks.append(chunk)
        current = []
        current_len = 0
        if open_fence is not None:
            opener = f"```{open_fence}"
            current.append(opener)
            current_len = len(opener) + 1

    for raw_line in text.split("\n"):
        for line in _split_long_line(raw_line, limit - 8) or [""]:
            if current and current_len + len(line) + 1 > limit:
                flush(fence)
            current.append(line)
            current_len += len(line) + 1
            stripped = line.strip()
            if stripped.startswith("```"):
                fence = None if fence is not None else stripped[3:].strip()

    flush(None)
    return [chunk for chunk in chunks if chunk.strip()]


def render_chunks(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    """Готовые к отправке HTML-куски, каждый не длиннее лимита Telegram."""
    if not text or not text.strip():
        return []

    budget = min(limit, 3000)
    while budget >= 400:
        rendered = [render(part) for part in split_markdown(text, budget)]
        rendered = [part for part in rendered if part.strip()]
        if all(len(part) <= limit for part in rendered):
            return rendered
        budget //= 2

    # Крайний случай: очень «тяжёлая» разметка. Отдаём экранированный текст.
    plain = html.escape(text, quote=False)
    return [plain[index : index + limit] for index in range(0, len(plain), limit)]
