"""Тесты логики стейкинга: тарифы, срок погашения, выплата."""
from __future__ import annotations

from datetime import datetime, timedelta

from bot.database.models import StakePosition
from bot.services.staking_service import STAKE_TIERS, bonus_amount, is_matured, payout_amount, tier_by_term


def make_position(amount: int, term_days: int, bonus_percent: float, matures_at: datetime) -> StakePosition:
    return StakePosition(amount=amount, term_days=term_days, bonus_percent=bonus_percent, matures_at=matures_at)


def test_stake_tiers_match_screenshot():
    assert [(t.term_days, t.bonus_percent) for t in STAKE_TIERS] == [(7, 10.0), (14, 20.0), (30, 42.9)]


def test_tier_by_term_found_and_missing():
    assert tier_by_term(7).bonus_percent == 10.0
    assert tier_by_term(99) is None


def test_is_matured_before_and_after_deadline():
    now = datetime(2026, 9, 23, 12, 0)
    future = make_position(100, 7, 10.0, matures_at=now + timedelta(days=1))
    past = make_position(100, 7, 10.0, matures_at=now - timedelta(seconds=1))
    assert is_matured(future, now) is False
    assert is_matured(past, now) is True


def test_bonus_and_payout_amount():
    position = make_position(1000, 30, 42.9, matures_at=datetime.utcnow())
    assert bonus_amount(position) == 429
    assert payout_amount(position) == 1429
