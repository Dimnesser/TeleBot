#!/data/data/com.termux/files/usr/bin/bash
#
# Обновление бота: свежий код, зависимости, проверка связи.
# Запуск:  bash ~/TeleBot/scripts/termux-update.sh
#
set -uo pipefail

TARGET="${TARGET:-$HOME/TeleBot}"
cd "$TARGET" || { echo "Нет каталога $TARGET"; exit 1; }

PYTHON="./.venv/bin/python"
[ -x "$PYTHON" ] || PYTHON="python"

echo "==> Забираю свежий код"
git pull --ff-only || { echo "Не удалось обновить код"; exit 1; }

echo
echo "==> Проверяю зависимости"
"$PYTHON" -m pip install -q -r requirements.txt || { echo "Не удалось поставить зависимости"; exit 1; }

echo
echo "==> Проверяю связь"
echo
"$PYTHON" main.py --check
