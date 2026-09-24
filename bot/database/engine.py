"""Инициализация БД и фабрика сессий."""
from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from bot.config import config
from bot.data.brainrot_roster import RARITY_ORDER, Rarity
from bot.data.coins import COIN_RARITY
from bot.data.seed_cases import CASES_CONTENT_VERSION, SEED_CASES, SEED_CASES_BY_CODE
from bot.data.seed_items import DEPOSIT_CATALOG_VERSION, SEED_ITEMS
from bot.data.seed_quests import SEED_QUESTS
from bot.database.models import (
    AppMeta,
    Base,
    Case,
    CaseCredit,
    CaseItem,
    DepositItem,
    GiveawayEntry,
    InventoryItem,
    PartnerCode,
    PromoCode,
    PromoRedemption,
    Quest,
    StakePosition,
    User,
    UserQuestProgress,
)

engine = create_async_engine(config.database_url)
async_session: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, expire_on_commit=False)

logger = logging.getLogger(__name__)

CASES_VERSION_KEY = "cases_content_version"
DEPOSIT_VERSION_KEY = "deposit_catalog_version"
# Смена id — ещё один полный откат прогресса. Не менять без явной просьбы.
PROGRESS_RESET_KEY = "progress_reset"
PROGRESS_RESET_ID = "2026-09-24-real-balance"

# Коды кейсов из прошлых версий каталога → ближайший кейс текущего. Нужны,
# чтобы уже выданные открытия, промокоды и партнёрские коды не «повисли» на
# исчезнувшем кейсе после пересева.
LEGACY_CASE_CODES = {
    # v12–13
    "referral_gift": "referral", "free_handout": "free",
    "nonna_kitchen": "fastfood", "ghost_lantern": "boo", "hybrid_lab": "crystal", "combo_vault": "safe",
    "dragon_forge": "dragon", "abyss_dive": "capitano", "party_popper": "party", "og_throne": "og",
    "market_hype": "legend", "market_blue_chips": "crystal", "market_runners": "party", "market_illiquid": "phantom",
    "eco_cardboard": "tirili", "eco_bin": "tirili", "eco_lunchbox": "tirili", "eco_toolbox": "tirili",
    "eco_piggy": "tirili", "eco_sahur": "tirili", "eco_mystery": "tirili", "eco_first_secret": "capitano",
    # v14
    "sandbox": "tirili", "sahur": "tirili", "crocodilo": "tirili", "sixseven": "tirili", "secret": "capitano",
    "techno": "crystal", "griffin": "dragon", "sweet": "fastfood",
}


def _ensure_sqlite_dir(database_url: str) -> None:
    if not database_url.startswith("sqlite"):
        return
    path_part = database_url.split("///", 1)[-1]
    if path_part and path_part != ":memory:":
        Path(path_part).parent.mkdir(parents=True, exist_ok=True)


async def init_db() -> None:
    _ensure_sqlite_dir(config.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _migrate_add_missing_columns()
    await _reset_progress_once()
    await _seed_items_reconcile()
    await _seed_cases_reconcile()
    await _seed_quests_if_empty()
    await load_granted_admins()


async def load_granted_admins() -> None:
    """Выданные владельцем админы — в память для синхронного is_admin."""
    from bot.config import set_granted_admins
    from bot.database.models import AdminGrant

    async with async_session() as session:
        set_granted_admins((await session.execute(select(AdminGrant.tg_id))).scalars().all())


async def _migrate_add_missing_columns() -> None:
    """Лёгкая ad-hoc миграция для SQLite: ADD COLUMN, если её ещё нет.

    В проекте нет полноценного миграционного инструмента (Alembic и т.п.) —
    для демо-масштаба этого бота ALTER TABLE ADD COLUMN на старте процесса
    достаточно и не требует ручных шагов при обновлении с прошлых версий.
    """
    if not config.database_url.startswith("sqlite"):
        return
    columns_to_add = [
        ("case_items", "rarity", "VARCHAR(16)"),
        ("inventory_items", "rarity", "VARCHAR(16)"),
        ("cases", "best_rarity", "VARCHAR(16)"),
        ("cases", "top_item_name", "VARCHAR(128)"),
        ("users", "partner_percent", "FLOAT"),
        ("users", "deposit_bonus_percent", "FLOAT"),
        ("users", "partner_code_id", "INTEGER"),
        ("users", "free_case_at", "DATETIME"),
        ("stars_deposits", "credited_b", "INTEGER"),
        ("users", "luck", "FLOAT"),
        ("deposit_requests", "promo_code", "VARCHAR(32)"),
        ("deposit_requests", "bonus_percent", "FLOAT"),
    ]
    async with engine.begin() as conn:
        for table, column, coltype in columns_to_add:
            result = await conn.execute(text(f"PRAGMA table_info({table})"))
            existing = {row[1] for row in result.fetchall()}
            if column not in existing:
                await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}"))


async def _seed_items_reconcile() -> None:
    """Каталог приёма депозитов = SEED_ITEMS (версия DEPOSIT_CATALOG_VERSION).

    Строки не удаляются — заявки хранят id предметов: совпавшие по
    (категория, имя) обновляются, новые добавляются, пропавшие из сида
    выключаются (is_active=False).
    """
    async with async_session() as session:
        version = (await session.execute(select(AppMeta.value).where(AppMeta.key == DEPOSIT_VERSION_KEY))).scalar_one_or_none()
        if version == DEPOSIT_CATALOG_VERSION:
            return
        existing = {(i.category, i.name): i for i in (await session.execute(select(DepositItem))).scalars()}
        wanted = set()
        for seed in SEED_ITEMS:
            wanted.add((seed.category, seed.name))
            item = existing.get((seed.category, seed.name)) or DepositItem(category=seed.category, name=seed.name)
            item.emoji, item.price_b, item.min_qty = seed.emoji, seed.price_b, seed.min_qty
            item.hot_stock_left, item.sort_order, item.is_active = seed.hot_stock_left, seed.sort_order, True
            session.add(item)
        for key, item in existing.items():
            if key not in wanted:
                item.is_active = False
        await session.merge(AppMeta(key=DEPOSIT_VERSION_KEY, value=DEPOSIT_CATALOG_VERSION))
        await session.commit()


async def _reset_progress_once() -> None:
    """Разовый откат всего игрового прогресса при переходе с демо-режима на
    настоящий баланс (PROGRESS_RESET_ID): балансы, инвентарь, квесты, стейкинг,
    участия в розыгрышах, выданные открытия и активации промокодов. Аккаунты,
    рефералы, партнёрки, промокоды и история депозитов остаются. Перед
    откатом файл SQLite копируется рядом (…-before-reset-<время>.db).
    """
    async with async_session() as session:
        done = (await session.execute(select(AppMeta.value).where(AppMeta.key == PROGRESS_RESET_KEY))).scalar_one_or_none()
        if done == PROGRESS_RESET_ID:
            return
        has_users = (await session.execute(select(User.id).limit(1))).scalar_one_or_none() is not None

    if has_users:
        _backup_sqlite("before-reset")
        async with async_session() as session:
            for model in (InventoryItem, UserQuestProgress, StakePosition, GiveawayEntry, CaseCredit, PromoRedemption):
                await session.execute(delete(model))
            await session.execute(update(PromoCode).values(uses=0))
            await session.execute(update(User).values(balance=0, game_tokens=0, free_case_at=None, referral_earned_total=0))
            await session.commit()
        logger.warning("Игровой прогресс всех игроков откатан (%s)", PROGRESS_RESET_ID)

    async with async_session() as session:
        await session.merge(AppMeta(key=PROGRESS_RESET_KEY, value=PROGRESS_RESET_ID))
        await session.commit()


def _backup_sqlite(tag: str) -> Path | None:
    # Путь берётся у движка, с которым реально работаем (в тестах — in-memory).
    if engine.url.get_backend_name() != "sqlite" or not engine.url.database or engine.url.database == ":memory:":
        return None
    path = Path(engine.url.database)
    if not path.exists():
        return None
    target = path.with_name(f"{path.stem}-{tag}-{datetime.utcnow():%Y%m%d-%H%M%S}{path.suffix}")
    shutil.copy2(path, target)
    logger.warning("Резервная копия БД: %s", target)
    return target


async def _seed_cases_reconcile() -> None:
    """Пересеивает каталог кейсов, если контент устарел (CASES_CONTENT_VERSION).

    В отличие от прежнего «only if empty», это переживает обновление ростера
    персонажей/цен без ручного вмешательства: поднял CASES_CONTENT_VERSION в
    bot/data/seed_cases.py — при следующем старте каталог кейсов
    пересобирается из SEED_CASES. Инвентарь пользователей не трогается:
    InventoryItem хранит своё собственное имя/цену/редкость на момент
    выигрыша, а не ссылку на живой каталог.
    """
    async with async_session() as session:
        result = await session.execute(select(AppMeta.value).where(AppMeta.key == CASES_VERSION_KEY))
        current_version = result.scalar_one_or_none()
        if current_version == CASES_CONTENT_VERSION:
            return

        await session.execute(delete(CaseItem))
        await session.execute(delete(Case))

        for seed_case in SEED_CASES:
            best_rarity = None
            top_item_name = None
            brainrots = [i for i in seed_case.items if i.rarity != COIN_RARITY]  # монеты — не персонажи
            if brainrots:
                best_index = max(
                    (RARITY_ORDER.index(Rarity(i.rarity)) for i in brainrots if i.rarity), default=None
                )
                best_rarity = RARITY_ORDER[best_index].value if best_index is not None else None
                top_item_name = max(brainrots, key=lambda i: i.value).name
            case = Case(
                category=seed_case.category,
                code=seed_case.code,
                name=seed_case.name,
                price_tokens=seed_case.price_tokens,
                item_count_label=seed_case.item_count_label,
                note=seed_case.note,
                is_openable=seed_case.is_openable,
                best_rarity=best_rarity,
                top_item_name=top_item_name,
                sort_order=seed_case.sort_order,
            )
            session.add(case)
            await session.flush()
            session.add_all(
                CaseItem(case_id=case.id, name=item.name, value=item.value, rarity=item.rarity, sort_order=i)
                for i, item in enumerate(seed_case.items)
            )

        await _remap_legacy_case_codes(session)

        if current_version is None:
            session.add(AppMeta(key=CASES_VERSION_KEY, value=CASES_CONTENT_VERSION))
        else:
            await session.execute(
                AppMeta.__table__.update().where(AppMeta.key == CASES_VERSION_KEY).values(value=CASES_CONTENT_VERSION)
            )
        await session.commit()


async def _remap_legacy_case_codes(session: AsyncSession) -> None:
    """Переносит открытия/промокоды/партнёрские коды со старых кодов кейсов."""
    for pc in (await session.execute(select(PartnerCode))).scalars():
        if pc.case_code in LEGACY_CASE_CODES:
            pc.case_code = LEGACY_CASE_CODES[pc.case_code]
    for promo in (await session.execute(select(PromoCode))).scalars():
        if promo.case_code in LEGACY_CASE_CODES:
            promo.case_code = LEGACY_CASE_CODES[promo.case_code]
    credits = (await session.execute(select(CaseCredit))).scalars().all()
    kept = {(c.user_id, c.case_code): c for c in credits if c.case_code not in LEGACY_CASE_CODES}
    for credit in credits:
        new_code = LEGACY_CASE_CODES.get(credit.case_code)
        if new_code is None:
            continue
        target = kept.get((credit.user_id, new_code))
        if target is None:
            credit.case_code = new_code
            kept[(credit.user_id, new_code)] = credit
        else:  # у игрока уже есть открытия нового кейса — складываем
            target.count += credit.count
            await session.delete(credit)
    await session.flush()


async def _seed_quests_if_empty() -> None:
    async with async_session() as session:
        result = await session.execute(select(Quest.id).limit(1))
        if result.scalar_one_or_none() is not None:
            await _retarget_stale_case_quests(session)
            return
        session.add_all(
            Quest(
                code=quest.code,
                scope=quest.scope,
                title=quest.title,
                description=quest.description,
                target_type=quest.target_type,
                target_count=quest.target_count,
                reward_tokens=quest.reward_tokens,
                sort_order=quest.sort_order,
            )
            for quest in SEED_QUESTS
        )
        await session.commit()


async def _retarget_stale_case_quests(session: AsyncSession) -> None:
    """Квест «открой кейс X», чей кейс исчез из каталога после пересева,
    переписывается на квест из SEED_QUESTS с тем же scope/sort_order (id и
    прогресс игроков сохраняются) — иначе его стало бы невозможно выполнить.
    """
    quests = (await session.execute(select(Quest))).scalars().all()
    changed = False
    for quest in quests:
        if not quest.target_type.startswith("open_case:"):
            continue
        if quest.target_type.split(":", 1)[1] in SEED_CASES_BY_CODE:
            continue
        seed = next((q for q in SEED_QUESTS if q.scope == quest.scope and q.sort_order == quest.sort_order), None)
        if seed is None:
            continue
        quest.code = seed.code
        quest.title = seed.title
        quest.description = seed.description
        quest.target_type = seed.target_type
        quest.target_count = seed.target_count
        quest.reward_tokens = seed.reward_tokens
        changed = True
    if changed:
        await session.commit()
