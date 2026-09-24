"""Варианты вывода: сам брейнрот из стока или обмен + доплата в B."""
from __future__ import annotations

from bot.services.withdraw_service import options_for


def test_direct_when_in_stock():
    (opt,) = options_for("Kraken", 3077, {"Kraken": 1, "Garama and Madundung": 100})
    assert opt.items == [("Kraken", 3077, 1)] and opt.topup == 0


def test_exchange_for_many_cheaper_with_topup():
    opts = options_for("Dragon Cannelloni", 973, {"Garama and Madundung": 100})
    (opt,) = opts
    assert opt.items == [("Garama and Madundung", 41, 23)]  # 23 × 41 = 943
    assert opt.topup == 973 - 943


def test_exchange_limited_by_stock_and_sorted_by_topup():
    opts = options_for("Dragon Cannelloni", 973, {"Garama and Madundung": 5, "La Casa Boo": 1, "Kraken": 3})
    assert all(n != "Kraken" for o in opts for n, *_ in o.items)  # дороже выводимого не даём
    assert opts[0].topup == min(o.topup for o in opts)
    assert any(len(o.items) > 1 for o in opts)  # смешанный набор


def test_no_options_when_stock_empty():
    assert options_for("Kraken", 3077, {}) == []
