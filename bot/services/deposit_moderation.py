"""Очередь пополнений брейнротами/гирсами и решения модератора.

Строгая очередь «по одному»: у игрока одна открытая заявка; в работе
(PENDING — «твоя очередь, жди трейд») всегда одна заявка — первая по
времени, остальные ждут (QUEUED) со своим номером. Зачислить можно только
заявку в работе; после решения в работу уходит следующая, игрок получает
сообщение. Одна логика для чата (bot/handlers/deposit) и Mini App.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from aiogram import Bot
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import DepositCategory, DepositItem, DepositRequest, DepositRequestStatus, User
from bot.database.repo import deposit_items as items_repo
from bot.database.repo import deposit_requests as requests_repo
from bot.services.deposit_service import cart_total, get_buff
from bot.services.notify import notify_admins_new_request
from bot.services.partner_service import deposit_bonus
from bot.services.referral_service import credit_referral_commission
from bot.utils.texts import DEPOSIT_QUEUE_PROMOTED_TEXT, USER_DEPOSIT_APPROVED, USER_DEPOSIT_REJECTED

logger = logging.getLogger(__name__)

OPEN_STATUSES = (DepositRequestStatus.PENDING, DepositRequestStatus.QUEUED)


class DepositAlreadyResolved(Exception):
    pass


class NotYourTurn(Exception):
    """Зачислить можно только заявку, которая сейчас в работе (первую в очереди)."""


class DepositAlreadyOpen(Exception):
    def __init__(self, request: DepositRequest):
        super().__init__(request.id)
        self.request = request


async def open_request_of(session: AsyncSession, user: User) -> DepositRequest | None:
    return (await session.execute(
        select(DepositRequest).where(DepositRequest.user_id == user.id, DepositRequest.status.in_(OPEN_STATUSES)).limit(1)
    )).scalar_one_or_none()


async def queue_position(session: AsyncSession, request: DepositRequest) -> int:
    """1 — заявка в работе (игроку кидают трейд), 2+ — сколько ждать до неё."""
    ahead = (await session.execute(
        select(func.count()).select_from(DepositRequest)
        .where(DepositRequest.status.in_(OPEN_STATUSES), DepositRequest.id < request.id)
    )).scalar_one()
    return ahead + 1


async def submit_deposit(
    session: AsyncSession, bot: Bot, user: User, category: DepositCategory, cart: dict[int, int],
    nickname: str, items: list[DepositItem],
) -> tuple[DepositRequest, int]:
    """Встать в очередь. Если очередь пуста — заявка сразу в работе."""
    if (existing := await open_request_of(session, user)) is not None:
        raise DepositAlreadyOpen(existing)
    busy = (await requests_repo.count_status(session, DepositRequestStatus.PENDING)) > 0
    request = await requests_repo.create_request(
        session, user, category, cart, buff=None, game_nickname=nickname,
        total_b=cart_total(items, cart, get_buff("none")),
        status=DepositRequestStatus.QUEUED if busy else DepositRequestStatus.PENDING,
    )
    if not busy:
        await notify_admins_new_request(bot, request, user, category, {i.id: i for i in items})
    return request, await queue_position(session, request)


@dataclass
class Decision:
    request: DepositRequest
    credited: int  # 0 при отклонении


async def resolve_deposit(
    session: AsyncSession, bot: Bot, request_id: int, *, approve: bool, admin_tg_id: int
) -> Decision:
    request = await requests_repo.get_request(session, request_id)
    if request is None or request.status not in OPEN_STATUSES:
        raise DepositAlreadyResolved
    if approve and request.status != DepositRequestStatus.PENDING:
        raise NotYourTurn
    was_pending = request.status == DepositRequestStatus.PENDING
    user = await session.get(User, request.user_id)

    credited = 0
    if approve:
        credited = request.total_b + deposit_bonus(user, request.total_b)  # бонус партнёрского кода
        user.balance += credited
        await requests_repo.resolve_request(session, request, DepositRequestStatus.APPROVED, admin_tg_id)
        await credit_referral_commission(session, user, request.total_b)
        text = USER_DEPOSIT_APPROVED.format(total=credited, balance=user.balance)
    else:
        await requests_repo.resolve_request(session, request, DepositRequestStatus.REJECTED, admin_tg_id)
        text = USER_DEPOSIT_REJECTED.format(request_id=request.id)
    await _safe_send(bot, user.tg_id, text)

    if was_pending:  # заявка в работе закрыта — следующая по очереди в работу
        await _promote_next(session, bot)
    return Decision(request=request, credited=credited)


async def _promote_next(session: AsyncSession, bot: Bot) -> None:
    promoted = await requests_repo.get_oldest_queued(session)
    if promoted is None:
        return
    await requests_repo.promote_to_pending(session, promoted)
    promoted_user = await session.get(User, promoted.user_id)
    items_by_id = {}
    for item_id in promoted.items:
        item = await items_repo.get_item(session, int(item_id))
        if item is not None:
            items_by_id[item.id] = item
    await _safe_send(bot, promoted_user.tg_id, DEPOSIT_QUEUE_PROMOTED_TEXT.format(request_id=promoted.id))
    await notify_admins_new_request(bot, promoted, promoted_user, promoted.category, items_by_id)


async def _safe_send(bot: Bot, chat_id: int, text: str) -> None:
    # Игрок мог не начинать чат с ботом — решение по заявке от этого не зависит.
    try:
        await bot.send_message(chat_id, text)
    except Exception:  # noqa: BLE001
        logger.warning("Не удалось отправить уведомление по заявке игроку %s", chat_id, exc_info=True)
