"""
Router for payoff record (权责销账查询) endpoints.
Covers: query (10.1), export (10.2).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.writeoff import PayoffQuery
from app.services.payoff_query_service import (
    export_payoff_records,
    query_payoff_records,
)

router = APIRouter(prefix="/api/v1/payoff-record", tags=["权责销账查询"])


@router.post("/query", response_model=ApiResponse)
def payoff_query(
    query: PayoffQuery,
    db: Session = Depends(get_db),
):
    """10.1 销账记录查询接口."""
    offset = (query.page_num - 1) * query.page_size
    page = query_payoff_records(
        db,
        cust_p_code=query.cust_p_code,
        acct_name=query.acct_name,
        write_off_date_start=query.write_off_date_start,
        write_off_date_end=query.write_off_date_end,
        status=query.status,
        offset=offset,
        limit=query.page_size,
    )
    return ApiResponse(code="0", message="成功", data=page.model_dump())


@router.post("/export", response_model=ApiResponse)
def payoff_export(
    query: PayoffQuery,
    db: Session = Depends(get_db),
):
    """10.2 销账记录导出接口."""
    result = export_payoff_records(
        db,
        cust_p_code=query.cust_p_code,
        acct_name=query.acct_name,
        write_off_date_start=query.write_off_date_start,
        write_off_date_end=query.write_off_date_end,
        status=query.status,
    )
    return ApiResponse(code="0", message="成功", data=result.model_dump())
