"""
Router for acct-pay diff (收付权责欠费差异表) endpoints.
Covers: generate (12.1), query (12.2), export (12.3).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.writeoff import DiffGenerateRequest, DiffQuery
from app.services.diff_service import (
    export_diff,
    generate_diff,
    query_diff,
)

router = APIRouter(prefix="/api/v1/acct-pay-diff", tags=["收付权责欠费差异表"])


@router.post("/generate", response_model=ApiResponse)
def diff_generate(
    request: DiffGenerateRequest,
    db: Session = Depends(get_db),
):
    """12.1 差异数据生成接口."""
    result = generate_diff(db, request)
    db.commit()
    return ApiResponse(code="0", message="成功", data=result.model_dump())


@router.post("/query", response_model=ApiResponse)
def diff_query(
    query: DiffQuery,
    db: Session = Depends(get_db),
):
    """12.2 差异数据查询接口."""
    offset = (query.page_num - 1) * query.page_size
    page = query_diff(
        db,
        acct_name=query.acct_name,
        period=query.period,
        offset=offset,
        limit=query.page_size,
    )
    return ApiResponse(code="0", message="成功", data=page.model_dump())


@router.post("/export", response_model=ApiResponse)
def diff_export(
    query: DiffQuery,
    db: Session = Depends(get_db),
):
    """12.3 差异数据导出接口."""
    result = export_diff(
        db,
        acct_name=query.acct_name,
        period=query.period,
    )
    return ApiResponse(code="0", message="成功", data=result.model_dump())
