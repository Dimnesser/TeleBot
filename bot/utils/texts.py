"""Тексты сообщений бота."""
from __future__ import annotations

from bot.database.models import CaseCategory, DepositCategory

WELCOME_TEXT = (
    "👋 Привет, {name}!\n\n"
    "Это <b>BrainCore</b> — бот для управления твоим внутриигровым балансом.\n"
    "Текущий баланс: <b>{balance} B</b>\n\n"
    "🎁 Открой кейс — выбери категорию, или перейди в любой раздел ниже:"
)

# Приветствие на /start — подпись к баннеру bot/assets/welcome.jpg.
START_CAPTION = (
    "🤖 Добро пожаловать в <b>BrainCore</b>!\n\n"
    "Кейсы по игре «Steal a Brainrot»!\n"
    "<blockquote>» Открывай кейсы\n» Улучшай брейнротов\n» Играй в батлы</blockquote>\n\n"
    "🍀 Испытай удачу с нами!"
)

PARTNER_CODE_APPLIED = (
    "\n\n🎁 Партнёрский код активирован: реферальный кейс ×{cases} уже в Mini App, "
    "а к каждому пополнению — бонус +{bonus:g}%."
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
    "✅ Заявка №{request_id} принята — ты первый в очереди.\n"
    "Модератор кинет трейд на ник из заявки; после трейда B зачислятся на баланс."
)
DEPOSIT_ALREADY_OPEN_TEXT = "У тебя уже есть заявка №{request_id} в очереди — дождись её, потом оставляй новую."
DEPOSIT_CANCELLED_TEXT = "Заявка отменена."
DEPOSIT_CLOSED_TEXT = "Пополнение закрыто. Вернуться в меню: /start"

DEPOSIT_QUEUED_TEXT = (
    "✅ Ты в очереди на депозит: заявка №{request_id}, место {position}.\n"
    "Трейды идут строго по очереди — когда дойдёт твоя, пришлём сообщение."
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
STARS_PROMO_PROMPT = "Есть код? Любой промокод, партнёрский или реферальный код даёт бонус к пополнению. Отправь код или нажми «Пропустить»:"
STARS_READY_TEXT = (
    "⭐ К оплате: <b>{amount} Stars</b>\n"
    "Код: <b>{promo}</b>\n"
    "Курс: 1 ⭐ = {rate} B{bonus}\n"
    "Будет зачислено: <b>{credited} B</b>\n\n"
    "Нажми «Создать счёт в Stars», чтобы оплатить."
)
STARS_BAD_CODE = "Такого кода нет. Введи промокод, партнёрский или реферальный код — или нажми «Пропустить»."
STARS_PAYMENT_SUCCESS = "✅ Оплата получена! Начислено {credited} B. Текущий баланс: {balance} B."

CASES_CATEGORY_TITLES = {
    CaseCategory.STARTER: "СТАРТ",
    CaseCategory.SIGNATURE: "ЛЕГЕНДЫ",
    CaseCategory.APEX: "ВЕРШИНА",
}

CASES_HOME_TEXT = (
    "<b>{title}</b>\n\n"
    "Баланс: <b>{tokens} B</b>\n"
    "Внутри — только реальные брейнроты из Steal a Brainrot. "
    "Красивое открытие с анимацией — в Mini App.\n\n"
    "Выбери кейс:"
)

CASE_DETAIL_HEADER = "<b>{name}</b>"
CASE_DETAIL_PRICE_LINE = "Цена: <b>{price} B</b> за 1 шт · {count} предм. в пуле"
CASE_DETAIL_PRICE_UNKNOWN_LINE = "Цена уточняется · {count} предм. в пуле"
CASE_DETAIL_NOTE_LINE = "ℹ️ {note}"
CASE_DETAIL_NOT_OPENABLE = "🔒 У этого кейса пока нет содержимого — открытие недоступно."
CASE_DETAIL_DROP_POOL_HEADER = "<b>ЧТО ВНУТРИ</b>"
CASE_DETAIL_BALANCE_LINE = "Баланс: <b>{tokens} B</b>"
CASE_DETAIL_TOTAL_COST_LINE = "Стоимость открытия ×{qty}: <b>{cost} B</b>"

CASE_OPEN_NOT_OPENABLE_ALERT = "У этого кейса пока нет содержимого — открытие недоступно."
CASE_OPEN_NO_PRICE_ALERT = "У этого кейса не задана цена — открытие недоступно."
CASE_OPEN_NOT_ENOUGH_TOKENS = "Недостаточно B. Нужно {cost} B, у тебя {balance} B. Пополни баланс."

CASE_OPEN_RESULT_HEADER = "🎉 Открыт кейс «{name}» ×{qty}:"
CASE_OPEN_RESULT_LINE = "• {name} [{rarity}] — {value} B"
CASE_OPEN_RESULT_FOOTER = "\nБаланс: <b>{tokens} B</b>"

CASES_INVENTORY_HEADER = "<b>🎒 Твой инвентарь (последние {limit})</b>"
CASES_INVENTORY_EMPTY = "Пока пусто — открой кейс, чтобы что-то тут появилось."
CASES_INVENTORY_LINE = "• {item_name} ({case_name}) — {value} B"

UPGRADER_HOME_HEADER = "<b>АПГРЕЙДЕР</b>"
UPGRADER_HOME_DISCLAIMER = (
    "Апгрейдер работает с брейнротами из твоего инвентаря: ставишь один, "
    "при удаче получаешь дороже, при неудаче ставка сгорает."
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

# --- Квесты ---
QUESTS_HEADER = "<b>КВЕСТЫ</b>"
QUESTS_BALANCE_LINE = "БАЛАНС: <b>{tokens} B</b>"
QUESTS_SCOPE_DAILY = "<b>ДНЕВНЫЕ</b>"
QUESTS_SCOPE_WEEKLY = "<b>НЕДЕЛЬНЫЕ</b>"
QUEST_ROW = "{title}\n{description}\n{progress}/{target} · Сброс через {reset}\n+{reward} B"
QUEST_CLAIMED_ROW = "{title} — ✅ забрано"
QUEST_NOT_READY_ALERT = "Квест ещё не выполнен."
QUEST_ALREADY_CLAIMED_ALERT = "Награда уже забрана."
QUEST_CLAIMED_ALERT = "Получено {reward} B!"

# --- Бонусы: общее ---
BONUSES_HEADER = "<b>БОНУСЫ</b>"
BONUSES_TAB_REFERRAL = "👥 Рефералы"
BONUSES_TAB_STAKING = "🔒 Стейкинг"

# --- Бонусы: рефералы ---
REFERRAL_HEADER = "<b>РЕФЕРАЛЫ</b>\nПриглашай друзей и получай процент с их депозитов"
REFERRAL_CODE_LINE = "Мой реферальный код: <code>{code}</code>"
REFERRAL_LINK_LINE = "Ссылка: {link}"
REFERRAL_TIER_LINE = "Тир: <b>{tier}</b> (комиссия {commission}%)"
REFERRAL_NEXT_TIER_LINE = "До {next_tier}: ещё {remaining} чел."
REFERRAL_MAX_TIER_LINE = "Максимальный тир достигнут."
REFERRAL_STATS = "Рефералов: <b>{count}</b>\nЗаработано всего: <b>{earned} B</b>\nКомиссия: <b>{commission}%</b>"

# --- Бонусы: стейкинг ---
STAKING_HEADER = "<b>СТЕЙКИНГ БАЛАНСА</b>\nОдин активный стейк на аккаунт"
STAKING_DESCRIPTION = (
    "Заморозь B на срок и получи надбавку сверху. Забрать раньше срока нельзя. "
    "Минимум {min_amount} B."
)
STAKING_TIER_LABEL = "{label} — +{bonus}% ({days} дней)"
STAKING_ASK_AMOUNT = "Сколько заморозить? Минимум {min_amount} B, доступно {balance} B."
STAKING_AMOUNT_INVALID = "Введите целое число от {min_amount} до твоего баланса ({balance} B)."
STAKING_CONFIRM_TEXT = (
    "Заморозить <b>{amount} B</b> на {days} дней (+{bonus}%)?\n"
    "К получению по окончании срока: <b>{payout} B</b>."
)
STAKING_ALREADY_ACTIVE = "У тебя уже есть активный стейк — сначала забери его."
STAKING_STARTED_TEXT = "🔒 Заморожено {amount} B на {days} дней. Готово к получению: {matures_at}."
STAKING_NO_ACTIVE = "Активного стейка нет."
STAKING_ACTIVE_INFO = (
    "Заморожено: <b>{amount} B</b>\nСрок: {days} дней (+{bonus}%)\n"
    "Готово к получению: {matures_at}\nК выплате: <b>{payout} B</b>"
)
STAKING_NOT_MATURED_ALERT = "Ещё рано — заберёшь после {matures_at}."
STAKING_CLAIMED_TEXT = "✅ Стейк завершён! Начислено <b>{payout} B</b> ({amount} B тело + {bonus} B бонус)."
STAKING_MY_STATS = (
    "<b>МОЙ СТЕЙКИНГ</b>\nЗаморожено за всё время: {total_frozen} B\n"
    "Заработано сверху: {total_bonus} B\nСтейков завершено: {completed_count}"
)

# --- Батл ---
BATTLE_HOME_HEADER = "<b>БАТЛ</b>"
BATTLE_HOME_DISCLAIMER = (
    "1×1 против бота-соперника за B: оба открывают один кейс, "
    "у кого дороже дроп — забирает оба предмета, ничья — возврат входа."
)
BATTLE_PICK_CASE_HINT = "Выбери кейс для батла:"
BATTLE_NO_CASES = "Пока нет ни одного кейса с подтверждённым пулом для батла."
BATTLE_NOT_ENOUGH_TOKENS = "Недостаточно B. Вход {cost} B, у тебя {balance} B."
BATTLE_RESULT_HEADER = "<b>{case_name}</b> — батл против бота"
BATTLE_RESULT_PLAYER_LINE = "Ты: {name} — {value} B"
BATTLE_RESULT_BOT_LINE = "Бот: {name} — {value} B"
BATTLE_RESULT_WIN = "🎉 <b>Победа!</b> Забираешь оба предмета."
BATTLE_RESULT_LOSS = "💥 <b>Поражение.</b> Вход потерян."
BATTLE_RESULT_TIE = "🤝 <b>Ничья.</b> Вход возвращён."

# --- Розыгрыши ---
GIVEAWAYS_HEADER = "<b>РОЗЫГРЫШИ</b>"
GIVEAWAYS_EMPTY = "Активных розыгрышей пока нет."
GIVEAWAY_ROW = "🏆 <b>{title}</b>\nПриз: {prize}\nУчастников: {entries}\nЗавершится: {ends_at}"
GIVEAWAY_ALREADY_JOINED = "Ты уже участвуешь в этом розыгрыше."
GIVEAWAY_JOINED = "✅ Ты участвуешь в розыгрыше «{title}»!"
GIVEAWAY_ALREADY_RESOLVED = "Этот розыгрыш уже завершён."
GIVEAWAY_WINNER_ANNOUNCEMENT = "🏆 Розыгрыш «{title}» завершён! Победитель: {winner}"
GIVEAWAY_NO_WINNER_ANNOUNCEMENT = "🏆 Розыгрыш «{title}» завершён — участников не было."

# --- FAQ ---
FAQ_HEADER = "<b>FAQ</b>"
FAQ_ENTRIES = [
    ("Что такое B?", "B — единый баланс BrainCore. Пополняется брейнротами, гирсами или Telegram Stars; на него открываются кейсы и батлы, туда же идут продажи дропа."),
    ("Можно ли вывести B в деньги или предметы?", "Нет, обратного вывода из бота не предусмотрено — только приём пополнений."),
    ("Как пополнить баланс?", "В Mini App нажми на кошелёк: брейнроты и гирсы — заявка, которую проверяет модератор; Stars — оплата прямо в Telegram, B приходят сразу. Раз в 12 часов есть бесплатный кейс."),
    ("Как работает депозит предметами?", "Выбираешь предметы в обменнике, указываешь ник, заявку проверяет модератор — после подтверждения B зачисляется на баланс."),
    ("Что внутри кейсов?", "Только реальные брейнроты Steal a Brainrot тиров Secret и OG. Чем дороже брейнрот — тем реже он выпадает."),
    ("Какой шанс в апгрейдере?", "Шанс = ценность вклада / ценность цели. Цели — только с шансом от 75% до 1%. Исход решает сервер до начала анимации."),
]

