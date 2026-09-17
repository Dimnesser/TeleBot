import html

from bot.telegram_format import TELEGRAM_LIMIT, render, render_chunks, split_markdown


def test_plain_text_is_escaped():
    assert render("5 < 7 & 8 > 2") == "5 &lt; 7 &amp; 8 &gt; 2"


def test_bold_and_italic():
    assert render("**важно** и *курсив*") == "<b>важно</b> и <i>курсив</i>"
    assert render("__жирный__ и _наклонный_") == "<b>жирный</b> и <i>наклонный</i>"


def test_inline_code_is_not_formatted_inside():
    assert render("`a * b * c`") == "<code>a * b * c</code>"


def test_code_block_keeps_language_and_escapes():
    out = render("```python\nif a < b:\n    pass\n```")
    assert out == '<pre><code class="language-python">if a &lt; b:\n    pass</code></pre>'


def test_code_block_without_language():
    assert render("```\nplain\n```") == "<pre><code>plain</code></pre>"


def test_unterminated_code_block_still_renders():
    out = render("```python\nx = 1")
    assert out.startswith('<pre><code class="language-python">')
    assert out.endswith("</code></pre>")


def test_headings_become_bold():
    assert render("## Заголовок") == "<b>Заголовок</b>"


def test_bullets_become_dots():
    assert render("- один\n- два") == "• один\n• два"


def test_links():
    assert render("[док](https://example.com/a)") == '<a href="https://example.com/a">док</a>'


def test_link_text_with_special_chars_is_escaped():
    assert render("[a<b](https://e.com)") == '<a href="https://e.com">a&lt;b</a>'


def test_underscores_in_identifiers_are_left_alone():
    assert render("some_var_name") == "some_var_name"


def test_strikethrough():
    assert render("~~нет~~") == "<s>нет</s>"


def test_empty_input():
    assert render("") == ""
    assert render_chunks("   ") == []


def test_render_chunks_respects_telegram_limit():
    text = "Очень длинный ответ. " * 1200
    chunks = render_chunks(text)
    assert len(chunks) > 1
    assert all(len(chunk) <= TELEGRAM_LIMIT for chunk in chunks)
    joined = " ".join(chunks)
    assert "Очень длинный ответ." in joined


def test_split_keeps_code_fences_balanced():
    body = "\n".join(f"line_{i} = {i}" for i in range(400))
    parts = split_markdown(f"текст\n```python\n{body}\n```", limit=800)
    assert len(parts) > 1
    for part in parts:
        assert part.count("```") % 2 == 0


def test_chunks_of_long_code_block_are_valid_html():
    body = "\n".join(f"value_{i} = {i}" for i in range(500))
    chunks = render_chunks(f"```python\n{body}\n```")
    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk.count("<pre>") == chunk.count("</pre>")
        assert len(chunk) <= TELEGRAM_LIMIT


def test_very_long_single_line_is_split():
    chunks = render_chunks("x" * 12000)
    assert all(len(chunk) <= TELEGRAM_LIMIT for chunk in chunks)
    assert sum(chunk.count("x") for chunk in chunks) == 12000


def test_html_in_user_text_cannot_inject_tags():
    out = render("<script>alert(1)</script>")
    assert "<script>" not in out
    assert html.escape("<script>alert(1)</script>", quote=False) == out
