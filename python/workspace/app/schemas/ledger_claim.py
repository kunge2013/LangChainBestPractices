"""Schemas for ledger claim (正式资金台账) and temp fund."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class LedgerClaimQuery(BaseModel):
    cust_p_code: str | None = None
    acct_name: str | None = None
    deposit_period: str | None = None
    status_cd: str | None = None
    is_t0_init: str | None = None
    available_balance_min: Decimal | None = None
    available_balance_max: Decimal | None = None
    page_num: int = 1
    page_size: int = 20


class LedgerClaimOut(BaseModel):
    fund_ledger_id: int
    payment_id: int | None = None
    finance_id: str | None = None
    temp_claim_id: int | None = None
    cust_p_code: str | None = None
    cust_name: str | None = None
    acct_name: str | None = None
    acct_code: str | None = None
    deposit_period: str | None = None
    deposit_amount: Decimal | None = None
    used_amount: Decimal | None = None
    available_balance: Decimal | None = None
    acct_subject_code: str | None = None
    status_cd: str | None = None
    is_t0_init: str | None = None
    create_time: datetime | None = None

    class Config:
        from_attributes = True


class CreateClaimRequest(BaseModel):
    payment_id: int
    finance_id: str
    cust_p_code: str
    deposit_amount: Decimal
    deposit_period: str
    claim_id: int | None = None


class CreateClaimResult(BaseModel):
    fund_ledger_id: int
    available_balance: Decimal


class FinanceQuery(BaseModel):
    payment_month: str | None = None
    cust_name: str | None = None
    page_num: int = 1
    page_size: int = 20


class FinanceOut(BaseModel):
    finance_id: str
    payment_cust_name: str | None = None
    bank_nbr: str | None = None
    payment_date: datetime | None = None
    payment_money: Decimal | None = None
    deposit_amount: Decimal | None = None

    class Config:
        from_attributes = True


class ClaimItem(BaseModel):
    claim_acct_id: int
    claim_amount: Decimal


class TempClaimRequest(BaseModel):
    finance_id: int
    claim_list: list[ClaimItem]
    total_claim_amount: Decimal
    remark: str | None = None


class ClaimResultDetail(BaseModel):
    temp_claim_id: int
    temp_ledger_id: int
    claim_acct_id: int
    claim_acct_cd: str | None = None
    claim_p_code: str | None = None
    claim_amount: Decimal


class TempClaimResult(BaseModel):
    finance_id: int
    claim_count: int
    total_claim_amount: Decimal
    details: list[ClaimResultDetail] = Field(default_factory=list)


class TempFundQuery(BaseModel):
    cust_p_code: str | None = None
    acct_name: str | None = None
    deposit_period: str | None = None
    page_num: int = 1
    page_size: int = 20


class TempFundOut(BaseModel):
    temp_fund_ledger_id: int
    finance_id: str | None = None
    temp_claim_id: int | None = None
    cust_p_code: str | None = None
    cust_name: str | None = None
    acct_name: str | None = None
    acct_code: str | None = None
    deposit_period: str | None = None
    deposit_amount: Decimal | None = None
    acct_subject_code: str | None = None
    create_time: datetime | None = None

    class Config:
        from_attributes = True
