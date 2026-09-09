"""
Tests for report service (sections 9.1 - 9.3).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from app.exceptions import ReportError
from app.models.ledger_claim import LedgerClaimRecord, LedgerTempFundRecord
from app.models.ledger_item import LedgerItemRecord
from app.models.ledger_payoff import LedgerReportRecord
from app.schemas.writeoff import ReportGenerateRequest
from app.services.report_service import (
    export_report,
    generate_report,
    query_report,
)


class TestGenerateReport:
    def _setup_data(self, db_session):
        db_session.add(LedgerItemRecord(
            cust_p_code="P001",
            cust_name="客户A",
            acct_name="账户A",
            acct_cd="ACC001",
            bill_ym="202606",
            acct_subject_code="P041S002",
            rmb_all=Decimal("10000"),
            arrears_amount=Decimal("5000"),
            cancel_amount=Decimal("5000"),
            is_t0_init="1",
        ))
        db_session.add(LedgerClaimRecord(
            cust_p_code="P001",
            acct_cd="ACC001",
            acct_subject_code="P041S002",
            deposit_ym="202606",
            deposit_amount=Decimal("20000"),
            used_amount=Decimal("5000"),
            available_balance=Decimal("15000"),
            status_cd="1000",
        ))
        db_session.add(LedgerTempFundRecord(
            cust_p_code="P001",
            acct_cd="ACC001",
            deposit_ym="202606",
            deposit_amount=Decimal("5000"),
        ))
        db_session.flush()

    def test_generate_success(self, db_session):
        self._setup_data(db_session)
        result = generate_report(db_session, ReportGenerateRequest(
            report_month="202608",
        ))

        assert result.report_month == "202608"
        assert result.total_records == 1
        assert result.total_arrears_amount == Decimal("5000")
        assert result.total_write_off_amount == Decimal("5000")
        assert result.total_deposit_amount == Decimal("25000")  # 20000 + 5000

        reports = db_session.query(LedgerReportRecord).all()
        assert len(reports) == 1
        assert reports[0].cust_p_code == "P001"
        assert reports[0].deposit_amount == Decimal("25000")

    def test_generate_empty_month_raises(self, db_session):
        with pytest.raises(ReportError):
            generate_report(db_session, ReportGenerateRequest(report_month=""))

    def test_generate_idempotent(self, db_session):
        self._setup_data(db_session)
        generate_report(db_session, ReportGenerateRequest(report_month="202608"))
        generate_report(db_session, ReportGenerateRequest(report_month="202608"))

        reports = db_session.query(LedgerReportRecord).filter_by(
            report_month="202608"
        ).all()
        assert len(reports) == 1  # old data deleted, new inserted


class TestQueryReport:
    def _setup_reports(self, db_session):
        for i in range(5):
            db_session.add(LedgerReportRecord(
                cust_p_code=f"P{i:03d}",
                cust_name=f"客户{i}",
                acct_name=f"账户{i}",
                acct_cd=f"ACC{i:03d}",
                bill_ym="202606",
                rmb_all=Decimal("10000"),
                arrears_amount=Decimal("5000"),
                cancel_amount=Decimal("5000"),
                deposit_amount=Decimal("20000"),
                available_balance=Decimal("15000"),
                acct_subject_code="P041S002",
                report_month="202608",
            ))
        db_session.flush()

    def test_query_by_month(self, db_session):
        self._setup_reports(db_session)
        page = query_report(db_session, report_month="202608")
        assert page.total == 5

    def test_query_by_p_code(self, db_session):
        self._setup_reports(db_session)
        page = query_report(db_session, report_month="202608", cust_p_code="P000")
        assert page.total == 1

    def test_query_pagination(self, db_session):
        self._setup_reports(db_session)
        page = query_report(db_session, report_month="202608", offset=0, limit=2)
        assert page.total == 5
        assert len(page.list) == 2


class TestExportReport:
    def test_export_returns_file_info(self, db_session):
        db_session.add(LedgerReportRecord(
            cust_p_code="P001",
            cust_name="客户A",
            acct_cd="ACC001",
            bill_ym="202606",
            rmb_all=Decimal("10000"),
            arrears_amount=Decimal("5000"),
            cancel_amount=Decimal("5000"),
            deposit_amount=Decimal("20000"),
            available_balance=Decimal("15000"),
            report_month="202608",
        ))
        db_session.flush()

        result = export_report(db_session, report_month="202608")
        assert "权责台账报表" in result.file_name
        assert result.file_url.startswith("/download/")
        assert result.record_count == 1
