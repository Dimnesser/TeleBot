"""Бизнес-логика раздела пополнения баланса предметами (обменник)."""
from __future__ import annotations

import math

from bot.data.buffs import BUFF_OPTIONS, BuffOption
from bot.database.models import DepositItem


def get_buff(code: str) -> BuffOption:
    for buff in BUFF_OPTIONS:
        if buff.code == code:
            return buff
    return BUFF_OPTIONS[0]


def next_buff_code(current: str) -> str:
    codes = [b.code for b in BUFF_OPTIONS]
    index = codes.index(current) if current in codes else -1
    return codes[(index + 1) % len(codes)]


def item_unit_price(item: DepositItem, buff: BuffOption) -> int:
    surcharge = math.ceil(item.price_b * buff.surcharge_percent / 100)
    return item.price_b + surcharge


def apply_delta(item: DepositItem, current_qty: int, delta: int) -> int:
    """Считает новое количество предмета в корзине с учётом min_qty.

    При первом клике «+» количество сразу прыгает к минимальной партии
    (например, «от 2 шт»), дальше меняется по одному, как на скриншотах.
    """
    if delta > 0:
        if current_qty == 0:
            return item.min_qty
        return current_qty + 1
    if current_qty <= item.min_qty:
        return 0
    return current_qty - 1


def cart_total(items: list[DepositItem], cart: dict[int, int], buff: BuffOption) -> int:
    total = 0
    for item in items:
        qty = cart.get(item.id, 0)
        if qty:
            total += item_unit_price(item, buff) * qty
    return total


def estimate_wait_seconds(queue_position: int, max_concurrent: int, avg_trade_minutes: int) -> int:
    """Грубая оценка времени ожидания в очереди на трейд.

    [ЛОГИЧЕСКИ ПРЕДПОЛОЖЕНО] На скриншоте показано «~34:45» без пояснения
    формулы. Здесь используется простая модель: позиция в очереди делится на
    число одновременных слотов, округляется вверх до целого «цикла» обработки
    и умножается на среднее время трейда — легко заменить на реальную логику.
    """
    slots = max(max_concurrent, 1)
    cycles = math.ceil(queue_position / slots)
    return cycles * avg_trade_minutes * 60


def format_eta(seconds: int) -> str:
    minutes, secs = divmod(max(seconds, 0), 60)
    return f"{minutes}:{secs:02d}"


def cart_is_valid(items: list[DepositItem], cart: dict[int, int]) -> bool:
    by_id = {item.id: item for item in items}
    picked = {item_id: qty for item_id, qty in cart.items() if qty > 0}
    if not picked:
        return False
    for item_id, qty in picked.items():
        item = by_id.get(item_id)
        if item is None or qty < item.min_qty:
            return False
    return True
