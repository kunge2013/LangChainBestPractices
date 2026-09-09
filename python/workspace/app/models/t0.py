"""
T0 source data and T0 base record models.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, BigInt


class LedgerT0SourceRecord(Base):
    """T0基础数据源表 – raw data imported from Excel."""
    __tablename__ = "ledger_t0_source_record"

    t0_item_id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    cust_p_code: Mapped[str | None] = mapped_column(String(32))
    cust_m_code: Mapped[str | None] = mapped_column(String(32))
    sap_no: Mapped[str | None] = mapped_column(String(50))
    sap_item: Mapped[str | None] = mapped_column(String(10))
    company_code: Mapped[str | None] = mapped_column(String(10), default="A000")
    fiscal_year: Mapped[str | None] = mapped_column(String(10))
    during: Mapped[str | None] = mapped_column(String(10))
    bill_ym: Mapped[str | None] = mapped_column(String(10))
    amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    amount_type: Mapped[str | None] = mapped_column(String(10))
    voucher_date: Mapped[date | None] = mapped_column(Date)
    acct_subject_code: Mapped[str | None] = mapped_column(String(20))


class LedgerT0BaseRecord(Base):
    """T0基准存量欠费表 –固化财务T0值."""
    __tablename__ = "ledger_t0_base_record"

    t0_base_id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    cust_p_code: Mapped[str] = mapped_column(String(32), nullable=False)
    cutoff_period: Mapped[str] = mapped_column(String(10), nullable=False)
    t0_arrears_acct: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    t0_arrears_fin: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    t0_arrears_diff: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    diff_remark: Mapped[str | None] = mapped_column(String(500))
    create_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    update_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    create_staff: Mapped[int | None] = mapped_column(BigInteger)
    update_staff: Mapped[int | None] = mapped_column(BigInteger)
