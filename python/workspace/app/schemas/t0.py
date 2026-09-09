"""Schemas for T0 source and base records."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel

from app.schemas.common import PageResponse


class LedgerT0SourceRecordDTO(BaseModel):
    """Excel row DTO for T0 source import."""
    company_code: str = "A000"
    fiscal_year: str = ""
    sap_no: str | None = None
    sap_item: str | None = None
    during: str = ""
    voucher_date: date | None = None
    cust_m_code: str = ""
    amount: Decimal = Decimal("0")
    cust_p_code: str | None = None
    acct_subject_code: str | None = None
    bill_ym: str | None = None
    amount_type: str | None = None


class LedgerT0SourceRecordOut(BaseModel):
    t0_item_id: int
    cust_p_code: str | None = None
    cust_m_code: str | None = None
    sap_no: str | None = None
    sap_item: str | None = None
    company_code: str | None = None
    fiscal_year: str | None = None
    during: str | None = None
    bill_ym: str | None = None
    amount: Decimal | None = None
    amount_type: str | None = None
    voucher_date: date | None = None
    acct_subject_code: str | None = None

    class Config:
        from_attributes = True


class T0BaseImportItem(BaseModel):
    cust_p_code: str
    t0_arrears_acct: Decimal = Decimal("0")
    t0_arrears_fin: Decimal = Decimal("0")
    diff_remark: str | None = None


class T0BaseImportRequest(BaseModel):
    cutoff_period: str
    data_list: list[T0BaseImportItem]


class T0BaseImportResult(BaseModel):
    insert_count: int = 0
    update_count: int = 0
    total_diff_amount: Decimal = Decimal("0")


class T0BaseQuery(BaseModel):
    cust_p_code: str | None = None
    cutoff_period: str | None = None
    page_num: int = 1
    page_size: int = 20


class T0BaseOut(BaseModel):
    t0_base_id: int
    cust_p_code: str
    cutoff_period: str
    t0_arrears_acct: Decimal
    t0_arrears_fin: Decimal
    t0_arrears_diff: Decimal
    diff_remark: str | None = None

    class Config:
        from_attributes = True
