"""
Tests for payoff query service (section 10.x) and diff service (section 12.x).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from app.exceptions import DiffError
from app.models.ledger_claim import LedgerClaimRecord, LedgerTempFundRecord
from app.models.ledger_item import LedgerItemRecord
from app.models.ledger_payoff import (
    LedgerAcctPayDiffRecord,
    LedgerPayoffRecord,
    LedgerReportRecord,
)
from app.models.t0 import LedgerT0BaseRecord
from app.schemas.writeoff import DiffGenerateRequest
from app.services.diff_service import (
    export_diff,
    generate_diff,
    query_diff,
)
from app.services.payoff_query_service import (
    export_payoff_records,
    query_payoff_records,
)


class TestPayoffQuery:
    def _setup_payoffs(self, db_session):
        db_session.add(LedgerPayoffRecord(
            payoff_id=1,
            cancel_amount=Decimal("10000"),
            ledger_claim_id=1,
            ledger_item_id=1,
            acct_cd="ACC001",
            cust_p_code="P001",
            status_cd="1000",
            write_off_date=datetime(2026, 8, 3),
            batch_no="WO202607",
        ))
        db_session.add(LedgerPayoffRecord(
            payoff_id=2,
            cancel_amount=Decimal("5000"),
            ledger_claim_id=2,
            ledger_item_id=2,
            acct_cd="ACC002",
            cust_p_code="P002",
            status_cd="1200",
            write_off_date=datetime(2026, 8, 5),
            batch_no="WO202607",
        ))
        db_session.flush()

    def test_query_all(self, db_session):
        self._setup_payoffs(db_session)
        page = query_payoff_records(db_session)
        assert page.total == 2

    def test_query_by_status(self, db_session):
        self._setup_payoffs(db_session)
        page = query_payoff_records(db_session, status="1000")
        assert page.total == 1

    def test_query_by_p_code(self, db_session):
        self._setup_payoffs(db_session)
        page = query_payoff_records(db_session, cust_p_code="P001")
        assert page.total == 1

    def test_query_pagination(self, db_session):
        self._setup_payoffs(db_session)
        page = query_payoff_records(db_session, offset=0, limit=1)
        assert page.total == 2
        assert len(page.list) == 1


class TestPayoffExport:
    def test_export_returns_file_info(self, db_session):
        db_session.add(LedgerPayoffRecord(
            payoff_id=1,
            cancel_amount=Decimal("10000"),
            ledger_claim_id=1,
            ledger_item_id=1,
            acct_cd="ACC001",
            cust_p_code="P001",
            status_cd="1000",
            write_off_date=datetime(2026, 8, 3),
            batch_no="WO202607",
        ))
        db_session.flush()

        result = export_payoff_records(db_session)
        assert "权责销账查询" in result.file_name
        assert result.record_count == 1

    def test_export_with_negative_amount(self, db_session):
        db_session.add(LedgerPayoffRecord(
            payoff_id=1,
            cancel_amount=Decimal("-5000"),
            ledger_claim_id=1,
            acct_cd="ACC001",
            cust_p_code="P001",
            status_cd="1200",
            write_off_date=datetime(2026, 8, 5),
            batch_no="WO202607",
        ))
        db_session.flush()

        result = export_payoff_records(db_session)
        assert result.record_count == 1


class TestDiffGenerate:
    def _setup_data(self, db_session):
        # Ledger item
        db_session.add(LedgerItemRecord(
            cust_p_code="P001",
            acct_name="账户A",
            acct_cd="ACC001",
            bill_ym="202607",
            acct_subject_code="P041S002",
            rmb_all=Decimal("100000"),
            arrears_amount=Decimal("70000"),
            cancel_amount=Decimal("30000"),
            is_t0_init="1",
        ))
        # Formal fund
        db_session.add(LedgerClaimRecord(
            cust_p_code="P001",
            acct_cd="ACC001",
            deposit_ym="202607",
            deposit_amount=Decimal("80000"),
            used_amount=Decimal("30000"),
            available_balance=Decimal("50000"),
            status_cd="1000",
        ))
        # Temp fund
        db_session.add(LedgerTempFundRecord(
            cust_p_code="P001",
            acct_cd="ACC001",
            deposit_ym="202607",
            deposit_amount=Decimal("20000"),
        ))
        # Payoff
        db_session.add(LedgerPayoffRecord(
            cancel_amount=Decimal("30000"),
            ledger_claim_id=1,
            acct_cd="ACC001",
            cust_p_code="P001",
            status_cd="1000",
            write_off_date=datetime(2026, 8, 3),
            batch_no="WO202607",
        ))
        # T0 base
        db_session.add(LedgerT0BaseRecord(
            cust_p_code="P001",
            cutoff_period="202606",
            t0_arrears_acct=Decimal("10000"),
            t0_arrears_fin=Decimal("8000"),
            t0_arrears_diff=Decimal("2000"),
        ))
        # Report record (required pre-condition)
        db_session.add(LedgerReportRecord(
            cust_p_code="P001",
            acct_cd="ACC001",
            bill_ym="202607",
            rmb_all=Decimal("100000"),
            arrears_amount=Decimal("70000"),
            cancel_amount=Decimal("30000"),
            report_month="202607",
        ))
        db_session.flush()

    def test_generate_success(self, db_session):
        self._setup_data(db_session)
        result = generate_diff(db_session, DiffGenerateRequest(period="202607"))

        assert result.period == "202607"
        assert result.total_records == 1

        diffs = db_session.query(LedgerAcctPayDiffRecord).all()
        assert len(diffs) == 1
        assert diffs[0].cust_p_code == "P001"
        assert diffs[0].receivable_accr == Decimal("100000")
        assert diffs[0].receipt_amount == Decimal("100000")  # 80000+20000
        assert diffs[0].write_off_accr == Decimal("30000")
        assert diffs[0].begin_arrears_diff == Decimal("2000")

    def test_generate_no_report_raises(self, db_session):
        with pytest.raises(DiffError):
            generate_diff(db_session, DiffGenerateRequest(period="202607"))

    def test_generate_empty_period_raises(self, db_session):
        with pytest.raises(DiffError):
            generate_diff(db_session, DiffGenerateRequest(period=""))

    def test_generate_idempotent(self, db_session):
        self._setup_data(db_session)
        generate_diff(db_session, DiffGenerateRequest(period="202607"))
        generate_diff(db_session, DiffGenerateRequest(period="202607"))

        diffs = db_session.query(LedgerAcctPayDiffRecord).filter_by(
            period="202607"
        ).all()
        assert len(diffs) == 1


class TestDiffQuery:
    def _setup_diffs(self, db_session):
        for i in range(5):
            db_session.add(LedgerAcctPayDiffRecord(
                acct_name=f"账户{i}",
                acct_cd=f"ACC{i:03d}",
                cust_p_code=f"P{i:03d}",
                period="202607",
                receivable_pay=Decimal("100000"),
                receivable_accr=Decimal("100000"),
                receipt_amount=Decimal("80000"),
                write_off_pay=Decimal("30000"),
                write_off_accr=Decimal("30000"),
                balance_pay=Decimal("50000"),
                balance_accr=Decimal("50000"),
                current_diff=Decimal("0"),
                begin_arrears_diff=Decimal("0"),
                end_arrears_diff=Decimal("0"),
            ))
        db_session.flush()

    def test_query_all(self, db_session):
        self._setup_diffs(db_session)
        page = query_diff(db_session)
        assert page.total == 5

    def test_query_by_period(self, db_session):
        self._setup_diffs(db_session)
        page = query_diff(db_session, period="202607")
        assert page.total == 5

    def test_query_by_acct_name(self, db_session):
        self._setup_diffs(db_session)
        page = query_diff(db_session, acct_name="账户0")
        assert page.total == 1

    def test_query_pagination(self, db_session):
        self._setup_diffs(db_session)
        page = query_diff(db_session, offset=0, limit=2)
        assert page.total == 5
        assert len(page.list) == 2


class TestDiffExport:
    def test_export_returns_file_info(self, db_session):
        db_session.add(LedgerAcctPayDiffRecord(
            acct_name="账户A",
            acct_cd="ACC001",
            cust_p_code="P001",
            period="202607",
            receivable_pay=Decimal("100000"),
            receivable_accr=Decimal("100000"),
            receipt_amount=Decimal("80000"),
            write_off_pay=Decimal("30000"),
            write_off_accr=Decimal("30000"),
            balance_pay=Decimal("50000"),
            balance_accr=Decimal("50000"),
            current_diff=Decimal("0"),
            begin_arrears_diff=Decimal("0"),
            end_arrears_diff=Decimal("0"),
        ))
        db_session.flush()

        result = export_diff(db_session)
        assert "收付权责欠费差异表" in result.file_name
        assert result.record_count == 1
