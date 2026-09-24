"""successful_payment зачисляет ровно ту сумму, что зафиксирована в счёте."""
from __future__ import annotations

from types import SimpleNamespace

from bot.database.models import User
from bot.handlers.deposit import stars as stars_module
from bot.services import stars_service


class FakeState:
    async def clear(self):
        pass


async def test_successful_payment_credits_fixed_amount_once(in_memory_db, monkeypatch) -> None:
    monkeypatch.setattr(stars_module, "async_session", in_memory_db)
    async with in_memory_db() as session:
        user = User(tg_id=7, referral_code="R7")
        session.add(user)
        await session.commit()
        q = stars_service.StarsQuote(stars=100, rate=1.75, bonus_percent=10, code="X", credited=192)
        deposit = await stars_service.create_deposit(session, user, q)

    answers = []

    async def answer(text, **kw):
        answers.append(text)

    payment = SimpleNamespace(invoice_payload=deposit.payload, telegram_payment_charge_id="ch1")
    message = SimpleNamespace(successful_payment=payment, answer=answer)
    await stars_module.handle_successful_payment(message, FakeState())
    await stars_module.handle_successful_payment(message, FakeState())  # повтор от Telegram

    async with in_memory_db() as session:
        assert (await session.get(User, user.id)).balance == 192
    assert len(answers) == 1 and "192 B" in answers[0]
