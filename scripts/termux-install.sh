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

command -v python >/dev/null 2>&1 || die "Python не установился. Повтори pkg install python."
command -v git >/dev/null 2>&1 || die "Git не установился. Повтори pkg install git."

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
    warn "Готовых пакетов под Android нет — собираю pydantic-core и jiter из исходников."
    warn "Это долго: от 15 до 40 минут. Не сворачивай Termux, держи телефон на зарядке."

    pkg install -y rust binutils
    CARGO_BUILD_TARGET="$(rustc -vV | sed -n 's/^host: //p')"
    export CARGO_BUILD_TARGET
    export CARGO_NET_GIT_FETCH_WITH_CLI=true

    ./.venv/bin/pip install -r requirements.txt \
        || die "Сборка не удалась. Пришли вывод ошибки — разберёмся."
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
  1. nano ~/TeleBot/.env      — вписать токен бота и ключ Anthropic
  2. bash ~/TeleBot/scripts/termux-run.sh   — запустить бота

Автозапуск после перезагрузки телефона:
  bash ~/TeleBot/scripts/termux-autostart.sh
HINT
