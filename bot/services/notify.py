"""Уведомления администраторов о новых заявках на депозит."""
from __future__ import annotations

from aiogram import Bot

from bot.config import config
from bot.database.models import DepositCategory, DepositItem, DepositRequest, User
from bot.keyboards.deposit import admin_request_keyboard
from bot.utils.texts import ADMIN_NEW_REQUEST_TEXT, CATEGORY_TITLES


async def notify_admins_new_request(
    bot: Bot,
    request: DepositRequest,
    user: User,
    category: DepositCategory,
    items_by_id: dict[int, DepositItem],
) -> None:
    if not config.admin_chat_id:
        return

    items_text = ", ".join(
        f"{items_by_id[int(item_id)].emoji} {items_by_id[int(item_id)].name} × {qty}"
        for item_id, qty in request.items.items()
        if int(item_id) in items_by_id
    )
    text = ADMIN_NEW_REQUEST_TEXT.format(
        request_id=request.id,
        user=f"@{user.username}" if user.username else str(user.tg_id),
        category=CATEGORY_TITLES[category],
        nickname=request.game_nickname,
        items=items_text,
        total=request.total_b,
    )
    await bot.send_message(config.admin_chat_id, text, reply_markup=admin_request_keyboard(request.id))


async def notify_admins_text(bot: Bot, text: str) -> None:
    """Короткое уведомление в чат админов (например, новая заявка на вывод)."""
    if not config.admin_chat_id:
        return
    try:
        await bot.send_message(config.admin_chat_id, text)
    except Exception:  # noqa: BLE001 — уведомление не должно ломать заявку
        pass
