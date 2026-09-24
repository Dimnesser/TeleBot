"""Бесплатные открытия кейсов и промокоды."""
from __future__ import annotations

import secrets

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.database.models import CaseCredit, PromoCode, PromoKind, PromoRedemption, User
from bot.database.repo.users import add_balance, add_game_tokens

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # без 0/O и 1/I


async def case_credits(session: AsyncSession, user: User) -> dict[str, int]:
    result = await session.execute(select(CaseCredit).where(CaseCredit.user_id == user.id, CaseCredit.count > 0))
    return {c.case_code: c.count for c in result.scalars()}


async def add_case_credits(session: AsyncSession, user: User, case_code: str, count: int) -> int:
    result = await session.execute(
        select(CaseCredit).where(CaseCredit.user_id == user.id, CaseCredit.case_code == case_code)
    )
    credit = result.scalar_one_or_none()
    if credit is None:
        credit = CaseCredit(user_id=user.id, case_code=case_code, count=0)
        session.add(credit)
    credit.count += count
    await session.commit()
    return credit.count


async def use_case_credits(session: AsyncSession, user: User, case_code: str, count: int) -> bool:
    """Списывает count бесплатных открытий; False — если их не хватает."""
    result = await session.execute(
        select(CaseCredit).where(CaseCredit.user_id == user.id, CaseCredit.case_code == case_code)
    )
    credit = result.scalar_one_or_none()
    if credit is None or credit.count < count:
        return False
    credit.count -= count
    await session.commit()
    return True


def generate_code(length: int = 8) -> str:
    return "".join(secrets.choice(_CODE_ALPHABET) for _ in range(length))


async def create_promo(
    session: AsyncSession,
    *,
    kind: PromoKind,
    amount: int,
    max_uses: int,
    created_by_tg_id: int,
    case_code: str | None = None,
    code: str | None = None,
) -> PromoCode:
    code = (code or generate_code()).strip().upper()
    promo = PromoCode(
        code=code, kind=kind, amount=amount, case_code=case_code, max_uses=max_uses, created_by_tg_id=created_by_tg_id
    )
    session.add(promo)
    await session.commit()
    await session.refresh(promo)
    return promo


async def get_promo(session: AsyncSession, code: str) -> PromoCode | None:
    result = await session.execute(select(PromoCode).where(PromoCode.code == code.strip().upper()))
    return result.scalar_one_or_none()


async def list_promos(session: AsyncSession, limit: int = 20) -> list[PromoCode]:
    result = await session.execute(select(PromoCode).order_by(desc(PromoCode.created_at), desc(PromoCode.id)).limit(limit))
    return list(result.scalars())


class PromoError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


async def redeem_promo(session: AsyncSession, user: User, code: str) -> PromoCode:
    """Активирует промокод. PromoError: not_found | exhausted | already_used."""
    promo = await get_promo(session, code)
    if promo is None:
        raise PromoError("not_found")
    if promo.uses >= promo.max_uses:
        raise PromoError("exhausted")
    used = await session.execute(
        select(PromoRedemption.id).where(PromoRedemption.promo_id == promo.id, PromoRedemption.user_id == user.id)
    )
    if used.scalar_one_or_none() is not None:
        raise PromoError("already_used")

    promo.uses += 1
    session.add(PromoRedemption(promo_id=promo.id, user_id=user.id))
    await session.commit()
    if promo.kind == PromoKind.TOKENS:
        await add_game_tokens(session, user, promo.amount)
    elif promo.kind == PromoKind.BALANCE:
        await add_balance(session, user, promo.amount)
    else:
        await add_case_credits(session, user, promo.case_code, promo.amount)
    return promo
