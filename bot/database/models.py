"""Модели БД."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class AppMeta(Base):
    """Key-value хранилище служебных отметок (например, версия сид-контента кейсов)."""

    __tablename__ = "app_meta"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[str] = mapped_column(String(256))


class DepositCategory(str, enum.Enum):
    BRAINROT = "brainrot"
    HIRSY = "hirsy"


class DepositRequestStatus(str, enum.Enum):
    QUEUED = "queued"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"  # игрок сам отменил, пока ждал


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    balance: Mapped[int] = mapped_column(Integer, default=0)
    # Устарело: была отдельная демо-валюта 🎫. Демо-режим убран, всё идёт
    # через balance (B); колонка оставлена, чтобы не ломать старые SQLite-базы
    # (NOT NULL без server_default — без неё не вставить нового пользователя).
    game_tokens: Mapped[int] = mapped_column(Integer, default=0)
    referral_code: Mapped[str] = mapped_column(String(16), unique=True)
    referred_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    referral_earned_total: Mapped[int] = mapped_column(Integer, default=0)
    # Партнёр: персональный % реферальной комиссии, выданный админом;
    # перекрывает тир по числу рефералов. None — обычный пользователь.
    partner_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Бонус % к каждому пополнению — даёт активированный партнёрский код.
    deposit_bonus_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    partner_code_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    free_case_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Подкрутка шансов админом (×, None — выключена): кейсы, батл, апгрейдер.
    luck: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DepositItem(Base):
    __tablename__ = "deposit_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[DepositCategory] = mapped_column(SAEnum(DepositCategory))
    name: Mapped[str] = mapped_column(String(128))
    emoji: Mapped[str] = mapped_column(String(16), default="🧩")
    price_b: Mapped[int] = mapped_column(Integer)
    min_qty: Mapped[int] = mapped_column(Integer, default=1)
    hot_stock_left: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class DepositRequest(Base):
    __tablename__ = "deposit_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    category: Mapped[DepositCategory] = mapped_column(SAEnum(DepositCategory))
    items: Mapped[dict] = mapped_column(JSON)  # {"<item_id>": qty}
    buff: Mapped[str | None] = mapped_column(String(32), nullable=True)
    game_nickname: Mapped[str] = mapped_column(String(64))
    total_b: Mapped[int] = mapped_column(Integer)
    # Код при заявке (промо/партнёрский/реферальный) и его бонус к зачислению, %.
    promo_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    bonus_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[DepositRequestStatus] = mapped_column(
        SAEnum(DepositRequestStatus), default=DepositRequestStatus.PENDING
    )
    admin_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship()


class CaseCategory(str, enum.Enum):
    """Коллекции кейсов по уровню ставки (см. bot/data/seed_cases.py)."""

    STARTER = "starter"
    SIGNATURE = "signature"
    APEX = "apex"
    # Не продаётся: открывается только бесплатными открытиями (партнёрский код).
    REFERRAL = "referral"
    FREE = "free"  # бесплатно раз в N часов, после подписки на канал (settings_service)
    ECONOMY = "economy"  # дешёвые кейсы с «нищими» брейнротами и монетами


class Case(Base):
    """Кейс из каталога (bot/data/seed_cases.py).

    Название/тема кейса — собственные, цена выводится из содержимого
    (средний дроп / TARGET_RTP), см. докстринг seed_cases.
    """

    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[CaseCategory] = mapped_column(SAEnum(CaseCategory))
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    price_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    item_count_label: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str | None] = mapped_column(String(256), nullable=True)
    is_openable: Mapped[bool] = mapped_column(default=False)
    # Денормализовано при сидировании (макс. rarity среди items) — чтобы
    # карточка кейса в общем списке могла подсветиться цветом старшего
    # возможного дропа без N+1 запроса за items на каждую карточку.
    best_rarity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # Имя самого ценного предмета из дроп-пула — «джекпот», который
    # показывается внутри артефакта кейса на карточке и на странице открытия.
    top_item_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class CaseItem(Base):
    """Один возможный дроп из кейса — реальный персонаж Steal a Brainrot.

    name/rarity — из bot.data.brainrot_roster (сверено с вики игры), value —
    ценность в B со скриншотов пользователя. Вес выпадения ∝ 1/value,
    см. bot/services/cases_service.py.
    """

    __tablename__ = "case_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    name: Mapped[str] = mapped_column(String(128))
    value: Mapped[int] = mapped_column(Integer)
    rarity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class InventoryItem(Base):
    """Предмет, выпавший пользователю из кейса (коллекционная запись, не валюта)."""

    __tablename__ = "inventory_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id"), nullable=True)
    case_name: Mapped[str] = mapped_column(String(128))
    item_name: Mapped[str] = mapped_column(String(128))
    value: Mapped[int] = mapped_column(Integer)
    rarity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    obtained_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class QuestScope(str, enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"


class Quest(Base):
    """Задание из раздела «Квесты».

    Сид-данные — bot/data/seed_quests.py.
    target_type: "open_case:<code кейса>" | "upgrader_spin".
    """

    __tablename__ = "quests"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    scope: Mapped[QuestScope] = mapped_column(SAEnum(QuestScope))
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str] = mapped_column(String(256))
    target_type: Mapped[str] = mapped_column(String(64))
    target_count: Mapped[int] = mapped_column(Integer, default=1)
    reward_tokens: Mapped[int] = mapped_column(Integer)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class UserQuestProgress(Base):
    """Прогресс пользователя по квесту за текущий период (день/неделя).

    period_key — ключ периода («2026-09-23» для дневных, «2026-W39» для
    недельных), при смене периода прогресс логически обнуляется: старые
    записи просто перестают совпадать с текущим period_key и создаётся новая.
    """

    __tablename__ = "user_quest_progress"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    quest_id: Mapped[int] = mapped_column(ForeignKey("quests.id"))
    period_key: Mapped[str] = mapped_column(String(16))
    progress_count: Mapped[int] = mapped_column(Integer, default=0)
    claimed: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class StakeStatus(str, enum.Enum):
    ACTIVE = "active"
    COMPLETED = "completed"


class StakePosition(Base):
    """Стейкинг реального баланса B (раздел «Бонусы»).

    [ПОДТВЕРЖДЕНО СКРИНШОТОМ] 3 тарифа: неделя +10%, 2 недели +20%, месяц
    +42.9%; минимум 100 B; тело возвращается по частям (по одной в сутки
    после срока), надбавка — только если досидеть до конца.
    [ЛОГИЧЕСКИ ПРЕДПОЛОЖЕНО, упрощение] Заморозка выплачивается одним
    платежом (тело + бонус) сразу после наступления matures_at, а не
    подневным капанием — планировщика для фоновых ежедневных выплат в
    этом процессе нет, см. bot/services/staking_service.py.
    """

    __tablename__ = "stake_positions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[int] = mapped_column(Integer)
    term_days: Mapped[int] = mapped_column(Integer)
    bonus_percent: Mapped[float] = mapped_column()
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    matures_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[StakeStatus] = mapped_column(SAEnum(StakeStatus), default=StakeStatus.ACTIVE)


class GiveawayStatus(str, enum.Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"


class Giveaway(Base):
    """Розыгрыш из раздела «Розыгрыши».

    [НЕИЗВЕСТНО] Интерфейс раздела ни разу не был на скриншотах — по
    согласованию с пользователем сделано по собственному усмотрению:
    администратор создаёт розыгрыш с призом и датой окончания, пользователи
    участвуют один раз, по истечении срока случайно выбирается победитель.
    """

    __tablename__ = "giveaways"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(128))
    prize_description: Mapped[str] = mapped_column(String(256))
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[GiveawayStatus] = mapped_column(SAEnum(GiveawayStatus), default=GiveawayStatus.ACTIVE)
    winner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_by_tg_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class GiveawayEntry(Base):
    __tablename__ = "giveaway_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    giveaway_id: Mapped[int] = mapped_column(ForeignKey("giveaways.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class StarsDeposit(Base):
    __tablename__ = "stars_deposits"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    stars_amount: Mapped[int] = mapped_column(Integer)
    promo_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # Сколько B зачислить — зафиксировано при создании счёта (курс + бонус за код).
    credited_b: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payload: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | paid
    telegram_charge_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class CaseCredit(Base):
    """Бесплатные открытия кейса, выданные админом или промокодом."""

    __tablename__ = "case_credits"
    __table_args__ = (UniqueConstraint("user_id", "case_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # code, а не id: id кейсов меняются при пересеве каталога.
    case_code: Mapped[str] = mapped_column(String(64))
    count: Mapped[int] = mapped_column(Integer, default=0)


class PromoKind(str, enum.Enum):
    TOKENS = "tokens"  # устарело: демо-фишек больше нет, такие промо начисляют B
    BALANCE = "balance"  # баланс B
    CASE = "case"  # бесплатные открытия кейса


class PromoCode(Base):
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    kind: Mapped[PromoKind] = mapped_column(SAEnum(PromoKind))
    amount: Mapped[int] = mapped_column(Integer)
    case_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_uses: Mapped[int] = mapped_column(Integer, default=1)
    uses: Mapped[int] = mapped_column(Integer, default=0)
    created_by_tg_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PromoRedemption(Base):
    __tablename__ = "promo_redemptions"
    __table_args__ = (UniqueConstraint("promo_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    promo_id: Mapped[int] = mapped_column(ForeignKey("promo_codes.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    redeemed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PartnerCode(Base):
    """Личный реф-код партнёра (выдаётся админом).

    Кто активирует код: становится рефералом партнёра, получает
    case_amount открытий кейса case_code и deposit_bonus_percent к каждому
    своему пополнению. Партнёр получает commission_percent с депозитов
    рефералов (хранится в User.partner_percent).
    """

    __tablename__ = "partner_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)
    deposit_bonus_percent: Mapped[float] = mapped_column(Float, default=0)
    case_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    case_amount: Mapped[int] = mapped_column(Integer, default=1)
    uses: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class WithdrawStock(Base):
    """Сток брейнротов для вывода: сколько штук каждого есть у админа.

    Меняет админ (+/− в Mini App); одобренные депозиты брейнротами
    пополняют его автоматически (bot/services/deposit_moderation.py).
    """

    __tablename__ = "withdraw_stock"

    name: Mapped[str] = mapped_column(String(128), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)


class WithdrawStatus(str, enum.Enum):
    QUEUED = "queued"  # ждёт своей очереди
    PENDING = "pending"  # в работе: админ кидает трейд
    DONE = "done"  # выдано (доплата зачислена)
    CANCELLED = "cancelled"  # отменено: брейнрот вернулся в инвентарь, сток — обратно


class WithdrawRequest(Base):
    """Заявка на вывод брейнрота из инвентаря.

    payout — что реально выдаётся из стока: [{"name", "value", "qty"}]
    (тот же брейнрот или обмен на другие примерно той же цены); topup_b —
    разница в B, которую бот зачислит на баланс при выдаче.
    """

    __tablename__ = "withdraw_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    item_name: Mapped[str] = mapped_column(String(128))
    item_value: Mapped[int] = mapped_column(Integer)
    item_rarity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    payout: Mapped[list] = mapped_column(JSON)
    topup_b: Mapped[int] = mapped_column(Integer, default=0)
    game_nickname: Mapped[str] = mapped_column(String(64))
    status: Mapped[WithdrawStatus] = mapped_column(SAEnum(WithdrawStatus), default=WithdrawStatus.PENDING)
    admin_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class SupportMessage(Base):
    """Сообщение поддержки у админов: по реплаю админа на него бот понимает,
    какому игроку отправить ответ."""

    __tablename__ = "support_links"  # старая support_messages (с unique chat+message) не используется

    id: Mapped[int] = mapped_column(primary_key=True)
    bot_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # какой бот переслал (основной / поддержки)
    chat_id: Mapped[int] = mapped_column(BigInteger)
    message_id: Mapped[int] = mapped_column(BigInteger)
    user_tg_id: Mapped[int] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
