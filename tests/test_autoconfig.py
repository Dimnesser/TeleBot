import pytest

from bot.autoconfig import choose_model, score_model


def test_gemini_prefers_flash():
    names = ["models/gemini-2.5-pro", "models/gemini-2.5-flash", "models/embedding-001"]
    assert choose_model(names, "gemini") == "models/gemini-2.5-flash"


def test_gemini_skips_embeddings_and_tts():
    names = ["models/embedding-001", "models/gemini-2.0-flash-tts"]
    assert choose_model(names, "gemini") is None


def test_groq_prefers_versatile_llama():
    names = ["whisper-large-v3", "llama-guard-4", "llama-3.3-70b-versatile"]
    assert choose_model(names, "groq") == "llama-3.3-70b-versatile"


def test_openrouter_prefers_free():
    names = ["some/paid-model", "other/model:free"]
    assert choose_model(names, "openrouter") == "other/model:free"


def test_openai_prefers_mini():
    names = ["gpt-4o", "gpt-4o-mini", "tts-1", "text-embedding-3-small"]
    assert choose_model(names, "openai") == "gpt-4o-mini"


def test_unknown_provider_takes_first_usable():
    assert choose_model(["a", "b"], "неизвестный") == "a"


def test_empty_list():
    assert choose_model([], "gemini") is None


@pytest.mark.parametrize("name", ["whisper-large", "llama-guard", "playai-tts"])
def test_groq_avoids_non_chat_models(name):
    assert score_model(name, ("llama",), ("whisper", "guard", "tts")) == -1
