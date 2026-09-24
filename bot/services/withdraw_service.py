"""Вывод брейнротов из инвентаря через сток админа.

* Сток (WithdrawStock) — что у админа реально есть на выдачу. Меняет админ
  кнопками +/−, одобренные депозиты брейнротами пополняют его сами.
* Брейнрот есть в стоке — выводится он сам.
* Нет в стоке — обмен на брейнротов из стока примерно той же ценности,
  можно несколькими штуками (Dragon Cannelloni 973 → 23 × Garama 41); чего
  не хватает до ценности выводимого, бот доплачивает в B на баланс.
* Заявка сразу резервирует сток и забирает брейнрот из инвентаря.
* Очередь как у пополнений: у игрока одна открытая заявка, в работе одна —
  первая по времени («твоя очередь»), остальные ждут со своим номером.
  «Выдано» — только заявке в работе (доплата зачисляется); «Отменить» может
  админ или сам игрок (брейнрот и сток возвращаются). После решения по
  заявке в работе следующая получает «твоя очередь настала».
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from aiogram import Bot
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.data.brainrot_roster import ROSTER_BY_NAME
from bot.database.models import InventoryItem, User, WithdrawRequest, WithdrawStatus, WithdrawStock
from bot.database.repo import inventory as inventory_repo
from bot.utils.texts import QUEUE_CANCELLED_TEXT, QUEUE_FIRST_TEXT, QUEUE_TURN_TEXT, QUEUE_WAIT_TEXT

logger = logging.getLogger(__name__)

MAX_EXCHANGE_QTY = 50  # больше одного вида за раз не выдаём — трейд не резиновый
MAX_OPTIONS = 6
KIND = "Заявка на вывод"
OPEN = (WithdrawStatus.PENDING, WithdrawStatus.QUEUED)


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


def options_for(item_name: str, item_value: int, available: dict[str, int], *, exchange: bool = False) -> list[Option]:
    """Варианты выдачи: сам брейнрот, иначе обмены — одним видом (N штук)
    и смешанный набор «от дорогих к дешёвым». Лучшие — с меньшей доплатой.
    exchange=True — только обмен на других (даже если сам есть в стоке)."""
    if not exchange and available.get(item_name, 0) > 0:
        return [Option(items=[(item_name, item_value, 1)], topup=0)]
    pool = sorted(
        ((n, v, c) for n, c in available.items() if (v := stock_value(n)) and v <= item_value and n != item_name),
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


async def queue_position(session: AsyncSession, request: WithdrawRequest) -> int:
    ahead = (await session.execute(
        select(func.count()).select_from(WithdrawRequest)
        .where(WithdrawRequest.status.in_(OPEN), WithdrawRequest.id < request.id)
    )).scalar_one()
    return ahead + 1


async def create_request(
    session: AsyncSession, bot: Bot, user: User, item: InventoryItem, option_key: str, nickname: str,
    *, exchange: bool = False,
) -> tuple[WithdrawRequest, int]:
    if item.user_id != user.id:
        raise WithdrawError("item_gone", "Этого брейнрота уже нет в инвентаре")
    open_one = (await session.execute(
        select(WithdrawRequest).where(WithdrawRequest.user_id == user.id, WithdrawRequest.status.in_(OPEN)).limit(1)
    )).scalar_one_or_none()
    if open_one is not None:
        raise WithdrawError("already_open", f"У тебя уже есть заявка на вывод №{open_one.id} — дождись её")
    available = await stock(session)
    option = next((o for o in options_for(item.item_name, item.value, available, exchange=exchange) if o.key == option_key), None)
    if option is None:
        raise WithdrawError("option_gone", "Сток изменился — выбери вариант заново")
    for name, _, qty in option.items:
        await add_stock(session, name, -qty)
    busy = (await session.execute(
        select(func.count()).select_from(WithdrawRequest).where(WithdrawRequest.status == WithdrawStatus.PENDING)
    )).scalar_one() > 0
    request = WithdrawRequest(
        user_id=user.id, item_name=item.item_name, item_value=item.value, item_rarity=item.rarity,
        payout=option.as_json(), topup_b=option.topup, game_nickname=nickname,
        status=WithdrawStatus.QUEUED if busy else WithdrawStatus.PENDING,
    )
    session.add(request)
    await session.delete(item)
    await session.commit()
    await session.refresh(request)
    position = await queue_position(session, request)
    await _send(bot, user.tg_id, QUEUE_FIRST_TEXT.format(kind=KIND, request_id=request.id, nickname=nickname) if position == 1
                else QUEUE_WAIT_TEXT.format(kind=KIND, request_id=request.id, position=position))
    if not busy:
        await notify_admins(bot, request, user)
    return request, position


def payout_text(request: WithdrawRequest) -> str:
    text = ", ".join(f"{p['name']} ×{p['qty']}" for p in request.payout)
    return text + (f" + {request.topup_b} B доплаты" if request.topup_b else "")


async def notify_admins(bot: Bot, request: WithdrawRequest, user: User) -> None:
    """Заявка в работе — админам в чат с кнопками «Выдано» / «Отменить»."""
    from bot.config import config
    from bot.keyboards.withdraw import admin_withdraw_keyboard

    if not config.admin_chat_id:
        return
    who = f"@{user.username}" if user.username else str(user.tg_id)
    text = (f"📤 <b>Вывод №{request.id}</b> от {who}\nНик в игре: <b>{request.game_nickname}</b>\n"
            f"Выводит: {request.item_name} ({request.item_value} B)\nВыдать: <b>{payout_text(request)}</b>")
    try:
        await bot.send_message(config.admin_chat_id, text, reply_markup=admin_withdraw_keyboard(request.id))
    except Exception:  # noqa: BLE001
        logger.warning("Не удалось уведомить админов о выводе %s", request.id, exc_info=True)


async def resolve(
    session: AsyncSession, bot: Bot, request_id: int, *, done: bool, admin_tg_id: int, by_user: User | None = None,
) -> WithdrawRequest:
    """done=True — выдано (только заявка в работе); False — отмена (админ
    или сам игрок by_user). Потом в работу уходит следующая по очереди."""
    request = await session.get(WithdrawRequest, request_id)
    if request is None or request.status not in OPEN or (by_user is not None and request.user_id != by_user.id):
        raise WithdrawError("already_resolved", "Заявка уже обработана")
    if done and request.status != WithdrawStatus.PENDING:
        raise WithdrawError("not_your_turn", "Сначала заявка, которая первая в очереди")
    was_pending = request.status == WithdrawStatus.PENDING
    user = await session.get(User, request.user_id)
    request.admin_id = admin_tg_id
    request.resolved_at = datetime.utcnow()
    if done:
        request.status = WithdrawStatus.DONE
        user.balance += request.topup_b
        text = f"✅ Вывод №{request.id} выдан: {payout_text(request)}."
        if request.topup_b:
            text += f" Доплата {request.topup_b} B зачислена на баланс."
    else:
        request.status = WithdrawStatus.CANCELLED
        for p in request.payout:
            await add_stock(session, p["name"], p["qty"])
        await inventory_repo.add_items(session, user, "Отмена вывода", [(request.item_name, request.item_value)])
        text = QUEUE_CANCELLED_TEXT.format(kind=KIND, request_id=request.id) + f" {request.item_name} вернулся в инвентарь."
    await session.commit()
    await _send(bot, user.tg_id, text)
    if was_pending:
        await _promote_next(session, bot)
    return request


async def _promote_next(session: AsyncSession, bot: Bot) -> None:
    nxt = (await session.execute(
        select(WithdrawRequest).where(WithdrawRequest.status == WithdrawStatus.QUEUED).order_by(WithdrawRequest.id).limit(1)
    )).scalar_one_or_none()
    if nxt is None:
        return
    nxt.status = WithdrawStatus.PENDING
    await session.commit()
    owner = await session.get(User, nxt.user_id)
    await _send(bot, owner.tg_id, QUEUE_TURN_TEXT.format(kind=KIND, request_id=nxt.id, nickname=nxt.game_nickname))
    await notify_admins(bot, nxt, owner)


async def _send(bot: Bot, chat_id: int, text: str) -> None:
    try:
        await bot.send_message(chat_id, text)
    except Exception:  # noqa: BLE001 — игрок мог не открывать чат с ботом
        logger.warning("Не удалось отправить сообщение %s", chat_id, exc_info=True)
