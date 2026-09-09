"""
Router for write-off (权责销账处理) endpoints.
Covers: pre-check (7.2), execute (7.1), reverse (7.3).
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import ApiResponse
from app.schemas.writeoff import (
    PreCheckRequest,
    ReverseRequest,
    WriteOffRequest,
)
from app.services.writeoff_service import (
    execute_write_off,
    pre_check,
    reverse_write_off,
)

router = APIRouter(prefix="/api/v1/write-off", tags=["权责销账处理"])


@router.post("/pre-check", response_model=ApiResponse)
def write_off_pre_check(
    request: PreCheckRequest,
    db: Session = Depends(get_db),
):
    """7.2 销账前检查接口."""
    result = pre_check(db, request)
    return ApiResponse(code="0", message="成功", data=result.model_dump())


@router.post("/execute", response_model=ApiResponse)
def write_off_execute(
    request: WriteOffRequest,
    db: Session = Depends(get_db),
):
    """7.1 执行权责销账接口."""
    result = execute_write_off(db, request)
    db.commit()
    return ApiResponse(code="0", message="成功", data=result.model_dump())


@router.post("/reverse", response_model=ApiResponse)
def write_off_reverse(
    request: ReverseRequest,
    db: Session = Depends(get_db),
):
    """7.3 销账返销接口."""
    result = reverse_write_off(db, request)
    db.commit()
    return ApiResponse(code="0", message="成功", data=result.model_dump())
