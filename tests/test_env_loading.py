"""Регрессия: .env должен реально доходить до Config через настоящий main.py.

Раньше main.py импортировал bot.app (который транзитивно импортирует
bot.config) ДО вызова load_dotenv() — Config собирал свои поля через
os.getenv(...) в момент импорта модуля, то есть до того, как .env был
прочитан. В проде это означало, что BOT_TOKEN из .env никогда не
подхватывался. Юнит-тесты этого не ловили, потому что везде вокруг
env-переменные выставлялись в os.environ напрямую, а не через .env-файл —
поэтому здесь тест буквально импортирует настоящий main.py отдельным
процессом (без вызова asyncio.run — это происходит только под
`if __name__ == "__main__"`, которого при импорте не будет).
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


def _run_against_real_main(env_file_content: str | None, extra_env: dict[str, str] | None = None) -> str:
    repo_root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        (work_dir / "bot").symlink_to(repo_root / "bot")
        (work_dir / "webapp").symlink_to(repo_root / "webapp")
        (work_dir / "main.py").symlink_to(repo_root / "main.py")
        if env_file_content is not None:
            (work_dir / ".env").write_text(env_file_content, encoding="utf-8")

        code = (
            "import sys; sys.path.insert(0, '.'); "
            "import main; "  # исполняет реальный main.py на уровне модуля (load_dotenv + импорт bot.app)
            "from bot.config import config; "
            "print('BOT_TOKEN=' + repr(config.bot_token))"
        )
        env = {"PATH": "/usr/bin:/bin", **(extra_env or {})}
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=work_dir, capture_output=True, text=True, timeout=10, env=env
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout


def test_real_main_py_picks_up_bot_token_from_dotenv_file():
    output = _run_against_real_main("BOT_TOKEN=123456:test-token-from-dotenv\n")
    assert "BOT_TOKEN='123456:test-token-from-dotenv'" in output


def test_real_main_py_bot_token_empty_without_env_file_or_var():
    output = _run_against_real_main(env_file_content=None)
    assert "BOT_TOKEN=''" in output
