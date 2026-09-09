"""
Service for report (权责台账报表) operations.
Covers: generate (9.1), query (9.2), export (9.3).
"""
from __future__ import annotations

import io
import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from openpyxl import Workbook
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import ReportError
from app.models.ledger_claim import LedgerClaimRecord, LedgerTempFundRecord
from app.models.ledger_item import LedgerItemRecord
from app.models.ledger_payoff import LedgerReportRecord
from app.schemas.common import PageResponse
from app.schemas.writeoff import (
    ExportResult,
    ReportGenerateRequest,
    ReportGenerateResult,
    ReportOut,
)
from app.utils import current_staff_id

logger = logging.getLogger(__name__)


# ── 9.1 Generate Report ───────────────────────────────────────────────────────


def generate_report(
    db: Session, request: ReportGenerateRequest
) -> ReportGenerateResult:
    """Generate monthly report by merging three ledger tables."""
    if not request.report_month:
        raise ReportError("RPT_001", "报表月份不能为空")

    report_month = request.report_month
    staff_id = current_staff_id()
    now = datetime.now()

    # Delete existing records for this report_month
    db.execute(
        LedgerReportRecord.__table__.delete().where(
            LedgerReportRecord.report_month == report_month
        )
    )
    db.flush()

    # Aggregate arrears by cust_p_code + acct_cd + acct_subject_code
    arrears_rows = db.execute(
        select(
            LedgerItemRecord.cust_p_code,
            LedgerItemRecord.cust_name,
            LedgerItemRecord.acct_name,
            LedgerItemRecord.acct_cd,
            LedgerItemRecord.acct_subject_code,
            LedgerItemRecord.cust_m_code,
            LedgerItemRecord.cust_master_name,
            func.min(LedgerItemRecord.bill_ym).label("min_bill_ym"),
            func.sum(LedgerItemRecord.rmb_all).label("sum_rmb"),
            func.sum(LedgerItemRecord.arrears_amount).label("sum_arrears"),
            func.sum(LedgerItemRecord.cancel_amount).label("sum_cancel"),
            func.max(LedgerItemRecord.is_t0_init).label("is_t0_init"),
        )
        .where(LedgerItemRecord.cust_p_code.is_not(None))
        .group_by(
            LedgerItemRecord.cust_p_code,
            LedgerItemRecord.acct_cd,
            LedgerItemRecord.acct_subject_code,
        )
    ).all()

    # Build lookup for formal fund
    fund_rows = db.execute(
        select(
            LedgerClaimRecord.cust_p_code,
            LedgerClaimRecord.acct_cd,
            LedgerClaimRecord.acct_subject_code,
            func.sum(LedgerClaimRecord.deposit_amount).label("sum_deposit"),
            func.sum(LedgerClaimRecord.used_amount).label("sum_used"),
            func.sum(LedgerClaimRecord.available_balance).label("sum_avail"),
        )
        .where(LedgerClaimRecord.cust_p_code.is_not(None))
        .group_by(
            LedgerClaimRecord.cust_p_code,
            LedgerClaimRecord.acct_cd,
            LedgerClaimRecord.acct_subject_code,
        )
    ).all()

    fund_lookup: dict[tuple, dict] = {}
    for fr in fund_rows:
        key = (fr.cust_p_code, fr.acct_cd, fr.acct_subject_code)
        fund_lookup[key] = {
            "deposit": fr.sum_deposit or Decimal("0"),
            "used": fr.sum_used or Decimal("0"),
            "avail": fr.sum_avail or Decimal("0"),
        }

    # Build lookup for temp fund
    temp_rows = db.execute(
        select(
            LedgerTempFundRecord.cust_p_code,
            LedgerTempFundRecord.acct_cd,
            func.sum(LedgerTempFundRecord.deposit_amount).label("sum_deposit"),
        )
        .where(LedgerTempFundRecord.cust_p_code.is_not(None))
        .group_by(
            LedgerTempFundRecord.cust_p_code,
            LedgerTempFundRecord.acct_cd,
        )
    ).all()

    temp_lookup: dict[tuple, Decimal] = {}
    for tr in temp_rows:
        key = (tr.cust_p_code, tr.acct_cd)
        temp_lookup[key] = tr.sum_deposit or Decimal("0")

    total_records = 0
    total_arrears = Decimal("0")
    total_write_off = Decimal("0")
    total_deposit = Decimal("0")

    for ar in arrears_rows:
        key = (ar.cust_p_code, ar.acct_cd, ar.acct_subject_code)
        fund_info = fund_lookup.get(key, {})
        temp_key = (ar.cust_p_code, ar.acct_cd)
        temp_deposit = temp_lookup.get(temp_key, Decimal("0"))

        deposit_amount = (fund_info.get("deposit", Decimal("0"))
                          + temp_deposit)
        used_amount = fund_info.get("used", Decimal("0"))
        avail_balance = fund_info.get("avail", Decimal("0"))

        rmb_all = ar.sum_rmb or Decimal("0")
        arrears_amount = ar.sum_arrears or Decimal("0")
        cancel_amount = ar.sum_cancel or Decimal("0")

        report = LedgerReportRecord(
            cust_p_code=ar.cust_p_code,
            cust_name=ar.cust_name,
            acct_name=ar.acct_name,
            acct_cd=ar.acct_cd,
            bill_ym=ar.min_bill_ym,
            rmb_all=rmb_all,
            arrears_amount=arrears_amount,
            cancel_amount=cancel_amount,
            deposit_amount=deposit_amount,
            used_amount=used_amount,
            available_balance=avail_balance,
            acct_subject_code=ar.acct_subject_code,
            cust_m_code=ar.cust_m_code,
            cust_master_name=ar.cust_master_name,
            is_t0_init=ar.is_t0_init,
            report_month=report_month,
        )
        db.add(report)
        total_records += 1
        total_arrears += arrears_amount
        total_write_off += cancel_amount
        total_deposit += deposit_amount

    db.flush()

    return ReportGenerateResult(
        report_month=report_month,
        total_records=total_records,
        total_arrears_amount=total_arrears,
        total_write_off_amount=total_write_off,
        total_deposit_amount=total_deposit,
        generate_time=now,
    )


# ── 9.2 Query Report ──────────────────────────────────────────────────────────


def query_report(
    db: Session,
    cust_p_code: str | None = None,
    acct_name: str | None = None,
    ledger_period: str | None = None,
    report_month: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> PageResponse[ReportOut]:
    """Paginated query of report records."""
    stmt = select(LedgerReportRecord)
    count_stmt = select(func.count()).select_from(LedgerReportRecord)

    if report_month:
        stmt = stmt.where(LedgerReportRecord.report_month == report_month)
        count_stmt = count_stmt.where(
            LedgerReportRecord.report_month == report_month
        )
    if cust_p_code:
        stmt = stmt.where(LedgerReportRecord.cust_p_code == cust_p_code)
        count_stmt = count_stmt.where(LedgerReportRecord.cust_p_code == cust_p_code)
    if acct_name:
        stmt = stmt.where(LedgerReportRecord.acct_name.like(f"%{acct_name}%"))
        count_stmt = count_stmt.where(
            LedgerReportRecord.acct_name.like(f"%{acct_name}%")
        )
    if ledger_period:
        stmt = stmt.where(LedgerReportRecord.bill_ym == ledger_period)
        count_stmt = count_stmt.where(LedgerReportRecord.bill_ym == ledger_period)

    total = db.execute(count_stmt).scalar() or 0
    rows = db.execute(
        stmt.order_by(
            LedgerReportRecord.cust_p_code,
            LedgerReportRecord.acct_cd,
        ).offset(offset).limit(limit)
    ).scalars().all()

    out_list = [
        ReportOut(
            report_id=r.report_id,
            cust_p_code=r.cust_p_code,
            cust_name=r.cust_name,
            acct_name=r.acct_name,
            acct_code=r.acct_cd,
            ledger_period=r.bill_ym,
            receivable_amount=r.rmb_all,
            arrears_amount=r.arrears_amount,
            write_off_amount=r.cancel_amount,
            deposit_amount=r.deposit_amount,
            used_amount=r.used_amount,
            available_balance=r.available_balance,
            acct_subject_code=r.acct_subject_code,
            is_t0_init=r.is_t0_init,
        )
        for r in rows
    ]
    return PageResponse(total=total, list=out_list)


# ── 9.3 Export Report ─────────────────────────────────────────────────────────


def export_report(
    db: Session,
    cust_p_code: str | None = None,
    acct_name: str | None = None,
    ledger_period: str | None = None,
    report_month: str | None = None,
) -> ExportResult:
    """Export report records to Excel. Returns file URL and count."""
    page = query_report(
        db,
        cust_p_code=cust_p_code,
        acct_name=acct_name,
        ledger_period=ledger_period,
        report_month=report_month,
        offset=0,
        limit=100000,
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "权责台账报表"
    headers = [
        "P码", "客户名称", "账户名称", "账户编码", "权责账期",
        "应收金额", "欠费金额", "销账金额", "预存金额", "已使用金额",
        "可用余额", "会计科目",
    ]
    ws.append(headers)

    for item in page.list:
        ws.append([
            item.cust_p_code,
            item.cust_name,
            item.acct_name,
            item.acct_code,
            item.ledger_period,
            float(item.receivable_amount or 0),
            float(item.arrears_amount or 0),
            float(item.write_off_amount or 0),
            float(item.deposit_amount or 0),
            float(item.used_amount or 0),
            float(item.available_balance or 0),
            item.acct_subject_code,
        ])

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_name = f"权责台账报表_{timestamp}.xlsx"
    file_url = f"/download/{file_name}"

    return ExportResult(
        file_url=file_url,
        file_name=file_name,
        record_count=len(page.list),
    )
