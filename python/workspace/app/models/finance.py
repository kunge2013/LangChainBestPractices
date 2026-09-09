"""
Finance (到账登记表) and Payment (付款记录表) models.
These are treated as existing tables referenced by the ledger subsystem.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, BigInt


class Finance(Base):
    """公有资金池到账登记表."""
    __tablename__ = "finance"

    finance_id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    payment_cust_name: Mapped[str | None] = mapped_column(String(200))
    bank_nbr: Mapped[str | None] = mapped_column(String(50))
    payment_date: Mapped[datetime | None] = mapped_column(DateTime)
    payment_money: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    status_cd: Mapped[str] = mapped_column(String(10), default="1000")
    create_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    update_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class Payment(Base):
    """私有资金池付款记录表."""
    __tablename__ = "payment"

    payment_id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    finance_id: Mapped[int | None] = mapped_column(BigInteger)
    deposit_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    status_cd: Mapped[str] = mapped_column(String(10), default="1000")
    create_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    update_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
