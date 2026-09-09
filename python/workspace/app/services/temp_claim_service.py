"""
Service for temp claim (公有资金池临时认领) operations.
Covers: finance query (5.1), temp claim execution (5.2).
Also covers temp fund query (6.1).
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.exceptions import TempClaimError
from app.models.finance import Finance
from app.models.ledger_claim import LedgerTempFundRecord, TmpClaimRecord
from app.schemas.common import PageResponse
from app.schemas.ledger_claim import (
    ClaimResultDetail,
    FinanceOut,
    TempClaimRequest,
    TempClaimResult,
    TempFundOut,
    TempFundQuery,
)
from app.utils import current_staff_id, now_yyyymm, prev_month_yyyymm

logger = logging.getLogger(__name__)


# ── 5.1 Finance Query (unclaimed) ──────────────────────────────────────────────


def query_unclaimed_finance(
    db: Session,
    payment_month: str | None = None,
    cust_name: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> PageResponse[FinanceOut]:
    """Query finance records that have not been temp-claimed."""
    if not payment_month:
        payment_month = prev_month_yyyymm()

    # Build the date filter based on dialect
    if db.bind.dialect.name == "sqlite":
        date_filter = func.strftime("%Y%m", Finance.payment_date) == payment_month
    else:
        date_filter = func.date_format(Finance.payment_date, "%Y%m") == payment_month

    stmt = select(Finance).where(
        date_filter,
        Finance.status_cd == "1000",
        (Finance.payment_money - Finance.deposit_amount) > 0,
        ~Finance.finance_id.in_(
            select(TmpClaimRecord.finance_id).where(
                TmpClaimRecord.status_cd == "1000"
            )
        ),
    )
    if cust_name:
        stmt = stmt.where(Finance.payment_cust_name.like(f"%{cust_name}%"))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.execute(count_stmt).scalar() or 0

    rows = db.execute(
        stmt.order_by(Finance.payment_date.desc()).offset(offset).limit(limit)
    ).scalars().all()

    out_list = [
        FinanceOut(
            finance_id=str(r.finance_id),
            payment_cust_name=r.payment_cust_name,
            bank_nbr=r.bank_nbr,
            payment_date=r.payment_date,
            payment_money=r.payment_money,
            deposit_amount=r.deposit_amount,
        )
        for r in rows
    ]
    return PageResponse(total=total, list=out_list)


# ── 5.2 Execute Temp Claim ────────────────────────────────────────────────────


def execute_temp_claim(
    db: Session,
    request: TempClaimRequest,
    acct_info_lookup: dict[int, dict] | None = None,
) -> TempClaimResult:
    """Execute temp claim for a finance record across multiple accounts.

    Args:
        db: Active session (MySQL).
        request: Temp claim request with finance_id and claim_list.
        acct_info_lookup: Optional dict acct_id -> {party_nbr, acct_cd, acct_name, cust_name}
                         (simulates PostgreSQL account->customer->party query).
    """
    # Step 1: parameter validation
    if not request.claim_list:
        raise TempClaimError("TMP_003", "临时认领金额无效")

    sum_amount = sum((item.claim_amount for item in request.claim_list), Decimal("0"))
    if sum_amount <= 0 or sum_amount != request.total_claim_amount:
        raise TempClaimError("TMP_003", "临时认领金额无效")

    for item in request.claim_list:
        if item.claim_amount <= 0:
            raise TempClaimError("TMP_003", "临时认领金额无效")

    # Step 2: query and validate finance record
    finance = db.execute(
        select(Finance).where(Finance.finance_id == request.finance_id)
    ).scalar_one_or_none()

    if finance is None:
        raise TempClaimError("TMP_001", "到账记录不存在")

    if finance.status_cd not in ("1000", "1200"):
        raise TempClaimError("TMP_002", "到账无效!")

    if finance.payment_money < request.total_claim_amount:
        raise TempClaimError("TMP_003", "临时认领金额无效")

    # Step 3: row lock check - already claimed?
    existing = db.execute(
        select(TmpClaimRecord).where(
            TmpClaimRecord.finance_id == request.finance_id,
            TmpClaimRecord.status_cd == "1000",
        )
    ).scalar_one_or_none()

    if existing:
        raise TempClaimError("TMP_002", "该到账已被认领")

    # Step 4: batch query account P-code info (simulated PG)
    acct_ids = [item.claim_acct_id for item in request.claim_list]
    acct_info_map: dict[int, dict] = {}
    if acct_info_lookup:
        acct_info_map = {
            aid: acct_info_lookup[aid] for aid in acct_ids if aid in acct_info_lookup
        }

    if len(acct_info_map) != len(acct_ids):
        raise TempClaimError("TMP_005", "账户信息无效")

    # Step 5: insert temp claim records and temp fund records
    staff_id = current_staff_id()
    now = datetime.now()
    deposit_ym = now_yyyymm()
    details: list[ClaimResultDetail] = []

    for item in request.claim_list:
        info = acct_info_map[item.claim_acct_id]

        # 5.1 INSERT TMP_CLAIM_RECORD
        claim_record = TmpClaimRecord(
            finance_id=finance.finance_id,
            payment_cust_name=finance.payment_cust_name,
            bank_nbr=finance.bank_nbr,
            payment_date=finance.payment_date,
            payment_money=finance.payment_money,
            claim_date=now,
            claim_acct_cd=info.get("acct_cd"),
            claim_acct_id=item.claim_acct_id,
            claim_staff=str(staff_id),
            claim_amount=item.claim_amount,
            claim_p_code=info.get("party_nbr"),
            status_cd="1000",
            remark=request.remark,
            create_staff=staff_id,
            update_staff=staff_id,
        )
        db.add(claim_record)
        db.flush()

        # 5.2 INSERT LEDGER_TEMP_FUND_RECORD
        temp_fund = LedgerTempFundRecord(
            finance_id=finance.finance_id,
            claim_id=claim_record.claim_id,
            cust_p_code=info.get("party_nbr"),
            cust_name=info.get("cust_name"),
            acct_name=info.get("acct_name"),
            acct_cd=info.get("acct_cd"),
            acct_id=item.claim_acct_id,
            deposit_ym=deposit_ym,
            deposit_amount=item.claim_amount,
            acct_subject_code="合同负债",
            company_code="A000",
            is_t0_init="0",
            create_staff=staff_id,
            update_staff=staff_id,
        )
        db.add(temp_fund)
        db.flush()

        details.append(
            ClaimResultDetail(
                temp_claim_id=claim_record.claim_id,
                temp_ledger_id=temp_fund.temp_ledger_claim_id,
                claim_acct_id=item.claim_acct_id,
                claim_acct_cd=info.get("acct_cd"),
                claim_p_code=info.get("party_nbr"),
                claim_amount=item.claim_amount,
            )
        )

    # Step 6: update finance status
    finance.status_cd = "1200"
    finance.update_date = now
    db.flush()

    return TempClaimResult(
        finance_id=finance.finance_id,
        claim_count=len(details),
        total_claim_amount=request.total_claim_amount,
        details=details,
    )


# ── 6.1 Temp Fund Query ───────────────────────────────────────────────────────


def query_temp_funds(
    db: Session,
    cust_p_code: str | None = None,
    acct_name: str | None = None,
    deposit_period: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> PageResponse[TempFundOut]:
    """Paginated query of temp fund ledger records."""
    stmt = select(LedgerTempFundRecord)
    count_stmt = select(func.count()).select_from(LedgerTempFundRecord)

    if cust_p_code:
        stmt = stmt.where(LedgerTempFundRecord.cust_p_code == cust_p_code)
        count_stmt = count_stmt.where(LedgerTempFundRecord.cust_p_code == cust_p_code)
    if acct_name:
        stmt = stmt.where(LedgerTempFundRecord.acct_name.like(f"%{acct_name}%"))
        count_stmt = count_stmt.where(
            LedgerTempFundRecord.acct_name.like(f"%{acct_name}%")
        )
    if deposit_period:
        stmt = stmt.where(LedgerTempFundRecord.deposit_ym == deposit_period)
        count_stmt = count_stmt.where(LedgerTempFundRecord.deposit_ym == deposit_period)

    total = db.execute(count_stmt).scalar() or 0
    rows = db.execute(
        stmt.order_by(LedgerTempFundRecord.create_date.desc())
        .offset(offset)
        .limit(limit)
    ).scalars().all()

    out_list = [
        TempFundOut(
            temp_fund_ledger_id=r.temp_ledger_claim_id,
            finance_id=str(r.finance_id) if r.finance_id is not None else None,
            temp_claim_id=r.claim_id,
            cust_p_code=r.cust_p_code,
            cust_name=r.cust_name,
            acct_name=r.acct_name,
            acct_code=r.acct_cd,
            deposit_period=r.deposit_ym,
            deposit_amount=r.deposit_amount,
            acct_subject_code=r.acct_subject_code,
            create_time=r.create_date,
        )
        for r in rows
    ]
    return PageResponse(total=total, list=out_list)
