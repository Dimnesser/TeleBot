"""Логика квестов: ключ периода (для сброса) и учёт прогресса."""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import Quest, QuestScope, User
from bot.database.repo import quests as quests_repo


def period_key(scope: QuestScope, now: datetime | None = None) -> str:
    now = now or datetime.utcnow()
    if scope == QuestScope.DAILY:
        return now.date().isoformat()
    iso_year, iso_week, _ = now.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def time_until_reset(scope: QuestScope, now: datetime | None = None) -> timedelta:
    now = now or datetime.utcnow()
    today_midnight = datetime(now.year, now.month, now.day)
    if scope == QuestScope.DAILY:
        return today_midnight + timedelta(days=1) - now
    days_until_monday = (7 - now.weekday()) % 7 or 7
    return today_midnight + timedelta(days=days_until_monday) - now


def format_timedelta(delta: timedelta) -> str:
    total_minutes = max(int(delta.total_seconds() // 60), 0)
    hours, minutes = divmod(total_minutes, 60)
    if hours:
        return f"{hours}ч {minutes}м"
    return f"{minutes}м"


async def record_progress(session: AsyncSession, user: User, target_type: str) -> None:
    """Двигает прогресс всех квестов с данным target_type для пользователя.

    Вызывается из других разделов (кейсы, апгрейдер) сразу после успешного
    действия — сам по себе не начисляет награду, только считает прогресс;
    забрать награду нужно явно кнопкой «ЗАБРАТЬ» на экране квестов.
    """
    quests = await quests_repo.list_quests_by_target(session, target_type)
    for quest in quests:
        key = period_key(quest.scope)
        progress = await quests_repo.get_or_create_progress(session, user, quest, key)
        if progress.claimed or progress.progress_count >= quest.target_count:
            continue
        progress.progress_count = min(progress.progress_count + 1, quest.target_count)
        await session.commit()
