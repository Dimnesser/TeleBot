"""Решение модератора по заявке на пополнение брейнротами/гирсами.

Одна логика для кнопок в чате модераторов (bot/handlers/deposit/admin.py)
и для очереди заявок в админ-панели Mini App: зачисление B (+ бонус
партнёрского кода), комиссия реферу, уведомление игрока и перевод
следующей заявки из очереди в работу.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import DepositRequest, DepositRequestStatus, User
from bot.database.repo import deposit_items as items_repo
from bot.database.repo import deposit_requests as requests_repo
from bot.services.notify import notify_admins_new_request
from bot.services.partner_service import deposit_bonus
from bot.services.referral_service import credit_referral_commission
from bot.utils.texts import DEPOSIT_QUEUE_PROMOTED_TEXT, USER_DEPOSIT_APPROVED, USER_DEPOSIT_REJECTED

logger = logging.getLogger(__name__)

OPEN_STATUSES = (DepositRequestStatus.PENDING, DepositRequestStatus.QUEUED)


class DepositAlreadyResolved(Exception):
    pass


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

    if was_pending:  # освободился слот модератора — следующая из очереди в работу
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
