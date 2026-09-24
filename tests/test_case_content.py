"""Инварианты контента кейсов: только реальные брейнроты ростера (плюс
монеты в бесплатных/эконом-кейсах), у каждого есть официальный рендер, цена
выведена из пула, рыночные кейсы собраны строго по рыночному срезу."""
from __future__ import annotations

from pathlib import Path

from bot.data.brainrot_roster import POOR_ROSTER, ROSTER, ROSTER_BY_NAME, Rarity
from bot.data.coins import COIN_RARITY, coin_amount
from bot.data.market import DEMAND, TIER
from bot.data.seed_cases import CASE_THEMES, SEED_CASES, SEED_CASES_BY_CODE, TARGET_RTP, expected_value, price_for
from bot.database.models import CaseCategory

ASSETS = Path(__file__).resolve().parent.parent / "webapp" / "static" / "assets" / "brainrots"


def test_no_brainrot_god_and_top_roster_is_secret_or_og():
    assert Rarity.BRAINROT_GOD not in {b.rarity for b in ROSTER}
    poor = {b.name for b in POOR_ROSTER}
    assert {b.rarity for b in ROSTER if b.name not in poor} <= {Rarity.SECRET, Rarity.OG}


def test_market_snapshot_only_for_roster():
    assert set(TIER) <= set(ROSTER_BY_NAME) and set(DEMAND) <= set(ROSTER_BY_NAME)


def test_market_cases_follow_snapshot():
    assert all(DEMAND[i.name] in ("Very High", "High") for i in SEED_CASES_BY_CODE["market_hype"].items)
    assert all(DEMAND[i.name] == "Very Low" for i in SEED_CASES_BY_CODE["market_illiquid"].items)
    assert all(TIER[i.name] == "T0" for i in SEED_CASES_BY_CODE["market_blue_chips"].items)
    assert all(TIER[i.name] in ("T1", "T2") for i in SEED_CASES_BY_CODE["market_runners"].items)


def test_every_roster_brainrot_has_official_render():
    missing = [b.name for b in ROSTER if not (ASSETS / f"{b.slug}.webp").exists()]
    assert missing == []


def test_no_orphan_images():
    slugs = {b.slug for b in ROSTER}
    orphans = [p.name for p in ASSETS.glob("*.webp") if p.stem not in slugs]
    assert orphans == []


def test_cases_contain_only_roster_brainrots_with_roster_values():
    for case in SEED_CASES:
        for item in case.items:
            if item.rarity == COIN_RARITY:
                assert coin_amount(item.name) == item.value
                assert case.category in (CaseCategory.FREE, CaseCategory.REFERRAL, CaseCategory.ECONOMY)
                continue
            entry = ROSTER_BY_NAME[item.name]
            assert item.value == entry.value
            assert item.rarity == entry.rarity.value


def test_case_price_is_derived_from_pool():
    for case in SEED_CASES:
        values = [i.value for i in case.items]
        if case.category == CaseCategory.FREE:
            assert case.price_tokens == 0
            continue
        assert case.price_tokens == price_for(values)
        assert case.price_tokens >= expected_value(values) / TARGET_RTP


def test_every_case_has_theme_and_unique_code():
    codes = [c.code for c in SEED_CASES]
    assert len(codes) == len(set(codes))
    assert set(codes) == set(CASE_THEMES)
