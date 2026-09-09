"""Schemas for write-off (权责销账), reverse, report and diff."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ── Write-off ──────────────────────────────────────────────────────────────────
class WriteOffRequest(BaseModel):
    write_off_month: str
    cust_p_code: str | None = None
    batch_no: str | None = None
    is_dry_run: bool = False


class WriteOffDetail(BaseModel):
    write_off_id: int | None = None
    cust_p_code: str | None = None
    acct_code: str | None = None
    write_off_amount: Decimal
    fund_ledger_id: int | None = None
    arrears_ledger_id: int | None = None
    write_off_date: datetime | None = None


class WriteOffResult(BaseModel):
    batch_no: str | None = None
    total_write_off_amount: Decimal = Decimal("0")
    write_off_count: int = 0
    fund_used_count: int = 0
    arrears_cleared_count: int = 0
    details: list[WriteOffDetail] = Field(default_factory=list)


class PreCheckRequest(BaseModel):
    write_off_month: str


class PreCheckResult(BaseModel):
    can_write_off: bool
    unclaimed_count: int = 0
    unclaimed_amount: Decimal = Decimal("0")
    total_arrears_amount: Decimal = Decimal("0")
    total_fund_amount: Decimal = Decimal("0")
    estimated_write_off: Decimal = Decimal("0")


class ReverseRequest(BaseModel):
    write_off_id: int
    reason: str | None = None


class ReverseResult(BaseModel):
    write_off_id: int
    reverse_write_off_id: int | None = None
    restored_arrears_amount: Decimal
    restored_fund_balance: Decimal


# ── Revoke claim ──────────────────────────────────────────────────────────────
class RevokeClaimRequest(BaseModel):
    payment_id: int
    reason: str | None = None


class RevokePayoffDetail(BaseModel):
    payoff_id: int
    reverse_payoff_id: int | None = None
    restore_arrears_amount: Decimal
    restore_fund_balance: Decimal


class RevokeResult(BaseModel):
    reverse_amount: Decimal = Decimal("0")
    payoff_count: int = 0
    restored_fund_amount: Decimal = Decimal("0")
    details: list[RevokePayoffDetail] = Field(default_factory=list)


# ── Report ─────────────────────────────────────────────────────────────────────
class ReportGenerateRequest(BaseModel):
    report_month: str


class ReportGenerateResult(BaseModel):
    report_month: str
    total_records: int = 0
    total_arrears_amount: Decimal = Decimal("0")
    total_write_off_amount: Decimal = Decimal("0")
    total_deposit_amount: Decimal = Decimal("0")
    generate_time: datetime | None = None


class ReportQuery(BaseModel):
    cust_p_code: str | None = None
    acct_name: str | None = None
    ledger_period: str | None = None
    report_month: str | None = None
    page_num: int = 1
    page_size: int = 20


class ReportOut(BaseModel):
    report_id: int
    cust_p_code: str | None = None
    cust_name: str | None = None
    acct_name: str | None = None
    acct_code: str | None = None
    ledger_period: str | None = None
    receivable_amount: Decimal | None = None
    arrears_amount: Decimal | None = None
    write_off_amount: Decimal | None = None
    deposit_amount: Decimal | None = None
    used_amount: Decimal | None = None
    available_balance: Decimal | None = None
    acct_subject_code: str | None = None
    is_t0_init: str | None = None

    class Config:
        from_attributes = True


class ExportResult(BaseModel):
    file_url: str
    file_name: str
    record_count: int


# ── Payoff query ──────────────────────────────────────────────────────────────
class PayoffQuery(BaseModel):
    cust_p_code: str | None = None
    acct_name: str | None = None
    write_off_date_start: str | None = None
    write_off_date_end: str | None = None
    status: str | None = None
    page_num: int = 1
    page_size: int = 20


class PayoffOut(BaseModel):
    write_off_id: int
    write_off_amount: Decimal
    fund_ledger_id: int | None = None
    arrears_ledger_id: int | None = None
    acct_code: str | None = None
    cust_p_code: str | None = None
    status: str | None = None
    write_off_date: datetime | None = None
    batch_no: str | None = None
    create_time: datetime | None = None

    class Config:
        from_attributes = True


# ── Diff ──────────────────────────────────────────────────────────────────────
class DiffGenerateRequest(BaseModel):
    period: str


class DiffGenerateResult(BaseModel):
    period: str
    total_records: int = 0
    total_current_diff: Decimal = Decimal("0")
    generate_time: datetime | None = None


class DiffQuery(BaseModel):
    acct_name: str | None = None
    period: str | None = None
    page_num: int = 1
    page_size: int = 20


class DiffOut(BaseModel):
    diff_id: int
    acct_name: str | None = None
    acct_code: str | None = None
    cust_p_code: str | None = None
    period: str | None = None
    receivable_pay: Decimal | None = None
    receivable_accr: Decimal | None = None
    receipt_amount: Decimal | None = None
    write_off_pay: Decimal | None = None
    write_off_accr: Decimal | None = None
    balance_pay: Decimal | None = None
    balance_accr: Decimal | None = None
    current_diff: Decimal | None = None
    begin_arrears_diff: Decimal | None = None
    end_arrears_diff: Decimal | None = None

    class Config:
        from_attributes = True
