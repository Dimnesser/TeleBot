"""Модерация заявок на депозит администратором."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Filter
from aiogram.types import CallbackQuery

from bot.config import is_admin
from bot.database.engine import async_session
from bot.database.models import DepositRequestStatus, User
from bot.database.repo import deposit_items as items_repo
from bot.database.repo import deposit_requests as requests_repo
from bot.keyboards.callbacks import DepositAdminCB
from bot.services.notify import notify_admins_new_request
from bot.utils.texts import (
    ADMIN_REQUEST_ALREADY_RESOLVED,
    ADMIN_REQUEST_APPROVED,
    ADMIN_REQUEST_REJECTED,
    DEPOSIT_QUEUE_PROMOTED_TEXT,
    USER_DEPOSIT_APPROVED,
    USER_DEPOSIT_REJECTED,
)

router = Router(name="deposit_admin")


class IsAdmin(Filter):
    async def __call__(self, callback: CallbackQuery) -> bool:
        return is_admin(callback.from_user.id)


@router.callback_query(DepositAdminCB.filter(), IsAdmin())
async def handle_admin_decision(callback: CallbackQuery, callback_data: DepositAdminCB) -> None:
    async with async_session() as session:
        request = await requests_repo.get_request(session, callback_data.request_id)
        if request is None or request.status != DepositRequestStatus.PENDING:
            await callback.answer(ADMIN_REQUEST_ALREADY_RESOLVED, show_alert=True)
            return

        user = await session.get(User, request.user_id)

        if callback_data.action == "approve":
            user.balance += request.total_b
            await requests_repo.resolve_request(session, request, DepositRequestStatus.APPROVED, callback.from_user.id)
            admin_text = ADMIN_REQUEST_APPROVED.format(request_id=request.id)
            user_text = USER_DEPOSIT_APPROVED.format(total=request.total_b, balance=user.balance)
        else:
            await requests_repo.resolve_request(session, request, DepositRequestStatus.REJECTED, callback.from_user.id)
            admin_text = ADMIN_REQUEST_REJECTED.format(request_id=request.id)
            user_text = USER_DEPOSIT_REJECTED.format(request_id=request.id)

        target_tg_id = user.tg_id

        promoted = await requests_repo.get_oldest_queued(session)
        promoted_info = None
        if promoted is not None:
            await requests_repo.promote_to_pending(session, promoted)
            promoted_user = await session.get(User, promoted.user_id)
            promoted_items_by_id = {}
            for item_id_str in promoted.items:
                item = await items_repo.get_item(session, int(item_id_str))
                if item is not None:
                    promoted_items_by_id[item.id] = item
            promoted_info = (promoted, promoted_user, promoted_items_by_id)

    await callback.message.edit_text(admin_text)
    await callback.bot.send_message(target_tg_id, user_text)
    await callback.answer()

    if promoted_info is not None:
        promoted_request, promoted_user, promoted_items_by_id = promoted_info
        await callback.bot.send_message(
            promoted_user.tg_id, DEPOSIT_QUEUE_PROMOTED_TEXT.format(request_id=promoted_request.id)
        )
        await notify_admins_new_request(
            callback.bot, promoted_request, promoted_user, promoted_request.category, promoted_items_by_id
        )
