"""Модели БД."""
from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class DepositCategory(str, enum.Enum):
    BRAINROT = "brainrot"
    HIRSY = "hirsy"


class DepositRequestStatus(str, enum.Enum):
    QUEUED = "queued"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    balance: Mapped[int] = mapped_column(Integer, default=0)
    referral_code: Mapped[str] = mapped_column(String(16), unique=True)
    referred_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class DepositItem(Base):
    __tablename__ = "deposit_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[DepositCategory] = mapped_column(SAEnum(DepositCategory))
    name: Mapped[str] = mapped_column(String(128))
    emoji: Mapped[str] = mapped_column(String(16), default="🧩")
    price_b: Mapped[int] = mapped_column(Integer)
    min_qty: Mapped[int] = mapped_column(Integer, default=1)
    hot_stock_left: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class DepositRequest(Base):
    __tablename__ = "deposit_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    category: Mapped[DepositCategory] = mapped_column(SAEnum(DepositCategory))
    items: Mapped[dict] = mapped_column(JSON)  # {"<item_id>": qty}
    buff: Mapped[str | None] = mapped_column(String(32), nullable=True)
    game_nickname: Mapped[str] = mapped_column(String(64))
    total_b: Mapped[int] = mapped_column(Integer)
    status: Mapped[DepositRequestStatus] = mapped_column(
        SAEnum(DepositRequestStatus), default=DepositRequestStatus.PENDING
    )
    admin_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship()


class StarsDeposit(Base):
    __tablename__ = "stars_deposits"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    stars_amount: Mapped[int] = mapped_column(Integer)
    promo_code: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload: Mapped[str] = mapped_column(String(64), unique=True)
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending | paid
    telegram_charge_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    paid_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
