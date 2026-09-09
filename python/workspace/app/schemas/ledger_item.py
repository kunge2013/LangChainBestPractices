"""Schemas for ledger item (权责欠费台账)."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from app.schemas.common import PageResponse


class T0ArrearsImportResult(BaseModel):
    success_count: int
    source_count: int


class EdaItemDTO(BaseModel):
    acct_subject_code: str
    rmb_all: Decimal
    arrears_amount: Decimal
    acct_id: int
    bill_ym: str
    item_id: int
    item_type: str


class EdaImportResult(BaseModel):
    batch_no: str
    delete_count: int = 0
    insert_count: int = 0
    total_amount: Decimal = Decimal("0")
    failed_acct_count: int = 0


class LedgerItemQuery(BaseModel):
    cust_p_code: str | None = None
    acct_name: str | None = None
    arrears_period: str | None = None
    is_t0_init: str | None = None
    page_num: int = 1
    page_size: int = 20


class LedgerItemOut(BaseModel):
    arrears_ledger_id: int
    cust_p_code: str | None = None
    cust_name: str | None = None
    acct_name: str | None = None
    acct_code: str | None = None
    arrears_period: str | None = None
    receivable_amount: Decimal | None = None
    arrears_amount: Decimal | None = None
    write_off_amount: Decimal | None = None
    acct_subject_code: str | None = None
    is_t0_init: str | None = None
    create_time: datetime | None = None

    class Config:
        from_attributes = True


class AcctInfoVO(BaseModel):
    """Account info result from PG query (P-code based lookup)."""
    party_nbr: str | None = None
    cust_name: str | None = None
    acct_name: str | None = None
    acct_cd: str | None = None
    acct_id: int | None = None


class AcctInfoByAcctIdVO(BaseModel):
    """Account info result from PG query (ACCT_ID based reverse lookup)."""
    acct_id: int
    cust_name: str | None = None
    party_nbr: str | None = None
    acct_name: str | None = None
    acct_cd: str | None = None


class T0RefreshResult(BaseModel):
    refreshed_p_code_count: int = 0
    refreshed_count: int = 0
    unrefreshed_p_code_count: int = 0
    failed_p_code_count: int = 0
    fail_p_code_list: list[dict] = Field(default_factory=list)


class EdaRefreshResult(BaseModel):
    refreshed_acct_id_count: int = 0
    refreshed_count: int = 0
    unrefreshed_acct_id_count: int = 0
    failed_acct_id_count: int = 0
    fail_acct_id_list: list[dict] = Field(default_factory=list)
