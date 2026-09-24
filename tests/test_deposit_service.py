"""Тесты чистой логики обменника: корзина и минимальные партии."""
from __future__ import annotations

from bot.database.models import DepositCategory, DepositItem
from bot.services.deposit_service import (
    apply_delta,
    cart_is_valid,
    cart_total,
    get_buff,
    item_unit_price,
)


def make_item(item_id: int, price: int, min_qty: int = 1) -> DepositItem:
    return DepositItem(
        id=item_id,
        category=DepositCategory.BRAINROT,
        name=f"Item {item_id}",
        emoji="🧩",
        price_b=price,
        min_qty=min_qty,
    )


def test_apply_delta_jumps_to_min_qty_on_first_increment():
    item = make_item(1, price=10, min_qty=2)
    assert apply_delta(item, 0, +1) == 2
    assert apply_delta(item, 2, +1) == 3


def test_apply_delta_drops_to_zero_below_min_qty():
    item = make_item(1, price=10, min_qty=2)
    assert apply_delta(item, 2, -1) == 0
    assert apply_delta(item, 3, -1) == 2


def test_cart_is_valid_requires_min_qty():
    item = make_item(1, price=10, min_qty=2)
    assert cart_is_valid([item], {}) is False
    assert cart_is_valid([item], {1: 1}) is False
    assert cart_is_valid([item], {1: 2}) is True


def test_buff_surcharge_applied_to_unit_price():
    item = make_item(1, price=100)
    buff = get_buff("combo1")  # +5%
    assert item_unit_price(item, buff) == 105


def test_cart_total_sums_items_with_buff():
    items = [make_item(1, price=100), make_item(2, price=50, min_qty=2)]
    buff = get_buff("none")
    total = cart_total(items, {1: 1, 2: 2}, buff)
    assert total == 100 + 50 * 2
