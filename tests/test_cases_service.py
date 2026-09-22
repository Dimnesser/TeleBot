"""Тесты логики открытия кейсов: вес дропа и стоимость."""
from __future__ import annotations

from collections import Counter

from bot.database.models import Case, CaseCategory, CaseItem
from bot.services.cases_service import draw_items, item_weight, total_cost


def make_case(price: int | None) -> Case:
    return Case(id=1, category=CaseCategory.CASES, code="test", name="Test Case", price_tokens=price)


def make_item(item_id: int, value: int) -> CaseItem:
    return CaseItem(id=item_id, case_id=1, name=f"Item {item_id}", value=value)


def test_total_cost_scales_with_quantity():
    case = make_case(price=100)
    assert total_cost(case, 1) == 100
    assert total_cost(case, 5) == 500


def test_total_cost_none_when_price_unknown():
    case = make_case(price=None)
    assert total_cost(case, 3) is None


def test_item_weight_is_inverse_of_value():
    cheap = make_item(1, value=10)
    expensive = make_item(2, value=1000)
    assert item_weight(cheap) > item_weight(expensive)


def test_draw_items_returns_requested_quantity():
    items = [make_item(1, 100), make_item(2, 200), make_item(3, 300)]
    result = draw_items(items, quantity=5)
    assert len(result) == 5
    assert all(item in items for item in result)


def test_draw_items_empty_pool_returns_empty():
    assert draw_items([], quantity=3) == []


def test_draw_items_favors_cheaper_item_statistically():
    cheap = make_item(1, value=1)
    expensive = make_item(2, value=10000)
    counts = Counter()
    for _ in range(500):
        (drawn,) = draw_items([cheap, expensive], quantity=1)
        counts[drawn.id] += 1
    assert counts[cheap.id] > counts[expensive.id]
