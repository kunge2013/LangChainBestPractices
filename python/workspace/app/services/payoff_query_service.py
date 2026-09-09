"""
Service for payoff query (权责销账查询) operations.
Covers: payoff query (10.1), payoff export (10.2).
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import LedgerError
from app.models.ledger_payoff import LedgerPayoffRecord
from app.schemas.common import PageResponse
from app.schemas.writeoff import ExportResult, PayoffOut

logger = logging.getLogger(__name__)

STATUS_MAP = {"1000": "正常", "1200": "返销", "1300": "作废"}


# ── 10.1 Payoff Query ──────────────────────────────────────────────────────────


def query_payoff_records(
    db: Session,
    cust_p_code: str | None = None,
    acct_name: str | None = None,
    write_off_date_start: str | None = None,
    write_off_date_end: str | None = None,
    status: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> PageResponse[PayoffOut]:
    """Paginated query of write-off records."""
    stmt = select(LedgerPayoffRecord)
    count_stmt = select(func.count()).select_from(LedgerPayoffRecord)

    if cust_p_code:
        stmt = stmt.where(LedgerPayoffRecord.cust_p_code == cust_p_code)
        count_stmt = count_stmt.where(LedgerPayoffRecord.cust_p_code == cust_p_code)
    if acct_name:
        stmt = stmt.where(LedgerPayoffRecord.acct_cd.like(f"%{acct_name}%"))
        count_stmt = count_stmt.where(LedgerPayoffRecord.acct_cd.like(f"%{acct_name}%"))
    if write_off_date_start:
        stmt = stmt.where(LedgerPayoffRecord.write_off_date >= write_off_date_start)
        count_stmt = count_stmt.where(
            LedgerPayoffRecord.write_off_date >= write_off_date_start
        )
    if write_off_date_end:
        stmt = stmt.where(LedgerPayoffRecord.write_off_date <= write_off_date_end)
        count_stmt = count_stmt.where(
            LedgerPayoffRecord.write_off_date <= write_off_date_end
        )
    if status:
        stmt = stmt.where(LedgerPayoffRecord.status_cd == status)
        count_stmt = count_stmt.where(LedgerPayoffRecord.status_cd == status)

    total = db.execute(count_stmt).scalar() or 0
    rows = db.execute(
        stmt.order_by(
            LedgerPayoffRecord.write_off_date.desc(),
            LedgerPayoffRecord.payoff_id.desc(),
        ).offset(offset).limit(limit)
    ).scalars().all()

    out_list = [
        PayoffOut(
            write_off_id=r.payoff_id,
            write_off_amount=r.cancel_amount,
            fund_ledger_id=r.ledger_claim_id,
            arrears_ledger_id=r.ledger_item_id,
            acct_code=r.acct_cd,
            cust_p_code=r.cust_p_code,
            status=r.status_cd,
            write_off_date=r.write_off_date,
            batch_no=r.batch_no,
            create_time=r.create_date,
        )
        for r in rows
    ]
    return PageResponse(total=total, list=out_list)


# ── 10.2 Payoff Export ─────────────────────────────────────────────────────────


def export_payoff_records(
    db: Session,
    cust_p_code: str | None = None,
    acct_name: str | None = None,
    write_off_date_start: str | None = None,
    write_off_date_end: str | None = None,
    status: str | None = None,
) -> ExportResult:
    """Export write-off records to Excel. Negative amounts highlighted in red."""
    page = query_payoff_records(
        db,
        cust_p_code=cust_p_code,
        acct_name=acct_name,
        write_off_date_start=write_off_date_start,
        write_off_date_end=write_off_date_end,
        status=status,
        offset=0,
        limit=100000,
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "权责销账查询"
    headers = [
        "销账ID", "销账金额", "资金台账ID", "欠费台账ID",
        "账户编码", "P码", "状态", "销账日期", "批次号",
    ]
    ws.append(headers)

    red_font = Font(color="FF0000")
    for item in page.list:
        row = [
            item.write_off_id,
            float(item.write_off_amount or 0),
            item.fund_ledger_id,
            item.arrears_ledger_id,
            item.acct_code,
            item.cust_p_code,
            STATUS_MAP.get(item.status, item.status),
            str(item.write_off_date) if item.write_off_date else "",
            item.batch_no,
        ]
        ws.append(row)
        # Highlight negative amounts in red
        if (item.write_off_amount or 0) < 0:
            for col in range(1, len(headers) + 1):
                ws.cell(row=ws.max_row, column=col).font = red_font

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    file_name = f"权责销账查询_{timestamp}.xlsx"
    file_url = f"/download/{file_name}"

    return ExportResult(
        file_url=file_url,
        file_name=file_name,
        record_count=len(page.list),
    )
