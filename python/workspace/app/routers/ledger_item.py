"""
Router for ledger item (权责欠费台账) endpoints.
Covers: T0 arrears import (3.1), EDA import (3.2), query (3.3),
T0 acct refresh (3.4), EDA acct refresh (3.5).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.ledger_item import (
    EdaImportResult,
    LedgerItemOut,
    LedgerItemQuery,
    T0ArrearsImportResult,
    T0RefreshResult,
    EdaRefreshResult,
)
from app.services.ledger_item_service import (
    import_t0_arrears,
    import_eda_data,
    query_ledger_items,
    refresh_t0_acct_attr,
    refresh_eda_acct_attr,
)

router = APIRouter(prefix="/api/v1/ledger-item", tags=["权责欠费台账"])


@router.post("/init-t0", response_model=ApiResponse)
def init_t0_arrears(
    amount_type: str = Query("0", description="固定值'0'，表示仅导入欠费数据"),
    db: Session = Depends(get_db),
):
    """3.1 T0欠费数据初始化导入接口."""
    result = import_t0_arrears(db, amount_type)
    db.commit()
    return ApiResponse(
        code="0",
        message="操作成功",
        data=result.model_dump(),
    )


@router.post("/import-bill", response_model=ApiResponse)
def import_bill(
    bill_ym: str = Query(..., description="账期，格式YYYYMM"),
    db: Session = Depends(get_db),
):
    """3.2 增量权责账单集成接口.

    In production, this would query PostgreSQL. For testing, it accepts
    no pre-loaded data and will raise if no external source is configured.
    """
    result = import_eda_data(db, bill_ym)
    db.commit()
    return ApiResponse(
        code="0",
        message="操作成功",
        data=result.model_dump(),
    )


@router.post("/query", response_model=ApiResponse)
def query_items(
    query: LedgerItemQuery,
    db: Session = Depends(get_db),
):
    """3.3 权责欠费台账查询接口."""
    page = query_ledger_items(
        db,
        cust_p_code=query.cust_p_code,
        acct_name=query.acct_name,
        arrears_period=query.arrears_period,
        is_t0_init=query.is_t0_init,
        offset=query.offset if hasattr(query, "offset") else (query.page_num - 1) * query.page_size,
        limit=query.page_size,
    )
    return ApiResponse(
        code="0",
        message="成功",
        data=page.model_dump(),
    )


@router.post("/refresh-t0-acct", response_model=ApiResponse)
def refresh_t0_acct(
    cust_p_codes: list[str] | None = None,
    db: Session = Depends(get_db),
):
    """3.4 T0台账账户属性刷新接口."""
    result = refresh_t0_acct_attr(db, cust_p_code_list=cust_p_codes)
    db.commit()
    return ApiResponse(
        code="0",
        message="成功",
        data=result.model_dump(),
    )


@router.post("/refresh-eda-acct", response_model=ApiResponse)
def refresh_eda_acct(
    bill_ym: str = Query(..., description="账期"),
    batch_no: str = Query(..., description="批次号"),
    db: Session = Depends(get_db),
):
    """3.5 增量权责账单客/账户以及P码属性刷新接口."""
    result = refresh_eda_acct_attr(db, bill_ym, batch_no)
    db.commit()
    return ApiResponse(
        code="0",
        message="成功",
        data=result.model_dump(),
    )
