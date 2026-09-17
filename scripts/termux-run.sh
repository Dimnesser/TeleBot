#!/data/data/com.termux/files/usr/bin/bash
#
# Запуск бота в Termux с защитой от засыпания и автоперезапуском.
#
set -uo pipefail

TARGET="${TARGET:-$HOME/TeleBot}"
cd "$TARGET" || { echo "Нет каталога $TARGET"; exit 1; }

if [ ! -f .env ]; then
    echo "Нет файла .env. Скопируй .env.example и впиши токены:"
    echo "    cp .env.example .env && nano .env"
    exit 1
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
    ./.venv/bin/python main.py
    code=$?
    # Ctrl+C и штатный выход — не перезапускаем.
    if [ "$code" -eq 0 ] || [ "$code" -eq 130 ]; then
        break
    fi
    echo "Процесс упал (код $code). Перезапуск через 10 секунд…"
    sleep 10
done
