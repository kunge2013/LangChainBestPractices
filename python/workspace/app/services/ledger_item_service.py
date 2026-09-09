"""
Service for ledger item (权责欠费台账) operations.
Covers: T0 arrears import (3.1), EDA import (3.2), query (3.3),
T0 acct refresh (3.4), EDA acct refresh (3.5).
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.exceptions import LedgerError
from app.models.ledger_item import LedgerItemRecord
from app.models.t0 import LedgerT0SourceRecord
from app.schemas.common import PageResponse
from app.schemas.ledger_item import (
    EdaImportResult,
    EdaItemDTO,
    EdaRefreshResult,
    LedgerItemOut,
    T0ArrearsImportResult,
    T0RefreshResult,
)
from app.utils import current_staff_id, now_yyyymm

logger = logging.getLogger(__name__)

QUERY_LIMIT = 5000
BATCH_SIZE = 1000
REFRESH_BATCH = 100

PROD_TYPE_SUBJECT_MAP = {
    "基础业务": "P041S002",
    "IDC业务": "P041S003",
    "集成业务": "P041S004",
    "组网专线业务": "P041S005",
    "其他": "P041S006",
    "其他（应收）": "P041S007",
}


# ── 3.1 T0 Arrears Import ──────────────────────────────────────────────────────


def import_t0_arrears(db: Session, amount_type: str = "0") -> T0ArrearsImportResult:
    """Import T0 arrears (AMOUNT_TYPE='0') from source into ledger_item_record."""
    if amount_type != "0":
        raise LedgerError("ARR_001", "amountType必须为'0'")

    # Count source
    total = db.execute(
        select(func.count()).select_from(LedgerT0SourceRecord).where(
            LedgerT0SourceRecord.amount_type == "0"
        )
    ).scalar() or 0

    if total <= 0:
        raise LedgerError("ARR_002", "无有效的T0欠费数据可导入")

    batch_no = now_yyyymm()
    staff_id = current_staff_id()
    now = datetime.now()
    success_count = 0
    last_max_id = 0

    while True:
        rows = db.execute(
            select(LedgerT0SourceRecord)
            .where(
                LedgerT0SourceRecord.amount_type == "0",
                LedgerT0SourceRecord.t0_item_id > last_max_id,
            )
            .order_by(LedgerT0SourceRecord.t0_item_id.asc())
            .limit(QUERY_LIMIT)
        ).scalars().all()

        if not rows:
            break

        batch: list[LedgerItemRecord] = []
        for src in rows:
            entity = LedgerItemRecord(
                cust_p_code=src.cust_p_code,
                cust_name=None,
                acct_name=None,
                acct_cd=None,
                acct_id=None,
                bill_ym=src.bill_ym,
                batch_no=batch_no,
                item_id=None,
                item_type="0",
                rmb_all=src.amount or Decimal("0"),
                arrears_amount=src.amount or Decimal("0"),
                cancel_amount=Decimal("0"),
                acct_subject_code=src.acct_subject_code,
                cust_m_code=src.cust_m_code,
                cust_master_name=None,
                sap_no=src.sap_no,
                sap_item=src.sap_item,
                company_code=src.company_code,
                fiscal_year=src.fiscal_year,
                voucher_date=src.voucher_date,
                eda_batch_no=None,
                is_t0_init="1",
                create_staff=staff_id,
                update_staff=staff_id,
            )
            batch.append(entity)
            success_count += 1

            if len(batch) >= BATCH_SIZE:
                db.add_all(batch)
                db.flush()
                batch.clear()

        if batch:
            db.add_all(batch)
            db.flush()
            batch.clear()

        last_max_id = rows[-1].t0_item_id

    return T0ArrearsImportResult(success_count=success_count, source_count=total)


# ── 3.2 EDA Import ─────────────────────────────────────────────────────────────


def import_eda_data(
    db: Session,
    bill_ym: str,
    eda_items_by_acct: dict[int, list[EdaItemDTO]] | None = None,
) -> EdaImportResult:
    """Import EDA data from external source.

    In production this would query PostgreSQL.  For testing, callers can
    pass ``eda_items_by_acct`` directly to simulate PG results.

    Args:
        db: MySQL session.
        bill_ym: Bill period YYYYMM.
        eda_items_by_acct: Optional dict of acct_id -> list of EdaItemDTO.

    Returns:
        EdaImportResult with counts.
    """
    if not bill_ym:
        raise LedgerError("ARR_009", "EDA集成账期不能为空")

    batch_no = bill_ym
    staff_id = current_staff_id()
    now = datetime.now()
    delete_count = 0
    insert_count = 0
    total_amount = Decimal("0")
    failed_acct = 0

    if eda_items_by_acct is None:
        eda_items_by_acct = {}

    if not eda_items_by_acct:
        raise LedgerError("ARR_010", "该账期无有效的EDA数据可导入")

    for acct_id, items in eda_items_by_acct.items():
        try:
            # Delete existing EDA data for this account+batch
            deleted = db.execute(
                LedgerItemRecord.__table__.delete().where(
                    LedgerItemRecord.batch_no == batch_no,
                    LedgerItemRecord.acct_id == acct_id,
                    LedgerItemRecord.is_t0_init == "0",
                )
            )
            delete_count += deleted.rowcount or 0

            # Insert new data in batches
            batch: list[LedgerItemRecord] = []
            for dto in items:
                entity = LedgerItemRecord(
                    cust_p_code=None,
                    cust_name=None,
                    acct_name=None,
                    acct_cd=None,
                    acct_id=dto.acct_id,
                    bill_ym=dto.bill_ym,
                    batch_no=batch_no,
                    item_id=dto.item_id,
                    item_type=dto.item_type,
                    rmb_all=dto.rmb_all,
                    arrears_amount=dto.arrears_amount,
                    cancel_amount=Decimal("0"),
                    acct_subject_code=dto.acct_subject_code,
                    cust_m_code=None,
                    cust_master_name=None,
                    eda_batch_no=None,
                    is_t0_init="0",
                    create_staff=staff_id,
                    update_staff=staff_id,
                )
                batch.append(entity)
                total_amount += dto.rmb_all
                insert_count += 1

                if len(batch) >= BATCH_SIZE:
                    db.add_all(batch)
                    db.flush()
                    batch.clear()

            if batch:
                db.add_all(batch)
                db.flush()
        except Exception as exc:
            logger.warning("EDA import failed for acct_id=%s: %s", acct_id, exc)
            failed_acct += 1

    return EdaImportResult(
        batch_no=batch_no,
        delete_count=delete_count,
        insert_count=insert_count,
        total_amount=total_amount,
        failed_acct_count=failed_acct,
    )


# ── 3.3 Query ──────────────────────────────────────────────────────────────────


def query_ledger_items(
    db: Session,
    cust_p_code: str | None = None,
    acct_name: str | None = None,
    arrears_period: str | None = None,
    is_t0_init: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> PageResponse[LedgerItemOut]:
    """Paginated query of ledger item records."""
    stmt = select(LedgerItemRecord)
    count_stmt = select(func.count()).select_from(LedgerItemRecord)

    if cust_p_code:
        stmt = stmt.where(LedgerItemRecord.cust_p_code == cust_p_code)
        count_stmt = count_stmt.where(LedgerItemRecord.cust_p_code == cust_p_code)
    if acct_name:
        stmt = stmt.where(LedgerItemRecord.acct_name.like(f"%{acct_name}%"))
        count_stmt = count_stmt.where(LedgerItemRecord.acct_name.like(f"%{acct_name}%"))
    if arrears_period:
        stmt = stmt.where(LedgerItemRecord.bill_ym == arrears_period)
        count_stmt = count_stmt.where(LedgerItemRecord.bill_ym == arrears_period)
    if is_t0_init:
        mapped = "1" if is_t0_init in ("1", "是") else ("0" if is_t0_init in ("0", "否") else is_t0_init)
        stmt = stmt.where(LedgerItemRecord.is_t0_init == mapped)
        count_stmt = count_stmt.where(LedgerItemRecord.is_t0_init == mapped)

    total = db.execute(count_stmt).scalar() or 0
    rows = db.execute(
        stmt.order_by(LedgerItemRecord.create_date.desc()).offset(offset).limit(limit)
    ).scalars().all()

    out_list = [
        LedgerItemOut(
            arrears_ledger_id=r.ledger_item_id,
            cust_p_code=r.cust_p_code,
            cust_name=r.cust_name,
            acct_name=r.acct_name,
            acct_code=r.acct_cd,
            arrears_period=r.bill_ym,
            receivable_amount=r.rmb_all,
            arrears_amount=r.arrears_amount,
            write_off_amount=r.cancel_amount,
            acct_subject_code=r.acct_subject_code,
            is_t0_init=r.is_t0_init,
            create_time=r.create_date,
        )
        for r in rows
    ]
    return PageResponse(total=total, list=out_list)


# ── 3.4 T0 Account Attribute Refresh ───────────────────────────────────────────


def refresh_t0_acct_attr(
    db: Session,
    cust_p_code_list: list[str] | None = None,
    acct_info_lookup: dict[str, dict] | None = None,
) -> T0RefreshResult:
    """Refresh account attributes for T0-init ledger items.

    Args:
        db: MySQL session.
        cust_p_code_list: Optional P-code filter.
        acct_info_lookup: Optional dict p_code -> {party_nbr, cust_name, acct_name, acct_cd, acct_id}
                         (simulates PostgreSQL party->customer->account query).

    Returns:
        T0RefreshResult with counts and failures.
    """
    # Query distinct pending P-codes
    stmt = (
        select(LedgerItemRecord.cust_p_code)
        .where(
            LedgerItemRecord.is_t0_init == "1",
            (LedgerItemRecord.cust_name.is_(None)) | (LedgerItemRecord.acct_name.is_(None)),
            LedgerItemRecord.cust_p_code.is_not(None),
        )
        .distinct()
    )
    if cust_p_code_list:
        stmt = stmt.where(LedgerItemRecord.cust_p_code.in_(cust_p_code_list))

    p_codes = [r for r in db.execute(stmt).scalars().all() if r]
    total_p = len(p_codes)

    if total_p == 0:
        return T0RefreshResult()

    refreshed_p = 0
    refreshed_count = 0
    failed_list: list[dict] = []
    matched_p = 0

    for i in range(0, total_p, REFRESH_BATCH):
        batch = p_codes[i : i + REFRESH_BATCH]

        # Look up account info (simulated PG query)
        if acct_info_lookup:
            batch_info = {
                p: acct_info_lookup[p] for p in batch if p in acct_info_lookup
            }
        else:
            batch_info = {}

        if not batch_info:
            continue

        matched_p += len(batch_info)

        try:
            # Batch update using CASE WHEN
            for p_code, info in batch_info.items():
                updated = db.execute(
                    LedgerItemRecord.__table__.update()
                    .where(
                        LedgerItemRecord.is_t0_init == "1",
                        (LedgerItemRecord.cust_name.is_(None))
                        | (LedgerItemRecord.acct_name.is_(None)),
                        LedgerItemRecord.cust_p_code == p_code,
                    )
                    .values(
                        cust_name=info.get("cust_name"),
                        acct_name=info.get("acct_name"),
                        acct_cd=info.get("acct_cd"),
                        acct_id=info.get("acct_id"),
                        update_date=datetime.now(),
                        update_staff=settings.system_staff_id,
                    )
                )
                refreshed_count += updated.rowcount or 0
            db.flush()
            refreshed_p += len(batch_info)
        except Exception as exc:
            logger.warning("T0 refresh failed for batch: %s", exc)
            for p in batch:
                failed_list.append({"pCode": p, "errorMsg": f"更新失败:{exc}"})

    unrefreshed = total_p - matched_p
    return T0RefreshResult(
        refreshed_p_code_count=refreshed_p,
        refreshed_count=refreshed_count,
        unrefreshed_p_code_count=unrefreshed,
        failed_p_code_count=len(failed_list),
        fail_p_code_list=failed_list,
    )


# ── 3.5 EDA Account Attribute Refresh ───────────────────────────────────────────


def refresh_eda_acct_attr(
    db: Session,
    bill_ym: str,
    batch_no: str,
    acct_info_lookup: dict[int, dict] | None = None,
) -> EdaRefreshResult:
    """Refresh account/customer/P-code attributes for EDA-imported ledger items.

    Args:
        db: MySQL session.
        bill_ym: Bill period.
        batch_no: Batch number.
        acct_info_lookup: Optional dict acct_id -> {cust_name, party_nbr, acct_name, acct_cd}
                         (simulates PG account->customer->party query).
    """
    stmt = (
        select(LedgerItemRecord.acct_id)
        .where(
            LedgerItemRecord.is_t0_init == "0",
            LedgerItemRecord.bill_ym == bill_ym,
            LedgerItemRecord.batch_no == batch_no,
            (LedgerItemRecord.cust_name.is_(None))
            | (LedgerItemRecord.acct_name.is_(None))
            | (LedgerItemRecord.cust_p_code.is_(None)),
            LedgerItemRecord.acct_id.is_not(None),
        )
        .distinct()
    )
    acct_ids = [r for r in db.execute(stmt).scalars().all() if r]
    total_a = len(acct_ids)

    if total_a == 0:
        return EdaRefreshResult()

    refreshed_a = 0
    refreshed_count = 0
    failed_list: list[dict] = []
    matched_a = 0

    for i in range(0, total_a, REFRESH_BATCH):
        batch = acct_ids[i : i + REFRESH_BATCH]

        if acct_info_lookup:
            batch_info = {
                a: acct_info_lookup[a] for a in batch if a in acct_info_lookup
            }
        else:
            batch_info = {}

        if not batch_info:
            continue

        matched_a += len(batch_info)

        try:
            for acct_id, info in batch_info.items():
                updated = db.execute(
                    LedgerItemRecord.__table__.update()
                    .where(
                        LedgerItemRecord.is_t0_init == "0",
                        LedgerItemRecord.bill_ym == bill_ym,
                        LedgerItemRecord.batch_no == batch_no,
                        (LedgerItemRecord.cust_name.is_(None))
                        | (LedgerItemRecord.acct_name.is_(None))
                        | (LedgerItemRecord.cust_p_code.is_(None)),
                        LedgerItemRecord.acct_id == acct_id,
                    )
                    .values(
                        cust_name=info.get("cust_name"),
                        cust_p_code=info.get("party_nbr"),
                        acct_name=info.get("acct_name"),
                        acct_cd=info.get("acct_cd"),
                        update_date=datetime.now(),
                        update_staff=settings.system_staff_id,
                    )
                )
                refreshed_count += updated.rowcount or 0
            db.flush()
            refreshed_a += len(batch_info)
        except Exception as exc:
            logger.warning("EDA refresh failed for batch: %s", exc)
            for a in batch:
                failed_list.append({"acctId": a, "errorMsg": f"更新失败:{exc}"})

    unrefreshed = total_a - matched_a
    return EdaRefreshResult(
        refreshed_acct_id_count=refreshed_a,
        refreshed_count=refreshed_count,
        unrefreshed_acct_id_count=unrefreshed,
        failed_acct_id_count=len(failed_list),
        fail_acct_id_list=failed_list,
    )
