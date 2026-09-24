"""Инварианты контента кейсов: только реальные брейнроты со скриншотов,
только Secret/OG, у каждого есть официальный рендер, цена выведена из пула."""
from __future__ import annotations

from pathlib import Path

from bot.data.brainrot_roster import ROSTER, ROSTER_BY_NAME, Rarity
from bot.data.seed_cases import CASE_THEMES, SEED_CASES, TARGET_RTP, expected_value, price_for

ASSETS = Path(__file__).resolve().parent.parent / "webapp" / "static" / "assets" / "brainrots"


def test_roster_only_top_tiers():
    assert {b.rarity for b in ROSTER} <= {Rarity.SECRET, Rarity.OG}


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
            entry = ROSTER_BY_NAME[item.name]
            assert item.value == entry.value
            assert item.rarity == entry.rarity.value


def test_case_price_is_derived_from_pool():
    for case in SEED_CASES:
        values = [i.value for i in case.items]
        assert case.price_tokens == price_for(values)
        assert case.price_tokens >= expected_value(values) / TARGET_RTP


def test_every_case_has_theme_and_unique_code():
    codes = [c.code for c in SEED_CASES]
    assert len(codes) == len(set(codes))
    assert set(codes) == set(CASE_THEMES)
