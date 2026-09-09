"""
Service for ledger claim (正式资金台账) operations.
Covers: query (4.1), create formal claim (4.2).
"""
from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions import ClaimError
from app.models.finance import Finance, Payment
from app.models.ledger_claim import LedgerClaimRecord, LedgerTempFundRecord
from app.schemas.common import PageResponse
from app.schemas.ledger_claim import (
    CreateClaimRequest,
    CreateClaimResult,
    LedgerClaimOut,
)
from app.utils import current_staff_id, now_yyyymm

logger = logging.getLogger(__name__)


# ── 4.1 Query ──────────────────────────────────────────────────────────────────


def query_ledger_claims(
    db: Session,
    cust_p_code: str | None = None,
    acct_name: str | None = None,
    deposit_period: str | None = None,
    status_cd: str | None = None,
    is_t0_init: str | None = None,
    available_balance_min: Decimal | None = None,
    available_balance_max: Decimal | None = None,
    offset: int = 0,
    limit: int = 20,
) -> PageResponse[LedgerClaimOut]:
    """Paginated query of formal fund ledger records."""
    stmt = select(LedgerClaimRecord)
    count_stmt = select(func.count()).select_from(LedgerClaimRecord)

    if cust_p_code:
        stmt = stmt.where(LedgerClaimRecord.cust_p_code == cust_p_code)
        count_stmt = count_stmt.where(LedgerClaimRecord.cust_p_code == cust_p_code)
    if acct_name:
        stmt = stmt.where(LedgerClaimRecord.acct_name.like(f"%{acct_name}%"))
        count_stmt = count_stmt.where(
            LedgerClaimRecord.acct_name.like(f"%{acct_name}%")
        )
    if deposit_period:
        stmt = stmt.where(LedgerClaimRecord.deposit_ym == deposit_period)
        count_stmt = count_stmt.where(LedgerClaimRecord.deposit_ym == deposit_period)
    if status_cd:
        stmt = stmt.where(LedgerClaimRecord.status_cd == status_cd)
        count_stmt = count_stmt.where(LedgerClaimRecord.status_cd == status_cd)
    if is_t0_init:
        stmt = stmt.where(LedgerClaimRecord.is_t0_init == is_t0_init)
        count_stmt = count_stmt.where(LedgerClaimRecord.is_t0_init == is_t0_init)
    if available_balance_min is not None:
        stmt = stmt.where(LedgerClaimRecord.available_balance >= available_balance_min)
        count_stmt = count_stmt.where(
            LedgerClaimRecord.available_balance >= available_balance_min
        )
    if available_balance_max is not None:
        stmt = stmt.where(LedgerClaimRecord.available_balance <= available_balance_max)
        count_stmt = count_stmt.where(
            LedgerClaimRecord.available_balance <= available_balance_max
        )

    total = db.execute(count_stmt).scalar() or 0
    rows = db.execute(
        stmt.order_by(LedgerClaimRecord.create_date.desc())
        .offset(offset)
        .limit(limit)
    ).scalars().all()

    out_list = [
        LedgerClaimOut(
            fund_ledger_id=r.ledger_claim_id,
            payment_id=r.payment_id,
            finance_id=str(r.finance_id) if r.finance_id is not None else None,
            temp_claim_id=r.claim_id,
            cust_p_code=r.cust_p_code,
            cust_name=r.cust_name,
            acct_name=r.acct_name,
            acct_code=r.acct_cd,
            deposit_period=r.deposit_ym,
            deposit_amount=r.deposit_amount,
            used_amount=r.used_amount,
            available_balance=r.available_balance,
            acct_subject_code=r.acct_subject_code,
            status_cd=r.status_cd,
            is_t0_init=r.is_t0_init,
            create_time=r.create_date,
        )
        for r in rows
    ]
    return PageResponse(total=total, list=out_list)


# ── 4.2 Create Formal Claim ────────────────────────────────────────────────────


def create_formal_claim(
    db: Session,
    request: CreateClaimRequest,
    m_code_info: dict[str, Any] | None = None,
) -> CreateClaimResult:
    """Create a formal fund ledger record from a payment.

    Scenario A: If temp claim records exist for the finance_id, split by
    temp claim amounts. Scenario B: No temp claim, use request deposit_amount.

    Args:
        db: Active session.
        request: Claim creation request.
        m_code_info: Optional dict with cust_m_code/cust_master_name (simulates
            external M-code API call).
    """
    staff_id = current_staff_id()
    now = datetime.now()

    # Check duplicate (payment_id + finance_id)
    existing = db.execute(
        select(LedgerClaimRecord).where(
            LedgerClaimRecord.payment_id == request.payment_id,
            LedgerClaimRecord.finance_id == request.finance_id,
        )
    ).scalar_one_or_none()
    if existing:
        raise ClaimError("FND_002", "重复认领（唯一索引冲突）")

    # Query temp fund records for this finance_id (scenario A)
    temp_funds = db.execute(
        select(LedgerTempFundRecord)
        .where(
            LedgerTempFundRecord.finance_id == request.finance_id,
            LedgerTempFundRecord.deposit_amount > 0,
        )
        .order_by(LedgerTempFundRecord.claim_id)
    ).scalars().all()

    cust_m_code = None
    cust_master_name = None
    if m_code_info:
        cust_m_code = m_code_info.get("cust_m_code")
        cust_master_name = m_code_info.get("cust_master_name")

    created_ids: list[int] = []
    last_available = Decimal("0")

    if temp_funds:
        # Scenario A: split by temp claim amounts
        for tf in temp_funds:
            claim_amount = tf.deposit_amount
            if claim_amount <= 0:
                continue
            record = LedgerClaimRecord(
                payment_id=request.payment_id,
                finance_id=request.finance_id,
                claim_id=tf.claim_id,
                cust_p_code=tf.cust_p_code,
                cust_name=tf.cust_name,
                acct_name=tf.acct_name,
                acct_cd=tf.acct_cd,
                deposit_ym=tf.deposit_ym or request.deposit_period,
                deposit_amount=claim_amount,
                used_amount=Decimal("0"),
                available_balance=claim_amount,
                acct_subject_code=tf.acct_subject_code or "合同负债",
                cust_m_code=cust_m_code,
                cust_master_name=cust_master_name,
                is_t0_init="0",
                status_cd="1000",
                create_staff=staff_id,
                update_staff=staff_id,
            )
            db.add(record)
            db.flush()
            created_ids.append(record.ledger_claim_id)
            last_available = record.available_balance

            # Reduce temp fund deposit_amount
            tf.deposit_amount = tf.deposit_amount - claim_amount
            tf.update_date = now
    else:
        # Scenario B: direct create
        record = LedgerClaimRecord(
            payment_id=request.payment_id,
            finance_id=request.finance_id,
            claim_id=None,
            cust_p_code=request.cust_p_code,
            cust_name=None,
            acct_name=None,
            acct_cd=None,
            deposit_ym=request.deposit_period,
            deposit_amount=request.deposit_amount,
            used_amount=Decimal("0"),
            available_balance=request.deposit_amount,
            acct_subject_code="合同负债",
            cust_m_code=cust_m_code,
            cust_master_name=cust_master_name,
            is_t0_init="0",
            status_cd="1000",
            create_staff=staff_id,
            update_staff=staff_id,
        )
        db.add(record)
        db.flush()
        created_ids.append(record.ledger_claim_id)
        last_available = record.available_balance

    db.flush()
    return CreateClaimResult(
        fund_ledger_id=created_ids[-1],
        available_balance=last_available,
    )
