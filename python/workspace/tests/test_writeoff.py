"""
Tests for write-off service (sections 7.1 - 7.3).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from app.exceptions import WriteOffError
from app.models.finance import Finance
from app.models.ledger_claim import LedgerClaimRecord
from app.models.ledger_item import LedgerItemRecord
from app.models.ledger_payoff import LedgerPayoffRecord
from app.models.ledger_claim import TmpClaimRecord
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


class TestPreCheck:
    def test_precheck_all_clear(self, db_session):
        """No unclaimed receipts, has arrears and funds."""
        db_session.add(LedgerItemRecord(
            cust_p_code="P001",
            bill_ym="202606",
            rmb_all=Decimal("10000"),
            arrears_amount=Decimal("5000"),
            cancel_amount=Decimal("0"),
            acct_cd="ACC001",
            is_t0_init="1",
        ))
        db_session.add(LedgerClaimRecord(
            ledger_claim_id=1,
            cust_p_code="P001",
            acct_cd="ACC001",
            deposit_ym="202606",
            deposit_amount=Decimal("10000"),
            used_amount=Decimal("0"),
            available_balance=Decimal("10000"),
            status_cd="1000",
        ))
        db_session.flush()

        result = pre_check(db_session, PreCheckRequest(write_off_month="202608"))
        assert result.can_write_off is True
        assert result.unclaimed_count == 0
        assert result.total_arrears_amount == Decimal("5000")
        assert result.total_fund_amount == Decimal("10000")

    def test_precheck_with_unclaimed(self, db_session):
        """Has unclaimed finance records - cannot write off."""
        db_session.add(Finance(
            finance_id=2001,
            payment_cust_name="客户A",
            payment_date=datetime(2026, 7, 15),
            payment_money=Decimal("100000"),
            deposit_amount=Decimal("0"),
            status_cd="1000",
        ))
        db_session.flush()

        result = pre_check(db_session, PreCheckRequest(write_off_month="202608"))
        assert result.can_write_off is False
        assert result.unclaimed_count == 1


class TestExecuteWriteOff:
    def _setup_data(self, db_session):
        """Set up arrears and fund for P001+ACC001."""
        db_session.add(LedgerItemRecord(
            ledger_item_id=1,
            cust_p_code="P001",
            acct_cd="ACC001",
            bill_ym="202606",
            rmb_all=Decimal("10000"),
            arrears_amount=Decimal("10000"),
            cancel_amount=Decimal("0"),
            is_t0_init="1",
        ))
        db_session.add(LedgerClaimRecord(
            ledger_claim_id=1,
            cust_p_code="P001",
            acct_cd="ACC001",
            deposit_ym="202606",
            deposit_amount=Decimal("8000"),
            used_amount=Decimal("0"),
            available_balance=Decimal("8000"),
            status_cd="1000",
        ))
        db_session.flush()

    def test_write_off_success(self, db_session):
        self._setup_data(db_session)
        result = execute_write_off(db_session, WriteOffRequest(
            write_off_month="202608",
        ))
        assert result.write_off_count == 1
        assert result.total_write_off_amount == Decimal("8000")

        # Verify arrears updated
        arrears = db_session.query(LedgerItemRecord).get(1)
        assert arrears.arrears_amount == Decimal("2000")
        assert arrears.cancel_amount == Decimal("8000")

        # Verify fund updated
        fund = db_session.query(LedgerClaimRecord).get(1)
        assert fund.used_amount == Decimal("8000")
        assert fund.available_balance == Decimal("0")
        assert fund.status_cd == "1100"

        # Verify payoff record
        payoffs = db_session.query(LedgerPayoffRecord).all()
        assert len(payoffs) == 1
        assert payoffs[0].cancel_amount == Decimal("8000")
        assert payoffs[0].status_cd == "1000"

    def test_write_off_dry_run(self, db_session):
        self._setup_data(db_session)
        result = execute_write_off(db_session, WriteOffRequest(
            write_off_month="202608",
            is_dry_run=True,
        ))
        assert result.write_off_count == 1
        assert result.total_write_off_amount == Decimal("8000")

        # No changes in dry run
        arrears = db_session.query(LedgerItemRecord).get(1)
        assert arrears.arrears_amount == Decimal("10000")

        payoffs = db_session.query(LedgerPayoffRecord).all()
        assert len(payoffs) == 0

    def test_write_off_unclaimed_raises(self, db_session):
        db_session.add(Finance(
            finance_id=2001,
            payment_cust_name="客户A",
            payment_date=datetime(2026, 7, 15),
            payment_money=Decimal("100000"),
            deposit_amount=Decimal("0"),
            status_cd="1000",
        ))
        db_session.flush()

        with pytest.raises(WriteOffError):
            execute_write_off(db_session, WriteOffRequest(write_off_month="202608"))

    def test_write_off_multiple_periods(self, db_session):
        """Test that arrears are matched oldest bill_ym first."""
        db_session.add(LedgerItemRecord(
            ledger_item_id=1,
            cust_p_code="P001",
            acct_cd="ACC001",
            bill_ym="202605",
            rmb_all=Decimal("5000"),
            arrears_amount=Decimal("5000"),
            cancel_amount=Decimal("0"),
            is_t0_init="1",
        ))
        db_session.add(LedgerItemRecord(
            ledger_item_id=2,
            cust_p_code="P001",
            acct_cd="ACC001",
            bill_ym="202606",
            rmb_all=Decimal("5000"),
            arrears_amount=Decimal("5000"),
            cancel_amount=Decimal("0"),
            is_t0_init="1",
        ))
        db_session.add(LedgerClaimRecord(
            ledger_claim_id=1,
            cust_p_code="P001",
            acct_cd="ACC001",
            deposit_ym="202606",
            deposit_amount=Decimal("7000"),
            used_amount=Decimal("0"),
            available_balance=Decimal("7000"),
            status_cd="1000",
        ))
        db_session.flush()

        result = execute_write_off(db_session, WriteOffRequest(
            write_off_month="202608",
        ))
        assert result.write_off_count == 2
        # 5000 for first period + 2000 for second
        assert result.total_write_off_amount == Decimal("7000")

        # First arrears fully cleared
        arr1 = db_session.query(LedgerItemRecord).get(1)
        assert arr1.arrears_amount == Decimal("0")

        # Second arrears partially cleared
        arr2 = db_session.query(LedgerItemRecord).get(2)
        assert arr2.arrears_amount == Decimal("3000")

    def test_write_off_no_matching_arrears(self, db_session):
        """Fund exists but no arrears for the same p_code+acct_cd."""
        db_session.add(LedgerClaimRecord(
            ledger_claim_id=1,
            cust_p_code="P001",
            acct_cd="ACC001",
            deposit_ym="202606",
            deposit_amount=Decimal("8000"),
            available_balance=Decimal("8000"),
            status_cd="1000",
        ))
        db_session.add(LedgerItemRecord(
            cust_p_code="P002",  # different P-code
            acct_cd="ACC001",
            bill_ym="202606",
            rmb_all=Decimal("10000"),
            arrears_amount=Decimal("10000"),
            is_t0_init="1",
        ))
        db_session.flush()

        result = execute_write_off(db_session, WriteOffRequest(
            write_off_month="202608",
        ))
        assert result.write_off_count == 0


class TestReverseWriteOff:
    def _setup_write_off(self, db_session):
        db_session.add(LedgerItemRecord(
            ledger_item_id=1,
            cust_p_code="P001",
            acct_cd="ACC001",
            bill_ym="202606",
            rmb_all=Decimal("10000"),
            arrears_amount=Decimal("2000"),  # already partially written off
            cancel_amount=Decimal("8000"),
            is_t0_init="1",
        ))
        db_session.add(LedgerClaimRecord(
            ledger_claim_id=1,
            cust_p_code="P001",
            acct_cd="ACC001",
            deposit_ym="202606",
            deposit_amount=Decimal("8000"),
            used_amount=Decimal("8000"),
            available_balance=Decimal("0"),
            status_cd="1100",
        ))
        db_session.add(LedgerPayoffRecord(
            payoff_id=1,
            cancel_amount=Decimal("8000"),
            ledger_claim_id=1,
            ledger_item_id=1,
            acct_cd="ACC001",
            cust_p_code="P001",
            status_cd="1000",
            write_off_date=datetime(2026, 8, 3),
            batch_no="202608",
        ))
        db_session.flush()

    def test_reverse_success(self, db_session):
        self._setup_write_off(db_session)
        result = reverse_write_off(db_session, ReverseRequest(
            write_off_id=1,
            reason="test reversal",
        ))

        assert result.write_off_id == 1
        assert result.reverse_write_off_id is not None
        assert result.restored_arrears_amount == Decimal("8000")

        # Original payoff voided
        orig = db_session.query(LedgerPayoffRecord).get(1)
        assert orig.status_cd == "1300"

        # Red-letter record created
        red = db_session.query(LedgerPayoffRecord).filter_by(
            status_cd="1200"
        ).first()
        assert red is not None
        assert red.cancel_amount == Decimal("-8000")

        # Arrears restored
        arrears = db_session.query(LedgerItemRecord).get(1)
        assert arrears.arrears_amount == Decimal("10000")
        assert arrears.cancel_amount == Decimal("0")

        # Fund restored
        fund = db_session.query(LedgerClaimRecord).get(1)
        assert fund.used_amount == Decimal("0")
        assert fund.available_balance == Decimal("8000")
        assert fund.status_cd == "1000"

    def test_reverse_not_found_raises(self, db_session):
        with pytest.raises(WriteOffError):
            reverse_write_off(db_session, ReverseRequest(write_off_id=9999))

    def test_reverse_already_reversed_raises(self, db_session):
        self._setup_write_off(db_session)
        # Reverse first
        reverse_write_off(db_session, ReverseRequest(write_off_id=1, reason="first"))

        # Try again - should fail
        with pytest.raises(WriteOffError):
            reverse_write_off(db_session, ReverseRequest(write_off_id=1, reason="second"))
