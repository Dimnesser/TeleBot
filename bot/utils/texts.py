"""Тексты сообщений бота."""
from __future__ import annotations

from bot.database.models import CaseCategory, DepositCategory

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

CASES_CATEGORY_TITLES = {
    CaseCategory.CASES: "КЕЙСЫ",
    CaseCategory.THEMATIC: "ТЕМАТИЧЕСКИЕ КЕЙСЫ",
    CaseCategory.ALLIN: "ALL-IN",
    CaseCategory.PARTNERS: "ПАРТНЁРЫ",
    CaseCategory.FREE: "БЕСПЛАТНЫЕ КЕЙСЫ",
}

CASES_HOME_TEXT = (
    "<b>{title}</b>\n\n"
    "Демо-баланс: <b>{tokens} 🎫</b>\n"
    "🔒 — пул предметов кейса пока не подтверждён скриншотами, открытие временно недоступно.\n\n"
    "Выбери кейс:"
)

CASE_DETAIL_HEADER = "<b>{name}</b>"
CASE_DETAIL_PRICE_LINE = "Цена: <b>{price} 🎫</b> за 1 шт · {count} предм. в пуле"
CASE_DETAIL_PRICE_UNKNOWN_LINE = "Цена уточняется · {count} предм. в пуле"
CASE_DETAIL_NOTE_LINE = "ℹ️ {note}"
CASE_DETAIL_NOT_OPENABLE = "🔒 Пул предметов этого кейса пока не подтверждён скриншотами — открытие недоступно."
CASE_DETAIL_DROP_POOL_HEADER = "<b>ЧТО МОЖЕТ ВЫПАСТЬ</b>"
CASE_DETAIL_DROP_POOL_PARTIAL = "(известно {known} из {total} предметов пула)"
CASE_DETAIL_BALANCE_LINE = "Демо-баланс: <b>{tokens} 🎫</b>"
CASE_DETAIL_TOTAL_COST_LINE = "Стоимость открытия ×{qty}: <b>{cost} 🎫</b>"

CASE_OPEN_NOT_OPENABLE_ALERT = "Пул предметов этого кейса ещё не подтверждён — открытие недоступно."
CASE_OPEN_NO_PRICE_ALERT = "У этого кейса не задана цена — открытие недоступно."
CASE_OPEN_NOT_ENOUGH_TOKENS = "Недостаточно демо-фишек. Нужно {cost} 🎫, у тебя {balance} 🎫."

CASE_OPEN_RESULT_HEADER = "🎉 Открыт кейс «{name}» ×{qty}:"
CASE_OPEN_RESULT_LINE = "• {name} — {value} B"
CASE_OPEN_RESULT_FOOTER = "\nДемо-баланс: <b>{tokens} 🎫</b>"

CASES_TOPUP_TEXT = "🎁 Начислено {amount} 🎫 демо-баланса. Текущий демо-баланс: {tokens} 🎫."

CASES_INVENTORY_HEADER = "<b>🎒 Твой инвентарь (последние {limit})</b>"
CASES_INVENTORY_EMPTY = "Пока пусто — открой кейс, чтобы что-то тут появилось."
CASES_INVENTORY_LINE = "• {item_name} ({case_name}) — {value} B"

CASES_DEMO_DISCLAIMER = (
    "Кейсы работают на демо-фишках 🎫 — они не покупаются за деньги/предметы и не выводятся, "
    "это отдельная песочница для проверки механики, не связанная с балансом B из обменника."
)

UPGRADER_HOME_HEADER = "<b>АПГРЕЙДЕР</b>"
UPGRADER_HOME_DISCLAIMER = (
    "Апгрейдер работает с предметами из твоего инвентаря (дропы из кейсов), а не с балансом B "
    "или Stars — рискуешь только тем, что уже выиграл в демо-режиме."
)
UPGRADER_CONTRIBUTION_LABEL = "ТВОЙ ВКЛАД"
UPGRADER_TARGET_LABEL = "ЖЕЛАЕМЫЙ ПРЕДМЕТ"
UPGRADER_SLOT_EMPTY = "— не выбрано —"
UPGRADER_SLOT_ITEM = "{name} ({value} B)"
UPGRADER_CHANCE_LINE = "ШАНС: <b>{chance}%</b>"
UPGRADER_CHANCE_BAR = "{bar} {chance}%"
UPGRADER_NEED_CONTRIBUTION_FIRST = "Сначала выбери предмет во «Твой вклад»."
UPGRADER_NO_ITEMS_TEXT = "Инвентарь пуст — сначала открой кейс, чтобы получить предметы для апгрейда."
UPGRADER_NO_TARGET_FOUND = "Не нашлось подходящего предмета под этот пресет — попробуй выбрать цель вручную."

UPGRADER_MY_ITEMS_HEADER = "<b>Мои предметы</b>\nВыбери, чем рискуешь:"
UPGRADER_TARGETS_HEADER = "<b>Желаемые предметы</b>\nВыбери, что хочешь получить:"

UPGRADER_CONFIRM_NEED_BOTH = "Выбери и вклад, и желаемый предмет."
UPGRADER_CONFIRM_ITEM_GONE = "Этот предмет уже не в инвентаре — выбери вклад заново."

UPGRADER_RESULT_SUCCESS = (
    "🎉 <b>Успех!</b> {contribution} превратился в {target} — предмет добавлен в инвентарь."
)
UPGRADER_RESULT_FAIL = "💥 <b>Не повезло.</b> {contribution} потерян."
UPGRADER_RESULT_CHANCE_LINE = "Шанс был: {chance}%"

CRASH_HOME_HEADER = "<b>КРАШ</b>"
CRASH_HOME_DISCLAIMER = (
    "В отличие от оригинала раунд личный, не общий на всех — Telegram-бот не может "
    "синхронно транслировать одну и ту же ракету всем игрокам сразу. "
    "Ставка — предмет из инвентаря."
)
CRASH_STAKE_LABEL = "СТАВКА"
CRASH_SLOT_EMPTY = "— не выбрано —"
CRASH_SLOT_ITEM = "{name} ({value} B)"
CRASH_HISTORY_LABEL = "Последние раунды: {history}"
CRASH_NO_ITEMS_TEXT = "Инвентарь пуст — сначала открой кейс, чтобы получить предметы для ставки."
CRASH_NEED_ITEM_FIRST = "Сначала выбери брейнрота для ставки."
CRASH_ALREADY_RUNNING = "У тебя уже есть раунд в полёте — сначала заверши его."
CRASH_ITEM_GONE = "Этот предмет уже не в инвентаре — выбери ставку заново."
CRASH_NO_ACTIVE_ROUND = "Нет активного раунда."
CRASH_ALREADY_RESOLVED = "Раунд уже завершён."

CRASH_IN_FLIGHT_TEXT = "🚀 <b>В ПОЛЁТЕ</b>\n\nМножитель: <b>{multiplier}x</b>\nСтавка: {stake}"
CRASH_CASHOUT_SUCCESS = (
    "💰 <b>Забрал на {multiplier}x!</b>\n{stake} превратился в {result} — предмет добавлен в инвентарь."
)
CRASH_CRASHED_TEXT = "💥 <b>Крах на {crash_point}x!</b>\n{stake} потерян."

DICE_HOME_HEADER = "<b>ДАЙСЫ</b>"
DICE_HOME_DISCLAIMER = "4 кубика, выбери цвет и предмет для ставки."
DICE_STAKE_LABEL = "СТАВКА"
DICE_COLOR_LABEL = "ЦВЕТ"
DICE_SLOT_EMPTY = "— не выбрано —"
DICE_SLOT_ITEM = "{name} ({value} B)"
DICE_NEED_BOTH = "Выбери и цвет, и предмет для ставки."
DICE_NO_ITEMS_TEXT = "Инвентарь пуст — сначала открой кейс, чтобы получить предметы для ставки."
DICE_ITEM_GONE = "Этот предмет уже не в инвентаре — выбери ставку заново."

DICE_RULES_HEADER = "<b>Правила игры</b>"
DICE_RULES_ROW_WIN = "{count}/4 — выигрыш x{multiplier}"
DICE_RULES_ROW_LOSS = "{count}/4 — проигрыш"
DICE_RULES_BONUS_ROW = "БОНУС 🌈 — выигрыш x{multiplier}"

DICE_RESULT_HEADER = "Выпало: {dice}"
DICE_RESULT_MATCHES = "Совпадений с {color}: {count}/4"
DICE_RESULT_BONUS = "🌈 БОНУС!"
DICE_RESULT_WIN = "🎉 <b>Выигрыш x{multiplier}!</b> {stake} превратился в {result} — предмет добавлен в инвентарь."
DICE_RESULT_LOSS = "💥 <b>Проигрыш.</b> {stake} потерян."
