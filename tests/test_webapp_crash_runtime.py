"""Рантайм краша Mini App: приз-лестница, отсутствие ложных взрывов, итог раунда."""
from __future__ import annotations

from bot.data.brainrot_roster import ROSTER_BY_NAME
from webapp import crash_runtime as rt


def test_prize_is_best_roster_brainrot_within_budget():
    stake = ROSTER_BY_NAME["Cerberus"]  # 155
    name, value = rt.prize_for(stake.name, stake.value, 2.0)  # бюджет 310
    assert value <= 310
    assert value == max(b.value for b in ROSTER_BY_NAME.values() if b.value <= 310)
    assert name in ROSTER_BY_NAME


def test_prize_at_low_multiplier_is_the_stake_itself():
    stake = ROSTER_BY_NAME["Cerberus"]
    assert rt.prize_for(stake.name, stake.value, 1.01) == (stake.name, stake.value)


def test_prize_never_below_stake():
    for b in ROSTER_BY_NAME.values():
        for mult in (1.0, 1.3, 2.5, 10.0):
            assert rt.prize_for(b.name, b.value, mult)[1] >= b.value


def test_ladder_sorted_with_thresholds():
    stake = ROSTER_BY_NAME["Garama and Madundung"]
    ladder = rt.prize_ladder(stake.name, stake.value)
    assert ladder and [s["value"] for s in ladder] == sorted(s["value"] for s in ladder)
    for step in ladder:
        assert step["at"] == round(step["value"] / stake.value, 2)


def test_round_does_not_crash_before_its_point(monkeypatch):
    monkeypatch.setattr(rt, "generate_crash_point", lambda: 50.0)
    round_ = rt.start_round(1001, "Cerberus", 155)
    round_.start_time -= 20  # 20 секунд полёта: ×e^2 ≈ 7.4 < 50 — раунд ещё летит
    assert rt.poll(1001).outcome is None
    cashed = rt.cashout(1001)
    assert cashed.outcome == "cashed" and 7 < cashed.final_multiplier < 8


def test_crash_result_persists_until_next_round(monkeypatch):
    monkeypatch.setattr(rt, "generate_crash_point", lambda: 1.5)
    round_ = rt.start_round(1002, "Cerberus", 155)
    round_.start_time -= 30
    assert rt.poll(1002).outcome == "crashed"
    assert rt.poll(1002).final_multiplier == 1.5
    assert rt.cashout(1002) is None
