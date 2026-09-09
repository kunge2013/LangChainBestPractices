"""
Router for reverse/revoke (回撤认领-返销) endpoints.
Covers: revoke execute (8.1), revoke query (8.2).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.writeoff import (
    PayoffQuery,
    RevokeClaimRequest,
)
from app.services.reverse_service import (
    query_reverse_records,
    revoke_claim,
)

router = APIRouter(prefix="/api/v1/reverse", tags=["回撤认领-返销"])


@router.post("/execute", response_model=ApiResponse)
def revoke_execute(
    request: RevokeClaimRequest,
    db: Session = Depends(get_db),
):
    """8.1 回撤认领执行接口."""
    result = revoke_claim(db, request)
    db.commit()
    return ApiResponse(code="0", message="成功", data=result.model_dump())


@router.post("/query", response_model=ApiResponse)
def revoke_query(
    query: PayoffQuery,
    db: Session = Depends(get_db),
):
    """8.2 回撤返销查询接口."""
    offset = (query.page_num - 1) * query.page_size
    page = query_reverse_records(
        db,
        cust_p_code=query.cust_p_code,
        acct_name=query.acct_name,
        status=query.status,
        write_off_date_start=query.write_off_date_start,
        write_off_date_end=query.write_off_date_end,
        offset=offset,
        limit=query.page_size,
    )
    return ApiResponse(code="0", message="成功", data=page.model_dump())
