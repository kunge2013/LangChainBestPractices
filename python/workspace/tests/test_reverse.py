"""
Tests for revoke claim service (sections 8.1, 8.2).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from app.exceptions import ReverseError
from app.models.ledger_claim import LedgerClaimRecord, LedgerTempFundRecord
from app.models.ledger_item import LedgerItemRecord
from app.models.ledger_payoff import LedgerPayoffRecord
from app.schemas.writeoff import RevokeClaimRequest
from app.services.reverse_service import (
    query_reverse_records,
    revoke_claim,
)


class TestRevokeClaim:
    def _setup_claim_with_payoff(self, db_session, with_temp=False):
        db_session.add(LedgerItemRecord(
            ledger_item_id=1,
            cust_p_code="P001",
            acct_cd="ACC001",
            bill_ym="202606",
            rmb_all=Decimal("10000"),
            arrears_amount=Decimal("2000"),
            cancel_amount=Decimal("8000"),
            is_t0_init="1",
        ))
        db_session.add(LedgerClaimRecord(
            ledger_claim_id=1,
            payment_id=1001,
            finance_id="3001",
            claim_id=5001 if with_temp else None,
            cust_p_code="P001",
            acct_cd="ACC001",
            deposit_ym="202606",
            deposit_amount=Decimal("8000"),
            used_amount=Decimal("8000"),
            available_balance=Decimal("0"),
            status_cd="1000",
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
        if with_temp:
            db_session.add(LedgerTempFundRecord(
                temp_ledger_claim_id=1,
                finance_id=3001,
                claim_id=5001,
                cust_p_code="P001",
                deposit_ym="202606",
                deposit_amount=Decimal("0"),
            ))
        db_session.flush()

    def test_revoke_success(self, db_session):
        self._setup_claim_with_payoff(db_session)
        result = revoke_claim(db_session, RevokeClaimRequest(
            payment_id=1001,
            reason="test revoke",
        ))

        assert result.payoff_count == 1
        assert result.reverse_amount == Decimal("8000")

        # Fund voided
        fund = db_session.query(LedgerClaimRecord).get(1)
        assert fund.status_cd == "1100"
        assert fund.used_amount == Decimal("0")
        assert fund.available_balance == Decimal("8000")

        # Original payoff voided
        payoff = db_session.query(LedgerPayoffRecord).get(1)
        assert payoff.status_cd == "1300"

        # Red-letter record exists
        red = db_session.query(LedgerPayoffRecord).filter_by(
            status_cd="1200"
        ).first()
        assert red is not None
        assert red.cancel_amount == Decimal("-8000")

        # Arrears restored
        arrears = db_session.query(LedgerItemRecord).get(1)
        assert arrears.arrears_amount == Decimal("10000")
        assert arrears.cancel_amount == Decimal("0")

    def test_revoke_with_temp_fund_restored(self, db_session):
        self._setup_claim_with_payoff(db_session, with_temp=True)
        result = revoke_claim(db_session, RevokeClaimRequest(
            payment_id=1001,
            reason="test revoke",
        ))

        temp_fund = db_session.query(LedgerTempFundRecord).get(1)
        assert temp_fund.deposit_amount == Decimal("8000")

    def test_revoke_not_found_raises(self, db_session):
        with pytest.raises(ReverseError):
            revoke_claim(db_session, RevokeClaimRequest(
                payment_id=9999,
                reason="test",
            ))


class TestQueryReverseRecords:
    def _setup_reverse_records(self, db_session):
        db_session.add(LedgerPayoffRecord(
            payoff_id=1,
            cancel_amount=Decimal("5000"),
            ledger_claim_id=1,
            ledger_item_id=1,
            acct_cd="ACC001",
            cust_p_code="P001",
            status_cd="1200",  # 返销
            write_off_date=datetime(2026, 8, 5),
            batch_no="WO202607",
        ))
        db_session.add(LedgerPayoffRecord(
            payoff_id=2,
            cancel_amount=Decimal("-5000"),
            ledger_claim_id=1,
            ledger_item_id=1,
            acct_cd="ACC001",
            cust_p_code="P001",
            status_cd="1300",  # 作废
            write_off_date=datetime(2026, 8, 6),
            batch_no="WO202607",
        ))
        db_session.add(LedgerPayoffRecord(
            payoff_id=3,
            cancel_amount=Decimal("3000"),
            ledger_claim_id=2,
            ledger_item_id=2,
            acct_cd="ACC002",
            cust_p_code="P002",
            status_cd="1000",  # 正常 - should NOT appear
            write_off_date=datetime(2026, 8, 7),
        ))
        db_session.flush()

    def test_query_all_reverse_records(self, db_session):
        self._setup_reverse_records(db_session)
        page = query_reverse_records(db_session)
        assert page.total == 2  # only 1200 and 1300

    def test_query_by_status_1200(self, db_session):
        self._setup_reverse_records(db_session)
        page = query_reverse_records(db_session, status="1200")
        assert page.total == 1
        assert page.list[0].status == "1200"

    def test_query_by_p_code(self, db_session):
        self._setup_reverse_records(db_session)
        page = query_reverse_records(db_session, cust_p_code="P001")
        assert page.total == 2

    def test_query_normal_records_excluded(self, db_session):
        self._setup_reverse_records(db_session)
        page = query_reverse_records(db_session)
        statuses = [item.status for item in page.list]
        assert "1000" not in statuses
