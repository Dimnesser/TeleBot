"""Модерация заявок на депозит администратором."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Filter
from aiogram.types import CallbackQuery

from bot.config import is_admin
from bot.database.engine import async_session
from bot.keyboards.callbacks import DepositAdminCB, WithdrawAdminCB
from bot.services import withdraw_service
from bot.services.deposit_moderation import DepositAlreadyResolved, resolve_deposit
from bot.utils.texts import ADMIN_REQUEST_ALREADY_RESOLVED, ADMIN_REQUEST_APPROVED, ADMIN_REQUEST_REJECTED

router = Router(name="deposit_admin")


class IsAdmin(Filter):
    async def __call__(self, callback: CallbackQuery) -> bool:
        return is_admin(callback.from_user.id)


@router.callback_query(DepositAdminCB.filter(), IsAdmin())
async def handle_admin_decision(callback: CallbackQuery, callback_data: DepositAdminCB) -> None:
    approve = callback_data.action == "approve"
    async with async_session() as session:
        try:
            decision = await resolve_deposit(
                session, callback.bot, callback_data.request_id, approve=approve, admin_tg_id=callback.from_user.id
            )
        except DepositAlreadyResolved:
            await callback.answer(ADMIN_REQUEST_ALREADY_RESOLVED, show_alert=True)
            return
    template = ADMIN_REQUEST_APPROVED if approve else ADMIN_REQUEST_REJECTED
    await callback.message.edit_text(template.format(request_id=decision.request.id))
    await callback.answer()


@router.callback_query(WithdrawAdminCB.filter(), IsAdmin())
async def handle_withdraw_decision(callback: CallbackQuery, callback_data: WithdrawAdminCB) -> None:
    done = callback_data.action == "done"
    async with async_session() as session:
        try:
            request = await withdraw_service.resolve(
                session, callback.bot, callback_data.request_id, done=done, admin_tg_id=callback.from_user.id
            )
        except withdraw_service.WithdrawError as exc:
            await callback.answer(exc.message, show_alert=True)
            return
    verdict = "✅ Выдано" if done else "↩️ Отменено"
    await callback.message.edit_text(f"{callback.message.html_text}\n\n<b>{verdict}</b> (вывод №{request.id})")
    await callback.answer()
