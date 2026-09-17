import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_deps  # noqa: E402


def test_parse_plain_versions():
    assert check_deps.parse("22.8") == (22, 8)
    assert check_deps.parse("1.6.0") == (1, 6, 0)


def test_parse_ignores_suffixes():
    assert check_deps.parse("22.8.1rc1") == (22, 8, 1)
    assert check_deps.parse("2.0.0b3") == (2, 0, 0)


def test_parse_bad_input():
    assert check_deps.parse("") == (0,)
    assert check_deps.parse("dev") == (0,)


def test_old_version_is_detected(monkeypatch):
    monkeypatch.setattr(check_deps, "REQUIRED", {"python-telegram-bot": ("22.8", "Python 3.14")})
    monkeypatch.setattr(check_deps, "version", lambda name: "21.9")
    found = check_deps.problems()
    assert len(found) == 1
    assert "21.9" in found[0] and "22.8" in found[0]


def test_new_version_passes(monkeypatch):
    monkeypatch.setattr(check_deps, "REQUIRED", {"python-telegram-bot": ("22.8", "Python 3.14")})
    monkeypatch.setattr(check_deps, "version", lambda name: "22.9")
    assert check_deps.problems() == []


def test_missing_package_is_reported(monkeypatch):
    def boom(name):
        raise check_deps.PackageNotFoundError(name)

    monkeypatch.setattr(check_deps, "REQUIRED", {"openai": ("1.60", "потоковые ответы")})
    monkeypatch.setattr(check_deps, "version", boom)
    assert "не установлен" in check_deps.problems()[0]


def test_requirements_file_matches_check():
    """Минимумы в check_deps не должны расходиться с requirements.txt."""
    text = (Path(__file__).resolve().parent.parent / "requirements.txt").read_text()
    for package in check_deps.REQUIRED:
        assert package in text
