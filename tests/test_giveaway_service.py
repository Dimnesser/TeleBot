"""Тесты логики розыгрышей: проверка истечения срока."""
from __future__ import annotations

from datetime import datetime, timedelta

from bot.database.models import Giveaway
from bot.services.giveaway_service import is_expired


def make_giveaway(ends_at: datetime) -> Giveaway:
    return Giveaway(title="Test", prize_description="Prize", ends_at=ends_at)


def test_is_expired_false_before_deadline():
    now = datetime(2026, 9, 23, 12, 0)
    giveaway = make_giveaway(now + timedelta(hours=1))
    assert is_expired(giveaway, now) is False


def test_is_expired_true_after_deadline():
    now = datetime(2026, 9, 23, 12, 0)
    giveaway = make_giveaway(now - timedelta(seconds=1))
    assert is_expired(giveaway, now) is True


def test_is_expired_true_exactly_at_deadline():
    now = datetime(2026, 9, 23, 12, 0)
    giveaway = make_giveaway(now)
    assert is_expired(giveaway, now) is True
