"""
Service for revoke claim (回撤认领) operations.
Covers: revoke claim execution (8.1), revoke query (8.2).
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import ReverseError
from app.models.ledger_claim import LedgerClaimRecord, LedgerTempFundRecord
from app.models.ledger_item import LedgerItemRecord
from app.models.ledger_payoff import LedgerPayoffRecord
from app.schemas.writeoff import (
    PayoffOut,
    RevokeClaimRequest,
    RevokePayoffDetail,
    RevokeResult,
)
from app.utils import current_staff_id
from app.schemas.common import PageResponse

logger = logging.getLogger(__name__)


# ── 8.1 Revoke Claim Execution ────────────────────────────────────────────────


def revoke_claim(db: Session, request: RevokeClaimRequest) -> RevokeResult:
    """Revoke a formal claim identified by payment_id.

    For each associated write-off record:
    1. Void original payoff (1300)
    2. Insert red-letter reversal (1200)
    3. Restore arrears and fund
    4. Void the fund record (1100)
    5. Restore temp fund if claim_id is not None.
    """
    # Locate formal fund ledger by payment_id
    fund = db.execute(
        select(LedgerClaimRecord).where(
            LedgerClaimRecord.payment_id == request.payment_id,
            LedgerClaimRecord.status_cd == "1000",
        )
    ).scalar_one_or_none()

    if fund is None:
        raise ReverseError("REV_001", "正式认领记录不存在")

    staff_id = current_staff_id()
    now = datetime.now()
    total_reverse = Decimal("0")
    details: list[RevokePayoffDetail] = []

    # Query all active write-off records for this fund
    payoffs = db.execute(
        select(LedgerPayoffRecord).where(
            LedgerPayoffRecord.ledger_claim_id == fund.ledger_claim_id,
            LedgerPayoffRecord.status_cd == "1000",
        )
    ).scalars().all()

    for payoff in payoffs:
        amt = payoff.cancel_amount

        # Void original
        payoff.status_cd = "1300"
        payoff.update_date = now

        # Insert red-letter
        reverse_payoff = LedgerPayoffRecord(
            cancel_amount=-amt,
            ledger_claim_id=payoff.ledger_claim_id,
            ledger_item_id=payoff.ledger_item_id,
            acct_cd=payoff.acct_cd,
            cust_p_code=payoff.cust_p_code,
            status_cd="1200",
            write_off_date=now,
            batch_no=payoff.batch_no,
            remark=request.reason,
            create_staff=staff_id,
            update_staff=staff_id,
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
                arrears.arrears_amount += amt
                arrears.cancel_amount -= amt
                arrears.update_date = now

        # Restore fund
        fund.used_amount -= amt
        fund.available_balance = fund.deposit_amount - fund.used_amount
        fund.update_date = now

        total_reverse += amt
        details.append(
            RevokePayoffDetail(
                payoff_id=payoff.payoff_id,
                reverse_payoff_id=reverse_payoff.payoff_id,
                restore_arrears_amount=amt,
                restore_fund_balance=amt,
            )
        )

    # Verify used_amount == 0
    if fund.used_amount != 0:
        db.rollback()
        raise ReverseError("REV_004", "返销金额不平衡")

    # Void the fund record
    fund.status_cd = "1100"
    fund.update_date = now

    # Restore temp fund if claim_id is not None
    if fund.claim_id is not None:
        temp_fund = db.execute(
            select(LedgerTempFundRecord).where(
                LedgerTempFundRecord.claim_id == fund.claim_id,
                LedgerTempFundRecord.finance_id == fund.finance_id,
            )
        ).scalar_one_or_none()
        if temp_fund:
            temp_fund.deposit_amount += fund.deposit_amount
            temp_fund.update_date = now

    db.flush()

    return RevokeResult(
        reverse_amount=total_reverse,
        payoff_count=len(details),
        restored_fund_amount=fund.deposit_amount,
        details=details,
    )


# ── 8.2 Revoke / Reverse Query ────────────────────────────────────────────────


def query_reverse_records(
    db: Session,
    cust_p_code: str | None = None,
    acct_name: str | None = None,
    status: str | None = None,
    write_off_date_start: str | None = None,
    write_off_date_end: str | None = None,
    offset: int = 0,
    limit: int = 20,
) -> PageResponse[PayoffOut]:
    """Query payoff records with status 1200 (返销) or 1300 (作废)."""
    stmt = select(LedgerPayoffRecord).where(
        LedgerPayoffRecord.status_cd.in_(["1200", "1300"])
    )
    count_stmt = select(func.count()).select_from(LedgerPayoffRecord).where(
        LedgerPayoffRecord.status_cd.in_(["1200", "1300"])
    )

    if cust_p_code:
        stmt = stmt.where(LedgerPayoffRecord.cust_p_code == cust_p_code)
        count_stmt = count_stmt.where(LedgerPayoffRecord.cust_p_code == cust_p_code)
    if acct_name:
        stmt = stmt.where(LedgerPayoffRecord.acct_cd.like(f"%{acct_name}%"))
        count_stmt = count_stmt.where(LedgerPayoffRecord.acct_cd.like(f"%{acct_name}%"))
    if status:
        stmt = stmt.where(LedgerPayoffRecord.status_cd == status)
        count_stmt = count_stmt.where(LedgerPayoffRecord.status_cd == status)
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
