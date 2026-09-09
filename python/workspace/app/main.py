"""
Main FastAPI application for 权责销账 (Accrual Write-Off) system.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.exceptions import LedgerError
from app.schemas.common import ApiResponse, PageResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="权责销账系统",
    description="权责销账功能 API",
    version="1.0.0",
    lifespan=lifespan,
)


# ── Exception handler ─────────────────────────────────────────────────────────


@app.exception_handler(LedgerError)
async def ledger_error_handler(request, exc: LedgerError):
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=400,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None,
            "timestamp": int(datetime.now().timestamp() * 1000),
        },
    )


# ── Import routers ────────────────────────────────────────────────────────────

from app.routers import (
    acct_pay_diff,
    claim_record,
    ledger_item,
    payoff_record,
    report,
    reverse,
    temp_claim,
    temp_fund_record,
    t0_base,
    t0_source,
    write_off,
)

app.include_router(t0_source.router)
app.include_router(ledger_item.router)
app.include_router(claim_record.router)
app.include_router(temp_claim.router)
app.include_router(temp_fund_record.router)
app.include_router(write_off.router)
app.include_router(reverse.router)
app.include_router(report.router)
app.include_router(payoff_record.router)
app.include_router(t0_base.router)
app.include_router(acct_pay_diff.router)


@app.get("/health")
def health():
    return {"status": "ok"}
