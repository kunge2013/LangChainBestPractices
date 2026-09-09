"""
Ledger claim (正式资金台账) and temp fund (临时资金台账) models.
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


class LedgerClaimRecord(Base):
    """正式资金台账表."""
    __tablename__ = "ledger_claim_record"
    __table_args__ = (
        Index("idx_claim_payment", "payment_id", "finance_id"),
        Index("idx_claim_pcode", "cust_p_code"),
    )

    ledger_claim_id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    payment_id: Mapped[int | None] = mapped_column(BigInteger)
    finance_id: Mapped[str | None] = mapped_column(String(50))
    claim_id: Mapped[int | None] = mapped_column(BigInteger)
    cust_p_code: Mapped[str | None] = mapped_column(String(32))
    cust_name: Mapped[str | None] = mapped_column(String(200))
    acct_name: Mapped[str | None] = mapped_column(String(200))
    acct_cd: Mapped[str | None] = mapped_column(String(50))
    deposit_ym: Mapped[str | None] = mapped_column(String(10))
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    used_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    available_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    acct_subject_code: Mapped[str | None] = mapped_column(String(20), default="合同负债")
    cust_m_code: Mapped[str | None] = mapped_column(String(50))
    cust_master_name: Mapped[str | None] = mapped_column(String(200))
    sap_no: Mapped[str | None] = mapped_column(String(50))
    sap_item: Mapped[str | None] = mapped_column(String(10))
    company_code: Mapped[str | None] = mapped_column(String(10), default="A000")
    fiscal_year: Mapped[str | None] = mapped_column(String(10))
    voucher_date: Mapped[date | None] = mapped_column(Date)
    eda_batch_no: Mapped[str | None] = mapped_column(String(50))
    is_t0_init: Mapped[str] = mapped_column(String(2), default="0")
    status_cd: Mapped[str] = mapped_column(String(10), default="1000")
    create_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    update_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    create_staff: Mapped[int | None] = mapped_column(BigInteger)
    update_staff: Mapped[int | None] = mapped_column(BigInteger)


class TmpClaimRecord(Base):
    """资金临时认领表."""
    __tablename__ = "tmp_claim_record"
    __table_args__ = (
        Index("idx_tmp_claim_finance", "finance_id", "status_cd"),
    )

    claim_id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    finance_id: Mapped[int | None] = mapped_column(BigInteger)
    payment_cust_name: Mapped[str | None] = mapped_column(String(200))
    bank_nbr: Mapped[str | None] = mapped_column(String(50))
    payment_date: Mapped[datetime | None] = mapped_column(DateTime)
    payment_money: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    claim_date: Mapped[datetime | None] = mapped_column(DateTime)
    claim_acct_cd: Mapped[str | None] = mapped_column(String(50))
    claim_acct_id: Mapped[int | None] = mapped_column(BigInteger)
    claim_staff: Mapped[str | None] = mapped_column(String(50))
    claim_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    claim_p_code: Mapped[str | None] = mapped_column(String(32))
    status_cd: Mapped[str] = mapped_column(String(10), default="1000")
    remark: Mapped[str | None] = mapped_column(String(500))
    create_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    update_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    create_staff: Mapped[int | None] = mapped_column(BigInteger)
    update_staff: Mapped[int | None] = mapped_column(BigInteger)


class LedgerTempFundRecord(Base):
    """临时资金台账表."""
    __tablename__ = "ledger_temp_fund_record"
    __table_args__ = (
        Index("idx_temp_fund_claim", "finance_id", "claim_id"),
    )

    temp_ledger_claim_id: Mapped[int] = mapped_column(BigInt, primary_key=True, autoincrement=True)
    finance_id: Mapped[int | None] = mapped_column(BigInteger)
    claim_id: Mapped[int | None] = mapped_column(BigInteger)
    cust_p_code: Mapped[str | None] = mapped_column(String(32))
    cust_name: Mapped[str | None] = mapped_column(String(200))
    acct_name: Mapped[str | None] = mapped_column(String(200))
    acct_cd: Mapped[str | None] = mapped_column(String(50))
    acct_id: Mapped[int | None] = mapped_column(BigInteger)
    deposit_ym: Mapped[str | None] = mapped_column(String(10))
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    acct_subject_code: Mapped[str | None] = mapped_column(String(20), default="合同负债")
    cust_m_code: Mapped[str | None] = mapped_column(String(50))
    cust_master_name: Mapped[str | None] = mapped_column(String(200))
    sap_no: Mapped[str | None] = mapped_column(String(50))
    sap_item: Mapped[str | None] = mapped_column(String(10))
    company_code: Mapped[str | None] = mapped_column(String(10), default="A000")
    fiscal_year: Mapped[str | None] = mapped_column(String(10))
    voucher_date: Mapped[date | None] = mapped_column(Date)
    eda_batch_no: Mapped[str | None] = mapped_column(String(50))
    is_t0_init: Mapped[str] = mapped_column(String(2), default="0")
    create_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    update_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    create_staff: Mapped[int | None] = mapped_column(BigInteger)
    update_staff: Mapped[int | None] = mapped_column(BigInteger)
