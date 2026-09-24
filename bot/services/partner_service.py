"""Партнёрская программа: личные реф-коды партнёров и бонус к пополнениям."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import PartnerCode, User
from bot.database.repo.rewards import add_case_credits, generate_code


class PartnerError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


async def get_partner_code(session: AsyncSession, code: str) -> PartnerCode | None:
    result = await session.execute(select(PartnerCode).where(PartnerCode.code == code.strip().upper()))
    return result.scalar_one_or_none()


async def get_partner_code_of(session: AsyncSession, user: User) -> PartnerCode | None:
    result = await session.execute(select(PartnerCode).where(PartnerCode.user_id == user.id))
    return result.scalar_one_or_none()


async def list_partner_codes(session: AsyncSession) -> list[tuple[PartnerCode, User]]:
    result = await session.execute(
        select(PartnerCode, User).join(User, User.id == PartnerCode.user_id).order_by(PartnerCode.id.desc())
    )
    return [(row[0], row[1]) for row in result.all()]


async def grant_partnership(
    session: AsyncSession,
    partner: User,
    *,
    commission_percent: float,
    deposit_bonus_percent: float,
    case_code: str | None,
    case_amount: int,
    code: str | None = None,
) -> PartnerCode:
    """Выдаёт/обновляет партнёрку. Код у партнёра один; при повторной выдаче
    меняются условия (и код, если передан новый)."""
    partner.partner_percent = commission_percent
    pc = await get_partner_code_of(session, partner)
    new_code = (code or "").strip().upper() or (pc.code if pc else generate_code(6))
    if pc is None:
        pc = PartnerCode(user_id=partner.id, code=new_code)
        session.add(pc)
    pc.code = new_code
    pc.deposit_bonus_percent = deposit_bonus_percent
    pc.case_code = case_code
    pc.case_amount = case_amount
    pc.is_active = True
    await session.commit()
    await session.refresh(pc)
    return pc


async def revoke_partnership(session: AsyncSession, partner: User) -> None:
    """Снимает партнёрку: код перестаёт активироваться, % партнёра — обычный тир.
    Уже привязанные рефералы сохраняют свой бонус к пополнениям."""
    partner.partner_percent = None
    pc = await get_partner_code_of(session, partner)
    if pc is not None:
        pc.is_active = False
    await session.commit()


async def apply_partner_code(session: AsyncSession, user: User, code: str) -> PartnerCode:
    """Активирует партнёрский код. PartnerError: not_found | own_code | already_partner_ref."""
    pc = await get_partner_code(session, code)
    if pc is None or not pc.is_active:
        raise PartnerError("not_found")
    if pc.user_id == user.id:
        raise PartnerError("own_code")
    if user.partner_code_id is not None:
        raise PartnerError("already_partner_ref")

    user.partner_code_id = pc.id
    user.referred_by_id = pc.user_id  # проценты с депозитов теперь идут партнёру
    user.deposit_bonus_percent = pc.deposit_bonus_percent or None
    pc.uses += 1
    await session.commit()
    if pc.case_code and pc.case_amount > 0:
        await add_case_credits(session, user, pc.case_code, pc.case_amount)
    return pc


def deposit_bonus(user: User, amount: int) -> int:
    """Бонус к пополнению от партнёрского кода (0, если кода нет)."""
    if not user.deposit_bonus_percent or amount <= 0:
        return 0
    return round(amount * user.deposit_bonus_percent / 100)
