"""
Router for claim record (正式资金台账) endpoints.
Covers: query (4.1), create formal claim (4.2).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.ledger_claim import (
    CreateClaimRequest,
    LedgerClaimQuery,
)
from app.services.ledger_claim_service import (
    create_formal_claim,
    query_ledger_claims,
)

router = APIRouter(prefix="/api/v1/claim-record", tags=["正式资金台账"])


@router.post("/query", response_model=ApiResponse)
def query_claims(
    query: LedgerClaimQuery,
    db: Session = Depends(get_db),
):
    """4.1 正式资金台账查询接口."""
    offset = (query.page_num - 1) * query.page_size
    page = query_ledger_claims(
        db,
        cust_p_code=query.cust_p_code,
        acct_name=query.acct_name,
        deposit_period=query.deposit_period,
        status_cd=query.status_cd,
        is_t0_init=query.is_t0_init,
        available_balance_min=query.available_balance_min,
        available_balance_max=query.available_balance_max,
        offset=offset,
        limit=query.page_size,
    )
    return ApiResponse(code="0", message="成功", data=page.model_dump())


@router.post("/create-from-claim", response_model=ApiResponse)
def create_from_claim(
    request: CreateClaimRequest,
    db: Session = Depends(get_db),
):
    """4.2 正式认领生成台账接口."""
    result = create_formal_claim(db, request)
    db.commit()
    return ApiResponse(code="0", message="成功", data=result.model_dump())
