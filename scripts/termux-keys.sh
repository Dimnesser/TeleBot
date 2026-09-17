#!/data/data/com.termux/files/usr/bin/bash
#
# Настройка провайдера и ключей, затем проверка связи.
# Запуск:  bash ~/TeleBot/scripts/termux-keys.sh
#
set -uo pipefail

TARGET="${TARGET:-$HOME/TeleBot}"
cd "$TARGET" || { echo "Нет каталога $TARGET"; exit 1; }

PYTHON="./.venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="python"

"$PYTHON" scripts/setup_keys.py || exit $?

echo
echo "Проверяю связь…"
echo
"$PYTHON" main.py --check
