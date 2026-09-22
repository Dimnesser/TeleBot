"""Тексты сообщений бота."""
from __future__ import annotations

from bot.database.models import DepositCategory

WELCOME_TEXT = (
    "👋 Привет, {name}!\n\n"
    "Это <b>Brainrot Battle</b> — бот для управления твоим внутриигровым балансом.\n"
    "Текущий баланс: <b>{balance} B</b>\n\n"
    "Выбери раздел ниже:"
)

SECTION_IN_PROGRESS = "🚧 Этот раздел ещё в разработке."

CATEGORY_TITLES = {
    DepositCategory.BRAINROT: "Брейнроты",
    DepositCategory.HIRSY: "Гирсы",
}

CATALOG_HEADER = {
    DepositCategory.BRAINROT: "<b>ПОПОЛНЕНИЕ БАЛАНСА</b>\n<b>ДЕПОЗИТ БРЕЙНРОТОМ</b>",
    DepositCategory.HIRSY: "<b>ПОПОЛНЕНИЕ БАЛАНСА</b>\n<b>ДЕПОЗИТ ГИРСАМИ</b>",
}

CATALOG_DESCRIPTION = {
    DepositCategory.BRAINROT: "Выбери брейнрота, введи свой ник в игре и отправь заявку — после проверки мы зачислим B на баланс.",
    DepositCategory.HIRSY: "Выбери гирсу, введи свой ник в игре и отправь заявку — после проверки мы зачислим B на баланс.",
}

CATALOG_HINT = "Выбери хотя бы один предмет ниже."
CATALOG_NEED_ITEM = "Выбери хотя бы один предмет выше."
CATALOG_TOTAL_LINE = "Итого к зачислению: <b>{total} B</b>"

DEPOSIT_ASK_NICKNAME = "Введите свой игровой ник в Roblox для заявки:"
DEPOSIT_NICKNAME_INVALID = "Ник должен быть от 2 до 32 символов. Попробуйте ещё раз:"

DEPOSIT_CONFIRM_TEXT = (
    "Проверь заявку перед отправкой:\n\n"
    "Ник в игре: <b>{nickname}</b>\n"
    "Предметы: {items}\n"
    "Итого к зачислению: <b>{total} B</b>\n\n"
    "После проверки модератором баланс будет пополнен."
)

DEPOSIT_SUBMITTED_TEXT = (
    "✅ Заявка №{request_id} отправлена на проверку.\n"
    "Мы уведомим тебя, как только баланс будет зачислен."
)
DEPOSIT_CANCELLED_TEXT = "Заявка отменена."
DEPOSIT_CLOSED_TEXT = "Пополнение закрыто. Вернуться в меню: /start"

DEPOSIT_UNAVAILABLE_TEXT = (
    "⚠️ <b>Депозит временно недоступен</b>\n\n"
    "⏳\n\n"
    "<b>В настоящее время мы не можем обработать твой депозит</b>\n\n"
    "Сейчас все места заняты другими игроками. Можешь встать в очередь — "
    "как только освободится место, мы сразу покажем инструкции для трейда.\n\n"
    "ПРИМЕРНОЕ ВРЕМЯ ОЖИДАНИЯ\n<b>~{eta}</b>"
)
DEPOSIT_QUEUED_TEXT = (
    "✅ Ты в очереди на депозит (заявка №{request_id}, позиция {position}).\n"
    "Как только освободится место, мы пришлём инструкции для трейда."
)
DEPOSIT_QUEUE_PROMOTED_TEXT = (
    "🎉 Место освободилось! Заявка №{request_id} принята в обработку — жди инструкции для трейда от модератора."
)

ADMIN_NEW_REQUEST_TEXT = (
    "🆕 Заявка на депозит №{request_id}\n"
    "Пользователь: {user}\n"
    "Категория: {category}\n"
    "Ник в игре: {nickname}\n"
    "Предметы: {items}\n"
    "Сумма: {total} B"
)

ADMIN_REQUEST_APPROVED = "✅ Заявка №{request_id} одобрена."
ADMIN_REQUEST_REJECTED = "❌ Заявка №{request_id} отклонена."
ADMIN_REQUEST_ALREADY_RESOLVED = "Заявка уже обработана."

USER_DEPOSIT_APPROVED = "✅ Твоя заявка одобрена! Начислено {total} B. Текущий баланс: {balance} B."
USER_DEPOSIT_REJECTED = "❌ Заявка №{request_id} отклонена модератором. Если это ошибка — напиши в поддержку."

STARS_HEADER = (
    "<b>ПОПОЛНЕНИЕ БАЛАНСА</b>\n<b>TELEGRAM STARS</b>\n\n"
    "Оплата Telegram Stars — зачисляется мгновенно после подтверждения в боте.\n\n"
    "Введи количество Stars (например: 625):"
)
STARS_AMOUNT_INVALID = "Введите целое число от {min} до {max}."
STARS_PROMO_PROMPT = "Промокод (необязательно). Отправьте код или нажмите «Пропустить»:"
STARS_READY_TEXT = (
    "Количество Stars: <b>{amount}</b>\n"
    "Промокод: {promo}\n"
    "Будет зачислено: <b>{credited} B</b>\n\n"
    "Нажми «Создать счёт в Stars», чтобы оплатить."
)
STARS_PAYMENT_SUCCESS = "✅ Оплата получена! Начислено {credited} B. Текущий баланс: {balance} B."
