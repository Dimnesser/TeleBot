"""Вывод брейнротов из инвентаря через сток админа.

* Сток (WithdrawStock) — что у админа реально есть на выдачу. Меняет админ
  кнопками +/−, одобренные депозиты брейнротами пополняют его сами.
* Брейнрот есть в стоке — выводится он сам.
* Нет в стоке — обмен на брейнротов из стока примерно той же ценности,
  можно несколькими штуками (Dragon Cannelloni 973 → 23 × Garama 41); чего
  не хватает до ценности выводимого, бот доплачивает в B на баланс.
* Заявка сразу резервирует сток и забирает брейнрот из инвентаря. Админ
  отмечает «Выдано» (доплата зачисляется, игроку сообщение) или «Отменить»
  (брейнрот возвращается в инвентарь, сток — обратно).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from aiogram import Bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.data.brainrot_roster import ROSTER_BY_NAME
from bot.database.models import InventoryItem, User, WithdrawRequest, WithdrawStatus, WithdrawStock
from bot.database.repo import inventory as inventory_repo

logger = logging.getLogger(__name__)

MAX_EXCHANGE_QTY = 50  # больше одного вида за раз не выдаём — трейд не резиновый
MAX_OPTIONS = 6


class WithdrawError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class Option:
    items: list[tuple[str, int, int]]  # (name, value, qty)
    topup: int

    @property
    def key(self) -> str:
        return ";".join(f"{n}×{q}" for n, _, q in self.items)

    @property
    def payout_value(self) -> int:
        return sum(v * q for _, v, q in self.items)

    def as_json(self) -> list[dict]:
        return [{"name": n, "value": v, "qty": q} for n, v, q in self.items]


def stock_value(name: str) -> int | None:
    entry = ROSTER_BY_NAME.get(name)
    return entry.value if entry else None


async def stock(session: AsyncSession) -> dict[str, int]:
    rows = (await session.execute(select(WithdrawStock))).scalars().all()
    return {r.name: r.count for r in rows if r.count > 0}


async def add_stock(session: AsyncSession, name: str, delta: int) -> int:
    row = await session.get(WithdrawStock, name)
    if row is None:
        row = WithdrawStock(name=name, count=0)
        session.add(row)
    row.count = max(0, row.count + delta)
    await session.flush()
    return row.count


def options_for(item_name: str, item_value: int, available: dict[str, int]) -> list[Option]:
    """Варианты выдачи: сам брейнрот, иначе обмены — одним видом (N штук)
    и смешанный набор «от дорогих к дешёвым». Лучшие — с меньшей доплатой."""
    if available.get(item_name, 0) > 0:
        return [Option(items=[(item_name, item_value, 1)], topup=0)]
    pool = sorted(
        ((n, v, c) for n, c in available.items() if (v := stock_value(n)) and v <= item_value),
        key=lambda t: -t[1],
    )
    found: dict[str, Option] = {}
    for name, value, count in pool:
        qty = min(count, item_value // value, MAX_EXCHANGE_QTY)
        if qty > 0:
            opt = Option(items=[(name, value, qty)], topup=item_value - qty * value)
            found[opt.key] = opt
    # смешанный набор: жадно от дорогих к дешёвым
    rest, mix = item_value, []
    for name, value, count in pool:
        qty = min(count, rest // value, MAX_EXCHANGE_QTY)
        if qty > 0:
            mix.append((name, value, qty))
            rest -= qty * value
    if len(mix) > 1:
        opt = Option(items=mix, topup=rest)
        found[opt.key] = opt
    return sorted(found.values(), key=lambda o: (o.topup, sum(q for *_, q in o.items)))[:MAX_OPTIONS]


async def create_request(
    session: AsyncSession, user: User, item: InventoryItem, option_key: str, nickname: str
) -> WithdrawRequest:
    if item.user_id != user.id:
        raise WithdrawError("item_gone", "Этого брейнрота уже нет в инвентаре")
    available = await stock(session)
    option = next((o for o in options_for(item.item_name, item.value, available) if o.key == option_key), None)
    if option is None:
        raise WithdrawError("option_gone", "Сток изменился — выбери вариант заново")
    for name, _, qty in option.items:
        await add_stock(session, name, -qty)
    request = WithdrawRequest(
        user_id=user.id, item_name=item.item_name, item_value=item.value, item_rarity=item.rarity,
        payout=option.as_json(), topup_b=option.topup, game_nickname=nickname, status=WithdrawStatus.PENDING,
    )
    session.add(request)
    await session.delete(item)
    await session.commit()
    await session.refresh(request)
    return request


async def resolve(session: AsyncSession, bot: Bot, request_id: int, *, done: bool, admin_tg_id: int) -> WithdrawRequest:
    request = await session.get(WithdrawRequest, request_id)
    if request is None or request.status != WithdrawStatus.PENDING:
        raise WithdrawError("already_resolved", "Заявка уже обработана")
    user = await session.get(User, request.user_id)
    request.admin_id = admin_tg_id
    request.resolved_at = datetime.utcnow()
    items_text = ", ".join(f"{p['name']} ×{p['qty']}" for p in request.payout)
    if done:
        request.status = WithdrawStatus.DONE
        user.balance += request.topup_b
        text = f"✅ Вывод №{request.id} выдан: {items_text}."
        if request.topup_b:
            text += f" Доплата {request.topup_b} B зачислена на баланс."
    else:
        request.status = WithdrawStatus.CANCELLED
        for p in request.payout:
            await add_stock(session, p["name"], p["qty"])
        await inventory_repo.add_items(session, user, "Отмена вывода", [(request.item_name, request.item_value)])
        text = f"↩️ Вывод №{request.id} отменён — {request.item_name} вернулся в инвентарь."
    await session.commit()
    try:
        await bot.send_message(user.tg_id, text)
    except Exception:  # noqa: BLE001 — игрок мог не открывать чат с ботом
        logger.warning("Не удалось уведомить игрока %s о выводе", user.tg_id, exc_info=True)
    return request
