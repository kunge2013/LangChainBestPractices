"""
Router for report (权责台账报表) endpoints.
Covers: generate (9.1), query (9.2), export (9.3).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.writeoff import (
    ReportGenerateRequest,
    ReportQuery,
)
from app.services.report_service import (
    export_report,
    generate_report,
    query_report,
)

router = APIRouter(prefix="/api/v1/report", tags=["权责台账报表"])


@router.post("/generate", response_model=ApiResponse)
def report_generate(
    request: ReportGenerateRequest,
    db: Session = Depends(get_db),
):
    """9.1 报表生成接口."""
    result = generate_report(db, request)
    db.commit()
    return ApiResponse(code="0", message="成功", data=result.model_dump())


@router.post("/query", response_model=ApiResponse)
def report_query(
    query: ReportQuery,
    db: Session = Depends(get_db),
):
    """9.2 报表查询接口."""
    offset = (query.page_num - 1) * query.page_size
    page = query_report(
        db,
        cust_p_code=query.cust_p_code,
        acct_name=query.acct_name,
        ledger_period=query.ledger_period,
        report_month=query.report_month,
        offset=offset,
        limit=query.page_size,
    )
    return ApiResponse(code="0", message="成功", data=page.model_dump())


@router.post("/export", response_model=ApiResponse)
def report_export(
    query: ReportQuery,
    db: Session = Depends(get_db),
):
    """9.3 报表导出接口."""
    result = export_report(
        db,
        cust_p_code=query.cust_p_code,
        acct_name=query.acct_name,
        ledger_period=query.ledger_period,
        report_month=query.report_month,
    )
    return ApiResponse(code="0", message="成功", data=result.model_dump())
