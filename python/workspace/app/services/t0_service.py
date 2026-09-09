"""
Service for T0 source data import (2.5) and T0 base record (11.x).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Sequence

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.exceptions import LedgerError
from app.models.t0 import LedgerT0BaseRecord, LedgerT0SourceRecord
from app.schemas.t0 import (
    LedgerT0SourceRecordDTO,
    T0BaseImportItem,
    T0BaseImportRequest,
    T0BaseImportResult,
    T0BaseOut,
)
from app.utils import current_staff_id, now_yyyymm

BATCH_SIZE = 1000


def _parse_excel_row(row: dict) -> LedgerT0SourceRecordDTO | None:
    """Parse one raw dict (from openpyxl) into a DTO.

    Returns ``None`` if company_code is empty (skip row).
    """
    company_code = str(row.get("公司（公司代码）") or row.get("company_code") or "").strip()
    if not company_code:
        return None

    fiscal_year = str(row.get("年（财年）") or row.get("fiscal_year") or "").strip()
    sap_no = str(row.get("凭证号码（SAP凭证号)") or row.get("sap_no") or "").strip() or None
    sap_item = str(row.get("项（SAP凭证行项）") or row.get("sap_item") or "").strip() or None
    during = str(row.get("期间") or row.get("during") or "").strip()
    voucher_date_raw = row.get("过帐日期") or row.get("voucher_date")
    cust_m_code = str(row.get("对象(客户编码（M码）)") or row.get("cust_m_code") or "").strip()
    amount_raw = row.get("本位币金额（正数为欠费金额，负数为预存金额）") or row.get("amount") or 0
    acct_subject_code = str(row.get("会计科目编码") or row.get("acct_subject_code") or "").strip() or None

    # Parse amount
    amount = Decimal(str(amount_raw)) if amount_raw else Decimal("0")

    # Parse voucher_date
    voucher_date = None
    if voucher_date_raw:
        if isinstance(voucher_date_raw, datetime):
            voucher_date = voucher_date_raw.date()
        else:
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
                try:
                    voucher_date = datetime.strptime(str(voucher_date_raw).strip(), fmt).date()
                    break
                except ValueError:
                    continue

    # Calculate bill_ym: fiscal_year + during (zero-padded to 2 digits)
    bill_ym = None
    if fiscal_year and during:
        try:
            bill_ym = f"{fiscal_year}{int(during):02d}"
        except (ValueError, TypeError):
            bill_ym = f"{fiscal_year}{during}"

    # Calculate amount_type: positive -> '0' (arrears), negative -> '1' (prepay)
    amount_type = "0" if amount > 0 else "1"

    return LedgerT0SourceRecordDTO(
        company_code=company_code,
        fiscal_year=fiscal_year,
        sap_no=sap_no,
        sap_item=sap_item,
        during=during,
        voucher_date=voucher_date,
        cust_m_code=cust_m_code,
        amount=amount,
        cust_p_code=None,
        acct_subject_code=acct_subject_code,
        bill_ym=bill_ym,
        amount_type=amount_type,
    )


def import_source_data(db: Session, rows: list[dict]) -> int:
    """Import raw Excel rows into ``ledger_t0_source_record``.

    Args:
        db: Active SQLAlchemy session.
        rows: List of raw dicts from openpyxl sheet iteration.

    Returns:
        Number of records imported.

    Raises:
        LedgerError: If no valid data.
    """
    batch: list[LedgerT0SourceRecord] = []
    total = 0

    for row in rows:
        dto = _parse_excel_row(row)
        if dto is None:
            continue

        entity = LedgerT0SourceRecord(
            cust_p_code=dto.cust_p_code,
            cust_m_code=dto.cust_m_code,
            sap_no=dto.sap_no,
            sap_item=dto.sap_item,
            company_code=dto.company_code,
            fiscal_year=dto.fiscal_year,
            during=dto.during,
            bill_ym=dto.bill_ym,
            amount=dto.amount,
            amount_type=dto.amount_type,
            voucher_date=dto.voucher_date,
            acct_subject_code=dto.acct_subject_code,
        )
        batch.append(entity)
        total += 1

        if len(batch) >= BATCH_SIZE:
            db.add_all(batch)
            db.flush()
            batch.clear()

    if batch:
        db.add_all(batch)
        db.flush()

    if total == 0:
        raise LedgerError("T0_003", "没有有效的数据可导入")

    return total


# ── T0 Base Record (11.x) ───────────────────────────────────────────────────────


def import_t0_base(db: Session, request: T0BaseImportRequest) -> T0BaseImportResult:
    """Import T0 base records with upsert semantics."""
    cutoff = request.cutoff_period
    if not cutoff:
        raise LedgerError("T0_001", "截止账期不能为空")

    insert_count = 0
    update_count = 0
    total_diff = Decimal("0")

    for item in request.data_list:
        existing = db.execute(
            select(LedgerT0BaseRecord).where(
                LedgerT0BaseRecord.cust_p_code == item.cust_p_code,
                LedgerT0BaseRecord.cutoff_period == cutoff,
            )
        ).scalar_one_or_none()

        diff = item.t0_arrears_acct - item.t0_arrears_fin
        total_diff += diff

        if existing:
            existing.t0_arrears_acct = item.t0_arrears_acct
            existing.t0_arrears_fin = item.t0_arrears_fin
            existing.t0_arrears_diff = diff
            existing.diff_remark = item.diff_remark
            existing.update_date = datetime.now()
            update_count += 1
        else:
            rec = LedgerT0BaseRecord(
                cust_p_code=item.cust_p_code,
                cutoff_period=cutoff,
                t0_arrears_acct=item.t0_arrears_acct,
                t0_arrears_fin=item.t0_arrears_fin,
                t0_arrears_diff=diff,
                diff_remark=item.diff_remark,
                create_staff=current_staff_id(),
                update_staff=current_staff_id(),
            )
            db.add(rec)
            insert_count += 1

    db.flush()
    return T0BaseImportResult(
        insert_count=insert_count,
        update_count=update_count,
        total_diff_amount=total_diff,
    )


def query_t0_base(
    db: Session,
    cust_p_code: str | None = None,
    cutoff_period: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[int, list[T0BaseOut]]:
    """Query T0 base records with pagination."""
    from sqlalchemy import func

    count_stmt = select(func.count()).select_from(LedgerT0BaseRecord)
    stmt = select(LedgerT0BaseRecord)

    if cust_p_code:
        count_stmt = count_stmt.where(LedgerT0BaseRecord.cust_p_code == cust_p_code)
        stmt = stmt.where(LedgerT0BaseRecord.cust_p_code == cust_p_code)
    if cutoff_period:
        count_stmt = count_stmt.where(LedgerT0BaseRecord.cutoff_period == cutoff_period)
        stmt = stmt.where(LedgerT0BaseRecord.cutoff_period == cutoff_period)

    total = db.execute(count_stmt).scalar() or 0

    stmt = stmt.order_by(
        LedgerT0BaseRecord.cutoff_period.desc(),
        LedgerT0BaseRecord.t0_base_id.desc(),
    ).offset(offset).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return total, [T0BaseOut.model_validate(r) for r in rows]
