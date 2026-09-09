"""
Router for T0 base record (T0基准存量欠费表) endpoints.
Covers: import (11.1), query (11.2).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.t0 import T0BaseImportRequest, T0BaseQuery
from app.services.t0_service import import_t0_base, query_t0_base

router = APIRouter(prefix="/api/v1/t0-base", tags=["T0基准存量欠费表"])


@router.post("/import", response_model=ApiResponse)
def t0_base_import(
    request: T0BaseImportRequest,
    db: Session = Depends(get_db),
):
    """11.1 T0基准数据导入接口."""
    result = import_t0_base(db, request)
    db.commit()
    return ApiResponse(code="0", message="成功", data=result.model_dump())


@router.post("/query", response_model=ApiResponse)
def t0_base_query(
    query: T0BaseQuery,
    db: Session = Depends(get_db),
):
    """11.2 T0基准数据查询接口."""
    offset = (query.page_num - 1) * query.page_size
    total, rows = query_t0_base(
        db,
        cust_p_code=query.cust_p_code,
        cutoff_period=query.cutoff_period,
        offset=offset,
        limit=query.page_size,
    )
    from app.schemas.common import PageResponse

    page = PageResponse(total=total, list=rows)
    return ApiResponse(code="0", message="成功", data=page.model_dump())
