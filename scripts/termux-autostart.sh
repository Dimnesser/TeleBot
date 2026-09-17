#!/data/data/com.termux/files/usr/bin/bash
#
# Автозапуск бота после перезагрузки телефона.
# Нужно приложение Termux:Boot (F-Droid), запущенное хотя бы один раз.
#
set -euo pipefail

BOOT_DIR="$HOME/.termux/boot"
TARGET="${TARGET:-$HOME/TeleBot}"

mkdir -p "$BOOT_DIR"
cat > "$BOOT_DIR/telebot.sh" <<SCRIPT
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
exec bash "$TARGET/scripts/termux-run.sh"
SCRIPT
chmod +x "$BOOT_DIR/telebot.sh"

echo "Автозапуск настроен: $BOOT_DIR/telebot.sh"
echo "Установи Termux:Boot из F-Droid и открой его один раз, иначе Android не даст стартовать."
