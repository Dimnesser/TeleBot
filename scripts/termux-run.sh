#!/data/data/com.termux/files/usr/bin/bash
#
# Запуск бота. Сам доставит зависимости и спросит ключи, если их ещё нет.
# Запуск:  bash ~/TeleBot/scripts/termux-run.sh
#
set -uo pipefail

TARGET="${TARGET:-$HOME/TeleBot}"
cd "$TARGET" || { echo "Нет каталога $TARGET"; exit 1; }

PYTHON="./.venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="python"

# Зависимости проверяем импортом: он мгновенный, в отличие от запуска pip.
if ! "$PYTHON" -c "import telegram, anthropic, openai" >/dev/null 2>&1; then
    echo "==> Доставляю зависимости"
    "$PYTHON" -m pip install -q -r requirements.txt || {
        echo "Не удалось поставить зависимости"
        exit 1
    }
fi

# Настройки спрашиваем, только если их ещё нет.
needs_setup=1
if [ -f .env ]; then
    "$PYTHON" - <<'PY' && needs_setup=0
import sys
from pathlib import Path

values = {}
for line in Path(".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        name, value = line.split("=", 1)
        values[name.strip()] = value.strip()

keys = ("ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY",
        "OPENROUTER_API_KEY", "OPENAI_API_KEY", "AI_API_KEY")
ready = bool(values.get("TELEGRAM_BOT_TOKEN")) and any(values.get(k) for k in keys)
sys.exit(0 if ready else 1)
PY
fi

if [ "$needs_setup" -eq 1 ]; then
    echo
    "$PYTHON" scripts/setup_keys.py || exit $?
    echo
fi

# Не даём Android усыпить процесс. Снимается командой termux-wake-unlock.
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock

cleanup() {
    command -v termux-wake-unlock >/dev/null 2>&1 && termux-wake-unlock
    echo "Бот остановлен."
}
trap cleanup EXIT INT TERM

echo "Бот запускается. Остановить — Ctrl+C."
while true; do
    "$PYTHON" main.py
    code=$?
    # Ctrl+C и штатный выход — не перезапускаем.
    if [ "$code" -eq 0 ] || [ "$code" -eq 130 ]; then
        break
    fi
    echo "Процесс упал (код $code). Перезапуск через 10 секунд…"
    sleep 10
done
