"""
Service for write-off (权责销账) operations.
Covers: execute write-off (7.1), pre-check (7.2), reverse (7.3).
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import WriteOffError
from app.models.finance import Finance
from app.models.ledger_claim import LedgerClaimRecord
from app.models.ledger_item import LedgerItemRecord
from app.models.ledger_payoff import LedgerPayoffRecord
from app.models.ledger_claim import TmpClaimRecord
from app.schemas.writeoff import (
    PreCheckRequest,
    PreCheckResult,
    ReverseRequest,
    ReverseResult,
    WriteOffDetail,
    WriteOffRequest,
    WriteOffResult,
)
from app.utils import current_staff_id, now_yyyymm, prev_month_yyyymm, validate_yyyymm

logger = logging.getLogger(__name__)


def _month_filter(db: Session, column, yyyymm: str):
    """Build a dialect-aware WHERE clause for matching YYYYMM on a datetime column."""
    if db.bind.dialect.name == "sqlite":
        return func.strftime("%Y%m", column) == yyyymm
    return func.date_format(column, "%Y%m") == yyyymm


# ── 7.1 Execute Write-Off ─────────────────────────────────────────────────────


def execute_write_off(db: Session, request: WriteOffRequest) -> WriteOffResult:
    """Execute write-off: match funds to arrears by P-code, deposit_ym ASC,
    bill_ym ASC.
    """
    # Step 1: check unclaimed receipts
    prev_month = prev_month_yyyymm()
    unclaimed = db.execute(
        select(func.count()).select_from(Finance).where(
            _month_filter(db, Finance.payment_date, prev_month),
            Finance.status_cd == "1000",
            ~Finance.finance_id.in_(
                select(TmpClaimRecord.finance_id).where(
                    TmpClaimRecord.status_cd == "1000"
                )
            ),
        )
    ).scalar() or 0

    if unclaimed > 0:
        raise WriteOffError("WO_001", "存在未认领回款，无法销账")

    staff_id = current_staff_id()
    now = datetime.now()
    batch_no = request.batch_no or now_yyyymm()
    total_write_off = Decimal("0")
    write_off_count = 0
    fund_used_count = 0
    arrears_cleared_count = 0
    details: list[WriteOffDetail] = []

    # Query available funds (status=1000, available>0), order by deposit_ym ASC
    fund_stmt = (
        select(LedgerClaimRecord)
        .where(
            LedgerClaimRecord.status_cd == "1000",
            LedgerClaimRecord.available_balance > 0,
        )
        .order_by(LedgerClaimRecord.deposit_ym.asc())
    )
    if request.cust_p_code:
        fund_stmt = fund_stmt.where(LedgerClaimRecord.cust_p_code == request.cust_p_code)

    funds = db.execute(fund_stmt).scalars().all()

    # Group funds by cust_p_code + acct_cd
    fund_groups: dict[tuple, list[LedgerClaimRecord]] = {}
    for fund in funds:
        key = (fund.cust_p_code, fund.acct_cd)
        fund_groups.setdefault(key, []).append(fund)

    for (cust_p_code, acct_cd), group_funds in fund_groups.items():
        # Query arrears for this group (arrears_amount > 0, order by bill_ym ASC)
        arrears_stmt = (
            select(LedgerItemRecord)
            .where(
                LedgerItemRecord.cust_p_code == cust_p_code,
                LedgerItemRecord.acct_cd == acct_cd,
                LedgerItemRecord.arrears_amount > 0,
            )
            .order_by(LedgerItemRecord.bill_ym.asc())
        )
        arrears_list = db.execute(arrears_stmt).scalars().all()

        if not arrears_list:
            continue

        for fund in group_funds:
            fund_remaining = fund.available_balance

            for arrears in arrears_list:
                if fund_remaining <= 0:
                    break
                if arrears.arrears_amount <= 0:
                    continue

                amt = min(fund_remaining, arrears.arrears_amount)

                if request.is_dry_run:
                    total_write_off += amt
                    write_off_count += 1
                    details.append(
                        WriteOffDetail(
                            cust_p_code=cust_p_code,
                            acct_code=acct_cd,
                            write_off_amount=amt,
                            fund_ledger_id=fund.ledger_claim_id,
                            arrears_ledger_id=arrears.ledger_item_id,
                            write_off_date=now,
                        )
                    )
                    fund_remaining -= amt
                    continue

                # Update arrears
                arrears.arrears_amount = arrears.arrears_amount - amt
                arrears.cancel_amount = arrears.cancel_amount + amt
                arrears.update_date = now

                # Update fund
                fund.used_amount = fund.used_amount + amt
                fund.available_balance = fund.deposit_amount - fund.used_amount
                if fund.available_balance == 0:
                    fund.status_cd = "1100"
                    fund_used_count += 1
                fund.update_date = now

                # Insert payoff record
                payoff = LedgerPayoffRecord(
                    cancel_amount=amt,
                    ledger_claim_id=fund.ledger_claim_id,
                    ledger_item_id=arrears.ledger_item_id,
                    acct_cd=acct_cd,
                    cust_p_code=cust_p_code,
                    status_cd="1000",
                    write_off_date=now,
                    batch_no=batch_no,
                    create_staff=staff_id,
                    update_staff=staff_id,
                )
                db.add(payoff)
                db.flush()

                total_write_off += amt
                write_off_count += 1
                details.append(
                    WriteOffDetail(
                        write_off_id=payoff.payoff_id,
                        cust_p_code=cust_p_code,
                        acct_code=acct_cd,
                        write_off_amount=amt,
                        fund_ledger_id=fund.ledger_claim_id,
                        arrears_ledger_id=arrears.ledger_item_id,
                        write_off_date=now,
                    )
                )
                fund_remaining -= amt

                if arrears.arrears_amount == 0:
                    arrears_cleared_count += 1

            if fund.available_balance == 0 and not request.is_dry_run:
                fund_used_count += 1

    db.flush()

    return WriteOffResult(
        batch_no=batch_no,
        total_write_off_amount=total_write_off,
        write_off_count=write_off_count,
        fund_used_count=fund_used_count,
        arrears_cleared_count=arrears_cleared_count,
        details=details,
    )


# ── 7.2 Pre-Check ──────────────────────────────────────────────────────────────


def pre_check(db: Session, request: PreCheckRequest) -> PreCheckResult:
    """Check whether write-off can proceed."""
    prev_month = prev_month_yyyymm()

    # Unclaimed count
    unclaimed_count = db.execute(
        select(func.count()).select_from(Finance).where(
            _month_filter(db, Finance.payment_date, prev_month),
            Finance.status_cd == "1000",
            ~Finance.finance_id.in_(
                select(TmpClaimRecord.finance_id).where(
                    TmpClaimRecord.status_cd == "1000"
                )
            ),
        )
    ).scalar() or 0

    unclaimed_amount = db.execute(
        select(func.coalesce(func.sum(Finance.payment_money), 0)).where(
            _month_filter(db, Finance.payment_date, prev_month),
            Finance.status_cd == "1000",
            ~Finance.finance_id.in_(
                select(TmpClaimRecord.finance_id).where(
                    TmpClaimRecord.status_cd == "1000"
                )
            ),
        )
    ).scalar() or Decimal("0")

    # Total arrears
    total_arrears = db.execute(
        select(func.coalesce(func.sum(LedgerItemRecord.arrears_amount), 0)).where(
            LedgerItemRecord.arrears_amount > 0
        )
    ).scalar() or Decimal("0")

    # Total fund
    total_fund = db.execute(
        select(
            func.coalesce(func.sum(LedgerClaimRecord.available_balance), 0)
        ).where(
            LedgerClaimRecord.status_cd == "1000",
            LedgerClaimRecord.available_balance > 0,
        )
    ).scalar() or Decimal("0")

    can_write_off = unclaimed_count == 0
    estimated = min(total_arrears, total_fund)

    return PreCheckResult(
        can_write_off=can_write_off,
        unclaimed_count=unclaimed_count,
        unclaimed_amount=unclaimed_amount,
        total_arrears_amount=total_arrears,
        total_fund_amount=total_fund,
        estimated_write_off=estimated,
    )


# ── 7.3 Reverse Write-Off ─────────────────────────────────────────────────────


def reverse_write_off(db: Session, request: ReverseRequest) -> ReverseResult:
    """Reverse a single write-off record (红字冲销)."""
    payoff = db.execute(
        select(LedgerPayoffRecord).where(
            LedgerPayoffRecord.payoff_id == request.write_off_id
        )
    ).scalar_one_or_none()

    if payoff is None:
        raise WriteOffError("WO_006", "销账记录不存在或状态异常")

    if payoff.status_cd != "1000":
        raise WriteOffError("WO_007", "返销时原记录已返销或作废")

    amt = payoff.cancel_amount

    # Void original record (1000 -> 1300)
    payoff.status_cd = "1300"
    payoff.update_date = datetime.now()

    # Insert red-letter reversal record (1200, negative amount)
    reverse_payoff = LedgerPayoffRecord(
        cancel_amount=-amt,
        ledger_claim_id=payoff.ledger_claim_id,
        ledger_item_id=payoff.ledger_item_id,
        acct_cd=payoff.acct_cd,
        cust_p_code=payoff.cust_p_code,
        status_cd="1200",
        write_off_date=datetime.now(),
        batch_no=payoff.batch_no,
        remark=request.reason,
        create_staff=current_staff_id(),
        update_staff=current_staff_id(),
    )
    db.add(reverse_payoff)
    db.flush()

    # Restore arrears
    if payoff.ledger_item_id:
        arrears = db.execute(
            select(LedgerItemRecord).where(
                LedgerItemRecord.ledger_item_id == payoff.ledger_item_id
            )
        ).scalar_one_or_none()
        if arrears:
            arrears.arrears_amount = arrears.arrears_amount + amt
            arrears.cancel_amount = arrears.cancel_amount - amt
            arrears.update_date = datetime.now()

    # Restore fund
    if payoff.ledger_claim_id:
        fund = db.execute(
            select(LedgerClaimRecord).where(
                LedgerClaimRecord.ledger_claim_id == payoff.ledger_claim_id
            )
        ).scalar_one_or_none()
        if fund:
            fund.used_amount = fund.used_amount - amt
            fund.available_balance = fund.deposit_amount - fund.used_amount
            if fund.status_cd == "1100" and fund.available_balance > 0:
                fund.status_cd = "1000"
            fund.update_date = datetime.now()

    db.flush()

    return ReverseResult(
        write_off_id=payoff.payoff_id,
        reverse_write_off_id=reverse_payoff.payoff_id,
        restored_arrears_amount=amt,
        restored_fund_balance=amt,
    )
