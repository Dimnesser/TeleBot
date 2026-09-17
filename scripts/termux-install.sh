#!/data/data/com.termux/files/usr/bin/bash
#
# Установка TeleBot в Termux на Android.
# Запуск:  bash termux-install.sh
#
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Dimnesser/TeleBot.git}"
BRANCH="${BRANCH:-claude/telegram-ai-assistant-pfzidg}"
TARGET="${TARGET:-$HOME/TeleBot}"

say()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m!   %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31m✗   %s\033[0m\n' "$*" >&2; exit 1; }

[ -d /data/data/com.termux ] || die "Это не Termux. Скрипт рассчитан на Termux для Android."

# Установка длинная, а Android охотно усыпляет фоновые процессы.
# Блокировка снимается в конце скрипта.
if command -v termux-wake-lock >/dev/null 2>&1; then
    termux-wake-lock
    trap 'command -v termux-wake-unlock >/dev/null 2>&1 && termux-wake-unlock' EXIT
fi

# Termux — система с плавающими версиями. Если поставить один свежий пакет
# поверх старой базы, он потянет библиотеку, которой ещё нет, и сломается.
# Классический симптом: curl падает с "cannot locate symbol". Поэтому
# сначала обновляем всё целиком и только потом что-то ставим.
# Работаем через apt, а не через pkg: pkg — это обёртка, которая сама
# вызывает curl для проверки зеркал и падает вместе с ним.
say "Обновляю Termux целиком (это защищает от поломки libcurl)"
apt update
apt full-upgrade -y -o Dpkg::Options::=--force-confold

if ! curl --version >/dev/null 2>&1; then
    die "curl всё ещё сломан. Выполни: apt update && apt full-upgrade -y  и запусти скрипт заново."
fi

say "Ставлю Python и Git"
apt install -y python git

command -v python >/dev/null 2>&1 || die "Python не установился. Повтори apt install -y python."
command -v git >/dev/null 2>&1 || die "Git не установился. Повтори apt install -y git."

say "Забираю код в $TARGET"
if [ -d "$TARGET/.git" ]; then
    git -C "$TARGET" fetch origin "$BRANCH"
    git -C "$TARGET" checkout "$BRANCH"
    git -C "$TARGET" pull --ff-only origin "$BRANCH"
else
    git clone --branch "$BRANCH" "$REPO_URL" "$TARGET"
fi

cd "$TARGET"

say "Создаю виртуальное окружение"
[ -d .venv ] || python -m venv .venv
./.venv/bin/pip install --upgrade pip wheel

say "Ставлю зависимости"
if ! ./.venv/bin/pip install -r requirements.txt; then
    warn "Готовых пакетов под Android нет: собираю pydantic-core и jiter из исходников."
    warn "Это долго, от 15 до 40 минут. Не сворачивай Termux, держи телефон на зарядке."

    free_mb="$(df -Pm "$HOME" | awk 'NR==2 {print $4}')"
    if [ -n "${free_mb:-}" ] && [ "$free_mb" -lt 2500 ]; then
        warn "Свободно всего ${free_mb} МБ. Сборке Rust нужно около 2 ГБ, может не хватить."
    fi

    apt install -y rust binutils

    CARGO_BUILD_TARGET="$(rustc -vV | sed -n 's/^host: //p')"
    export CARGO_BUILD_TARGET
    export CARGO_NET_GIT_FETCH_WITH_CLI=true
    # Termux ставит самый свежий Python, который часто новее, чем знает PyO3
    # в опубликованных исходниках. Без этого флага сборка отказывается
    # начинаться со словами про "newer than PyO3 maximum supported version".
    export PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

    ./.venv/bin/pip install -r requirements.txt \
        || die "Сборка не удалась. Пришли вывод ошибки, разберёмся."
fi

say "Проверяю, что всё импортируется"
./.venv/bin/python -c "import telegram, anthropic; print('telegram', telegram.__version__, '| anthropic', anthropic.__version__)"

if [ ! -f .env ]; then
    say "Создаю .env"
    cp .env.example .env
    warn "Открой .env и впиши TELEGRAM_BOT_TOKEN и ANTHROPIC_API_KEY:"
    warn "    nano ~/TeleBot/.env"
else
    say ".env уже есть, не трогаю"
fi

mkdir -p data

say "Готово"
cat <<'HINT'
Дальше:
  1. bash ~/TeleBot/scripts/termux-keys.sh  — вписать ключи и проверить связь
  2. bash ~/TeleBot/scripts/termux-run.sh   — запустить бота

Автозапуск после перезагрузки телефона:
  bash ~/TeleBot/scripts/termux-autostart.sh
HINT
