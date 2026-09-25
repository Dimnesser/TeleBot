"""Инварианты контента кейсов: только реальные брейнроты ростера (плюс
монеты в бесплатных кейсах), у каждого есть официальный рендер, цена
выведена из пула, кейсы идут лестницей цен."""
from __future__ import annotations

from pathlib import Path

from bot.data.brainrot_roster import ROSTER, ROSTER_BY_NAME, Rarity
from bot.data.coins import COIN_RARITY, coin_amount
from bot.data.market import DEMAND, TIER
from bot.data.seed_cases import (
    CASE_THEMES, PAYBACK_BAND, SEED_CASES, SEED_CASES_BY_CODE, TARGET_RTP, TOP_CHANCE_BAND, expected_value,
)
from bot.database.models import CaseCategory

ASSETS = Path(__file__).resolve().parent.parent / "webapp" / "static" / "assets" / "brainrots"


def test_roster_only_secret_and_og():
    assert {b.rarity for b in ROSTER} <= {Rarity.SECRET, Rarity.OG}


def test_every_case_has_a_3d_render():
    renders = ASSETS.parent / "cases"
    assert [c.code for c in SEED_CASES if not (renders / f"{c.code}.webp").exists()] == []


def test_market_snapshot_only_for_roster():
    assert set(TIER) <= set(ROSTER_BY_NAME) and set(DEMAND) <= set(ROSTER_BY_NAME)


def test_paid_cases_form_a_price_ladder_and_all_in_is_top():
    main = sorted((c for c in SEED_CASES if c.category == CaseCategory.STARTER), key=lambda c: c.sort_order)
    all_in = [c for c in SEED_CASES if c.category == CaseCategory.APEX]
    assert [c.price_tokens for c in main] == sorted(c.price_tokens for c in main)
    assert min(c.price_tokens for c in all_in) > max(c.price_tokens for c in main)
    assert min(c.price_tokens for c in main) < 30  # дешёвые кейсы — как на референсе (~19–30)


def test_paid_cases_hold_only_withdrawable_brainrots_or_coins():
    """В платных кейсах — брейнроты из каталога пополнения (от 41 B, их можно
    вывести) и монеты B; мелочи вне каталога нет."""
    for case in SEED_CASES:
        assert SEED_CASES_BY_CODE["free"].price_tokens == 0
        if case.category in (CaseCategory.FREE, CaseCategory.REFERRAL):
            continue
        for item in case.items:
            assert item.rarity == COIN_RARITY or item.value >= 41, (case.code, item.name)


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
                continue
            entry = ROSTER_BY_NAME[item.name]
            assert item.value == entry.value
            assert item.rarity == entry.rarity.value


def test_paid_cases_are_balanced():
    """Каждый платный кейс окупается в 25–40% открытий, возвращает ~94%
    цены, топ выпадает в 0.5–8%; веса — доли, в сумме 1."""
    lo, hi = PAYBACK_BAND
    for case in SEED_CASES:
        if case.category in (CaseCategory.FREE, CaseCategory.REFERRAL):
            continue
        weights = [i.weight for i in case.items]
        assert all(w and w > 0 for w in weights) and abs(sum(weights) - 1) < 1e-3, case.code
        payback = sum(i.weight for i in case.items if i.value >= case.price_tokens)
        rtp = sum(i.value * i.weight for i in case.items) / case.price_tokens
        top = max(case.items, key=lambda i: i.value)
        assert lo <= payback <= hi, (case.code, payback)
        assert 0.88 <= rtp <= TARGET_RTP + 1e-6, (case.code, rtp)
        assert TOP_CHANCE_BAND[0] <= top.weight <= TOP_CHANCE_BAND[1], (case.code, top.weight)


def test_free_case_lets_you_climb():
    """Бесплатный кейс в среднем даёт не меньше ~80% цены самого дешёвого кейса."""
    free = SEED_CASES_BY_CODE["free"]
    cheapest = min(c.price_tokens for c in SEED_CASES if c.category == CaseCategory.STARTER)
    assert expected_value([i.value for i in free.items]) >= cheapest * 0.8


def test_every_case_has_theme_and_unique_code():
    codes = [c.code for c in SEED_CASES]
    assert len(codes) == len(set(codes))
    assert set(codes) == set(CASE_THEMES)


def test_legacy_case_codes_point_to_existing_cases():
    from bot.database.engine import LEGACY_CASE_CODES

    assert set(LEGACY_CASE_CODES.values()) <= set(SEED_CASES_BY_CODE)


def test_legacy_coin_names_still_parse():
    from bot.data.coins import coin_amount

    assert coin_amount("🎫 5") == 5 and coin_amount("🪙 10") == 10 and coin_amount("67") is None


async def test_case_detail_survives_legacy_coin_rows():
    from webapp.api import _brainrot_json

    assert _brainrot_json("🎫 5", 5, "coins")["coins"] is True
    assert _brainrot_json("Unknown Thing", 7, "coins")["rarity"]  # неизвестный тир — без 500


def test_titan_is_the_most_expensive_case():
    titan = SEED_CASES_BY_CODE["titan"]
    assert titan.price_tokens == max(c.price_tokens or 0 for c in SEED_CASES)
