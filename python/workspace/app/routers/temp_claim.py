"""
Router for temp claim (公有资金池临时认领) endpoints.
Covers: finance query (5.1), execute temp claim (5.2).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.ledger_claim import FinanceQuery, TempClaimRequest
from app.services.temp_claim_service import (
    execute_temp_claim,
    query_unclaimed_finance,
)

router = APIRouter(prefix="/api/v1/tmp-claim", tags=["公有资金池临时认领"])


@router.post("/query-finance", response_model=ApiResponse)
def query_finance(
    query: FinanceQuery,
    db: Session = Depends(get_db),
):
    """5.1 上月公有资金池到账登记查询接口."""
    offset = (query.page_num - 1) * query.page_size
    page = query_unclaimed_finance(
        db,
        payment_month=query.payment_month,
        cust_name=query.cust_name,
        offset=offset,
        limit=query.page_size,
    )
    return ApiResponse(code="0", message="成功", data=page.model_dump())


@router.post("/claim", response_model=ApiResponse)
def temp_claim(
    request: TempClaimRequest,
    db: Session = Depends(get_db),
):
    """5.2 执行临时认领接口."""
    result = execute_temp_claim(db, request)
    db.commit()
    return ApiResponse(code="0", message="成功", data=result.model_dump())
