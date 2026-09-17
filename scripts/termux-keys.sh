#!/data/data/com.termux/files/usr/bin/bash
#
# Записывает токен Telegram и ключ Anthropic в .env без ручной правки файла.
# Запуск:  bash ~/TeleBot/scripts/termux-keys.sh
#
set -uo pipefail

TARGET="${TARGET:-$HOME/TeleBot}"
cd "$TARGET" || { echo "Нет каталога $TARGET"; exit 1; }

if [ ! -f .env ]; then
    cp .env.example .env || { echo "Нет файла .env.example"; exit 1; }
fi
chmod 600 .env

echo "Вставь значения. Пустая строка оставит то, что уже записано."
echo
printf 'Токен бота от @BotFather: '
IFS= read -r TOKEN
printf 'Ключ Anthropic (sk-ant-...): '
IFS= read -r KEY
echo

python - "$TOKEN" "$KEY" <<'PY'
import pathlib
import sys

token, key = sys.argv[1].strip(), sys.argv[2].strip()
path = pathlib.Path(".env")
lines = path.read_text(encoding="utf-8").splitlines()

updates = {}
if token:
    updates["TELEGRAM_BOT_TOKEN"] = token
if key:
    updates["ANTHROPIC_API_KEY"] = key

seen = set()
result = []
for line in lines:
    name = line.split("=", 1)[0].strip() if "=" in line else ""
    if name in updates:
        result.append(f"{name}={updates[name]}")
        seen.add(name)
    else:
        result.append(line)
for name, value in updates.items():
    if name not in seen:
        result.append(f"{name}={value}")

path.write_text("\n".join(result) + "\n", encoding="utf-8")

warnings = []
if token and ":" not in token:
    warnings.append("Токен Telegram обычно выглядит как 123456789:AA... Проверь, что скопировал целиком.")
if key and not key.startswith("sk-ant-"):
    warnings.append("Ключ Anthropic обычно начинается с sk-ant-. Проверь, что скопировал целиком.")

current = dict(
    line.split("=", 1) for line in path.read_text(encoding="utf-8").splitlines()
    if "=" in line and not line.strip().startswith("#")
)
missing = [n for n in ("TELEGRAM_BOT_TOKEN", "ANTHROPIC_API_KEY") if not current.get(n, "").strip()]

print("Записано в .env")
for note in warnings:
    print(f"!  {note}")
if missing:
    print(f"!  Ещё не заполнено: {', '.join(missing)}")
    sys.exit(1)
PY
status=$?

echo
if [ "$status" -ne 0 ]; then
    echo "Заполни оставшееся и запусти этот скрипт снова."
    exit "$status"
fi

echo "Проверяю связь…"
echo
./.venv/bin/python main.py --check
