"""Тесты логики квестов: ключ периода и форматирование обратного отсчёта."""
from __future__ import annotations

from datetime import datetime, timedelta

from bot.database.models import QuestScope
from bot.services.quest_service import format_timedelta, period_key, time_until_reset


def test_period_key_daily_is_isodate():
    now = datetime(2026, 9, 23, 12, 0)
    assert period_key(QuestScope.DAILY, now) == "2026-09-23"


def test_period_key_daily_changes_next_day():
    day1 = period_key(QuestScope.DAILY, datetime(2026, 9, 23, 23, 59))
    day2 = period_key(QuestScope.DAILY, datetime(2026, 9, 24, 0, 1))
    assert day1 != day2


def test_period_key_weekly_stable_within_same_iso_week():
    monday = period_key(QuestScope.WEEKLY, datetime(2026, 9, 21, 1, 0))
    sunday = period_key(QuestScope.WEEKLY, datetime(2026, 9, 27, 23, 0))
    assert monday == sunday


def test_period_key_weekly_changes_next_week():
    week1 = period_key(QuestScope.WEEKLY, datetime(2026, 9, 27, 23, 0))
    week2 = period_key(QuestScope.WEEKLY, datetime(2026, 9, 28, 1, 0))
    assert week1 != week2


def test_time_until_reset_daily_is_less_than_24h():
    now = datetime(2026, 9, 23, 15, 10)
    delta = time_until_reset(QuestScope.DAILY, now)
    assert timedelta(0) < delta <= timedelta(hours=24)


def test_time_until_reset_weekly_points_to_next_monday():
    monday = datetime(2026, 9, 21, 0, 0)  # понедельник
    delta = time_until_reset(QuestScope.WEEKLY, monday)
    assert delta == timedelta(days=7)


def test_format_timedelta_hours_and_minutes():
    assert format_timedelta(timedelta(hours=8, minutes=49)) == "8ч 49м"
    assert format_timedelta(timedelta(minutes=5)) == "5м"
    assert format_timedelta(timedelta(seconds=-30)) == "0м"
