"""
Ledger payoff (权责销账记录), report (权责台账报表) and diff (收付权责欠费差异) models.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, BigInt


class LedgerPayoffRecord(Base):
    """权责销账记录表."""
    __tablename__ = "ledger_payoff_record"
    __table_args__ = (
        Index("idx_payoff_claim", "ledger_claim_id", "status_cd"),
        Index("idx_payoff_item", "ledger_item_id", "status_cd"),
        Index("idx_payoff_date", "write_off_date"),
    )

    payoff_id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    cancel_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    ledger_claim_id: Mapped[int | None] = mapped_column(BigInteger)
    ledger_item_id: Mapped[int | None] = mapped_column(BigInteger)
    acct_cd: Mapped[str | None] = mapped_column(String(50))
    cust_p_code: Mapped[str | None] = mapped_column(String(32))
    status_cd: Mapped[str] = mapped_column(String(10), default="1000")
    write_off_date: Mapped[datetime | None] = mapped_column(DateTime)
    batch_no: Mapped[str | None] = mapped_column(String(50))
    remark: Mapped[str | None] = mapped_column(String(500))
    create_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    update_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    create_staff: Mapped[int | None] = mapped_column(BigInteger)
    update_staff: Mapped[int | None] = mapped_column(BigInteger)


class LedgerReportRecord(Base):
    """权责台账报表表."""
    __tablename__ = "ledger_report_record"
    __table_args__ = (
        Index("idx_report_month", "report_month"),
        Index("idx_report_pcode", "cust_p_code"),
    )

    report_id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    cust_p_code: Mapped[str | None] = mapped_column(String(32))
    cust_name: Mapped[str | None] = mapped_column(String(200))
    acct_name: Mapped[str | None] = mapped_column(String(200))
    acct_cd: Mapped[str | None] = mapped_column(String(50))
    bill_ym: Mapped[str | None] = mapped_column(String(10))
    rmb_all: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    arrears_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    cancel_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    used_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    available_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    acct_subject_code: Mapped[str | None] = mapped_column(String(20))
    cust_m_code: Mapped[str | None] = mapped_column(String(50))
    cust_master_name: Mapped[str | None] = mapped_column(String(200))
    sap_no: Mapped[str | None] = mapped_column(String(50))
    sap_item: Mapped[str | None] = mapped_column(String(10))
    company_code: Mapped[str | None] = mapped_column(String(10))
    fiscal_year: Mapped[str | None] = mapped_column(String(10))
    eda_batch_no: Mapped[str | None] = mapped_column(String(50))
    is_t0_init: Mapped[str | None] = mapped_column(String(2))
    report_month: Mapped[str | None] = mapped_column(String(10))
    create_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    update_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class LedgerAcctPayDiffRecord(Base):
    """收付权责欠费差异表."""
    __tablename__ = "ledger_acct_pay_diff_record"
    __table_args__ = (
        Index("idx_diff_period", "period"),
    )

    diff_id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    acct_name: Mapped[str | None] = mapped_column(String(200))
    acct_cd: Mapped[str | None] = mapped_column(String(50))
    cust_p_code: Mapped[str | None] = mapped_column(String(32))
    period: Mapped[str | None] = mapped_column(String(10))
    receivable_pay: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    receivable_accr: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    receipt_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    write_off_pay: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    write_off_accr: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    balance_pay: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    balance_accr: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    current_diff: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    begin_arrears_diff: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    end_arrears_diff: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    create_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    update_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
