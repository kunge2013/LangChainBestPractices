"""
Router for temp fund record (临时资金台账) endpoints.
Covers: query (6.1).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.ledger_claim import TempFundQuery
from app.services.temp_claim_service import query_temp_funds

router = APIRouter(prefix="/api/v1/temp-fund-record", tags=["临时资金台账"])


@router.post("/query", response_model=ApiResponse)
def query_temp_fund(
    query: TempFundQuery,
    db: Session = Depends(get_db),
):
    """6.1 临时资金台账查询接口."""
    offset = (query.page_num - 1) * query.page_size
    page = query_temp_funds(
        db,
        cust_p_code=query.cust_p_code,
        acct_name=query.acct_name,
        deposit_period=query.deposit_period,
        offset=offset,
        limit=query.page_size,
    )
    return ApiResponse(code="0", message="成功", data=page.model_dump())
