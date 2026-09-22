"""Розыгрыши: участие пользователей + админ-команда создания.

[НЕИЗВЕСТНО] Интерфейс раздела ни разу не был на скриншотах — сделано по
собственному усмотрению (см. bot.database.models.Giveaway).
"""
from __future__ import annotations

from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.config import config, is_admin
from bot.database.engine import async_session
from bot.database.models import GiveawayStatus
from bot.database.repo import giveaways as giveaways_repo
from bot.database.repo.users import get_or_create_user, get_user_by_id
from bot.keyboards.callbacks import GiveawayJoinCB, GiveawaysHomeCB
from bot.keyboards.giveaways import giveaways_keyboard
from bot.services.giveaway_service import resolve_all_expired
from bot.utils.texts import (
    GIVEAWAY_ALREADY_JOINED,
    GIVEAWAY_ALREADY_RESOLVED,
    GIVEAWAY_JOINED,
    GIVEAWAY_NO_WINNER_ANNOUNCEMENT,
    GIVEAWAY_ROW,
    GIVEAWAY_WINNER_ANNOUNCEMENT,
    GIVEAWAYS_EMPTY,
    GIVEAWAYS_HEADER,
)

router = Router(name="giveaways")


@router.callback_query(GiveawaysHomeCB.filter())
async def open_giveaways_home(callback: CallbackQuery, state: FSMContext, *, answer: bool = True) -> None:
    async with async_session() as session:
        resolved = await resolve_all_expired(session)

        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        active = await giveaways_repo.list_active(session)

        rows = []
        joined_ids: set[int] = set()
        for giveaway in active:
            entry = await giveaways_repo.get_entry(session, giveaway, user)
            if entry:
                joined_ids.add(giveaway.id)
            entries_count = await giveaways_repo.count_entries(session, giveaway)
            joined_note = "\n✅ Ты участвуешь" if giveaway.id in joined_ids else ""
            rows.append(
                GIVEAWAY_ROW.format(
                    title=giveaway.title,
                    prize=giveaway.prize_description,
                    entries=entries_count,
                    ends_at=giveaway.ends_at.strftime("%d.%m.%Y %H:%M UTC"),
                )
                + joined_note
            )

        announcements = []
        for giveaway in resolved:
            if giveaway.winner_user_id:
                winner = await get_user_by_id(session, giveaway.winner_user_id)
                winner_label = f"@{winner.username}" if winner and winner.username else "игрок"
                announcements.append(GIVEAWAY_WINNER_ANNOUNCEMENT.format(title=giveaway.title, winner=winner_label))
            else:
                announcements.append(GIVEAWAY_NO_WINNER_ANNOUNCEMENT.format(title=giveaway.title))

    lines = [GIVEAWAYS_HEADER]
    if rows:
        for row in rows:
            lines.append("")
            lines.append(row)
    else:
        lines.append("")
        lines.append(GIVEAWAYS_EMPTY)

    await callback.message.edit_text("\n".join(lines), reply_markup=giveaways_keyboard(active, joined_ids))
    if answer:
        await callback.answer()

    if announcements and config.admin_chat_id:
        for text in announcements:
            await callback.bot.send_message(config.admin_chat_id, text)


@router.callback_query(GiveawayJoinCB.filter())
async def handle_join(callback: CallbackQuery, callback_data: GiveawayJoinCB, state: FSMContext) -> None:
    async with async_session() as session:
        giveaway = await giveaways_repo.get(session, callback_data.giveaway_id)
        if giveaway is None or giveaway.status != GiveawayStatus.ACTIVE:
            await callback.answer(GIVEAWAY_ALREADY_RESOLVED, show_alert=True)
            return

        from_user = callback.from_user
        user = await get_or_create_user(session, from_user.id, from_user.username, from_user.first_name)
        existing = await giveaways_repo.get_entry(session, giveaway, user)
        if existing:
            await callback.answer(GIVEAWAY_ALREADY_JOINED, show_alert=True)
            return

        await giveaways_repo.join(session, giveaway, user)
        title = giveaway.title

    await callback.answer(GIVEAWAY_JOINED.format(title=title), show_alert=True)
    await open_giveaways_home(callback, state, answer=False)


@router.message(Command("creategiveaway"))
async def handle_create_giveaway(message: Message) -> None:
    if not is_admin(message.from_user.id):
        return

    args = (message.text or "").split(maxsplit=1)
    if len(args) < 2 or "|" not in args[1]:
        await message.answer("Формат: /creategiveaway Название | Приз | ГГГГ-ММ-ДД ЧЧ:ММ")
        return

    parts = [p.strip() for p in args[1].split("|")]
    if len(parts) != 3:
        await message.answer("Нужно ровно 3 части через «|»: Название | Приз | Дата окончания.")
        return

    title, prize, ends_at_raw = parts
    try:
        ends_at = datetime.strptime(ends_at_raw, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer("Дата должна быть в формате ГГГГ-ММ-ДД ЧЧ:ММ (UTC).")
        return

    async with async_session() as session:
        giveaway = await giveaways_repo.create(session, title, prize, ends_at, message.from_user.id)

    await message.answer(
        f"✅ Розыгрыш «{giveaway.title}» создан, завершится {ends_at.strftime('%d.%m.%Y %H:%M UTC')}."
    )
