"""
Ledger item (权责欠费台账) model.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, BigInt


class LedgerItemRecord(Base):
    """权责欠费台账表."""
    __tablename__ = "ledger_item_record"
    __table_args__ = (
        Index("idx_item_batch_acct", "batch_no", "acct_id", "is_t0_init"),
        Index("idx_item_pcode", "cust_p_code"),
    )

    ledger_item_id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    cust_p_code: Mapped[str | None] = mapped_column(String(32))
    cust_name: Mapped[str | None] = mapped_column(String(200))
    acct_name: Mapped[str | None] = mapped_column(String(200))
    acct_cd: Mapped[str | None] = mapped_column(String(50))
    acct_id: Mapped[int | None] = mapped_column(BigInteger)
    bill_ym: Mapped[str | None] = mapped_column(String(10))
    batch_no: Mapped[str | None] = mapped_column(String(10))
    item_id: Mapped[int | None] = mapped_column(BigInteger)
    item_type: Mapped[str | None] = mapped_column(String(2))
    rmb_all: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    arrears_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    cancel_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    acct_subject_code: Mapped[str | None] = mapped_column(String(20))
    cust_m_code: Mapped[str | None] = mapped_column(String(50))
    cust_master_name: Mapped[str | None] = mapped_column(String(200))
    sap_no: Mapped[str | None] = mapped_column(String(50))
    sap_item: Mapped[str | None] = mapped_column(String(10))
    company_code: Mapped[str | None] = mapped_column(String(10))
    fiscal_year: Mapped[str | None] = mapped_column(String(10))
    voucher_date: Mapped[date | None] = mapped_column(Date)
    eda_batch_no: Mapped[str | None] = mapped_column(String(50))
    is_t0_init: Mapped[str] = mapped_column(String(2), default="0")
    create_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    update_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    create_staff: Mapped[int | None] = mapped_column(BigInteger)
    update_staff: Mapped[int | None] = mapped_column(BigInteger)
