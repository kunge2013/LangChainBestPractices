"""
Tests for temp claim service (sections 5.1, 5.2, 6.1).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from app.exceptions import TempClaimError
from app.models.finance import Finance
from app.models.ledger_claim import LedgerTempFundRecord, TmpClaimRecord
from app.schemas.ledger_claim import (
    ClaimItem,
    TempClaimRequest,
)
from app.services.temp_claim_service import (
    execute_temp_claim,
    query_temp_funds,
    query_unclaimed_finance,
)


class TestQueryUnclaimedFinance:
    def _setup_finance(self, db_session, claimed=False):
        finance = Finance(
            finance_id=1001,
            payment_cust_name="客户A",
            bank_nbr="BOC001",
            payment_date=datetime(2026, 7, 15),
            payment_money=Decimal("100000"),
            deposit_amount=Decimal("0"),
            status_cd="1000",
        )
        db_session.add(finance)
        if claimed:
            db_session.add(TmpClaimRecord(
                finance_id=1001,
                claim_amount=Decimal("50000"),
                status_cd="1000",
            ))
        db_session.flush()

    def test_query_unclaimed(self, db_session):
        self._setup_finance(db_session, claimed=False)
        page = query_unclaimed_finance(db_session, payment_month="202607")
        assert page.total == 1
        assert page.list[0].finance_id == "1001"

    def test_query_excludes_claimed(self, db_session):
        self._setup_finance(db_session, claimed=True)
        page = query_unclaimed_finance(db_session, payment_month="202607")
        assert page.total == 0

    def test_query_filters_by_status(self, db_session):
        finance = Finance(
            finance_id=1002,
            payment_cust_name="客户B",
            payment_date=datetime(2026, 7, 15),
            payment_money=Decimal("100000"),
            deposit_amount=Decimal("0"),
            status_cd="1100",  # invalid status
        )
        db_session.add(finance)
        db_session.flush()
        page = query_unclaimed_finance(db_session, payment_month="202607")
        assert page.total == 0


class TestExecuteTempClaim:
    def _setup_finance(self, db_session):
        finance = Finance(
            finance_id=1001,
            payment_cust_name="客户A",
            bank_nbr="BOC001",
            payment_date=datetime(2026, 7, 15),
            payment_money=Decimal("100000"),
            deposit_amount=Decimal("0"),
            status_cd="1000",
        )
        db_session.add(finance)
        db_session.flush()
        return finance

    def test_single_claim_success(self, db_session):
        self._setup_finance(db_session)

        request = TempClaimRequest(
            finance_id=1001,
            claim_list=[
                ClaimItem(claim_acct_id=100, claim_amount=Decimal("50000")),
            ],
            total_claim_amount=Decimal("50000"),
            remark="test",
        )
        acct_info = {
            100: {"party_nbr": "P001", "acct_cd": "ACC001",
                  "acct_name": "账户A", "cust_name": "客户A"},
        }
        result = execute_temp_claim(db_session, request, acct_info)
        assert result.finance_id == 1001
        assert result.claim_count == 1
        assert result.total_claim_amount == Decimal("50000")
        assert len(result.details) == 1
        assert result.details[0].claim_p_code == "P001"

        # Verify records were created
        claims = db_session.query(TmpClaimRecord).all()
        assert len(claims) == 1
        assert claims[0].claim_amount == Decimal("50000")
        assert claims[0].status_cd == "1000"

        temp_funds = db_session.query(LedgerTempFundRecord).all()
        assert len(temp_funds) == 1
        assert temp_funds[0].deposit_amount == Decimal("50000")

        # Finance status updated
        finance = db_session.query(Finance).get(1001)
        assert finance.status_cd == "1200"

    def test_multi_account_claim(self, db_session):
        self._setup_finance(db_session)

        request = TempClaimRequest(
            finance_id=1001,
            claim_list=[
                ClaimItem(claim_acct_id=100, claim_amount=Decimal("70000")),
                ClaimItem(claim_acct_id=200, claim_amount=Decimal("30000")),
            ],
            total_claim_amount=Decimal("100000"),
        )
        acct_info = {
            100: {"party_nbr": "P001", "acct_cd": "ACC001",
                  "acct_name": "账户A", "cust_name": "客户A"},
            200: {"party_nbr": "P002", "acct_cd": "ACC002",
                  "acct_name": "账户B", "cust_name": "客户B"},
        }
        result = execute_temp_claim(db_session, request, acct_info)
        assert result.claim_count == 2

        claims = db_session.query(TmpClaimRecord).all()
        assert len(claims) == 2

    def test_empty_claim_list_raises(self, db_session):
        self._setup_finance(db_session)
        request = TempClaimRequest(
            finance_id=1001,
            claim_list=[],
            total_claim_amount=Decimal("0"),
        )
        with pytest.raises(TempClaimError):
            execute_temp_claim(db_session, request, {})

    def test_negative_amount_raises(self, db_session):
        self._setup_finance(db_session)
        request = TempClaimRequest(
            finance_id=1001,
            claim_list=[
                ClaimItem(claim_acct_id=100, claim_amount=Decimal("-100")),
            ],
            total_claim_amount=Decimal("-100"),
        )
        with pytest.raises(TempClaimError):
            execute_temp_claim(db_session, request, {})

    def test_sum_mismatch_raises(self, db_session):
        self._setup_finance(db_session)
        request = TempClaimRequest(
            finance_id=1001,
            claim_list=[
                ClaimItem(claim_acct_id=100, claim_amount=Decimal("50000")),
            ],
            total_claim_amount=Decimal("60000"),  # mismatch
        )
        with pytest.raises(TempClaimError):
            execute_temp_claim(db_session, request, {})

    def test_finance_not_found_raises(self, db_session):
        request = TempClaimRequest(
            finance_id=9999,
            claim_list=[ClaimItem(claim_acct_id=100, claim_amount=Decimal("100"))],
            total_claim_amount=Decimal("100"),
        )
        with pytest.raises(TempClaimError):
            execute_temp_claim(db_session, request, {})

    def test_invalid_status_raises(self, db_session):
        db_session.add(Finance(
            finance_id=1001,
            payment_cust_name="客户A",
            payment_date=datetime(2026, 7, 15),
            payment_money=Decimal("100000"),
            status_cd="1100",  # invalid
        ))
        db_session.flush()

        request = TempClaimRequest(
            finance_id=1001,
            claim_list=[ClaimItem(claim_acct_id=100, claim_amount=Decimal("100"))],
            total_claim_amount=Decimal("100"),
        )
        with pytest.raises(TempClaimError):
            execute_temp_claim(db_session, request, {})

    def test_amount_exceeds_payment_raises(self, db_session):
        self._setup_finance(db_session)
        request = TempClaimRequest(
            finance_id=1001,
            claim_list=[ClaimItem(claim_acct_id=100, claim_amount=Decimal("200000"))],
            total_claim_amount=Decimal("200000"),
        )
        with pytest.raises(TempClaimError):
            execute_temp_claim(db_session, request, {})

    def test_already_claimed_raises(self, db_session):
        self._setup_finance(db_session)
        db_session.add(TmpClaimRecord(
            finance_id=1001,
            claim_amount=Decimal("50000"),
            status_cd="1000",
        ))
        db_session.flush()

        request = TempClaimRequest(
            finance_id=1001,
            claim_list=[ClaimItem(claim_acct_id=100, claim_amount=Decimal("50000"))],
            total_claim_amount=Decimal("50000"),
        )
        with pytest.raises(TempClaimError):
            execute_temp_claim(db_session, request, {})

    def test_account_info_invalid_raises(self, db_session):
        self._setup_finance(db_session)
        request = TempClaimRequest(
            finance_id=1001,
            claim_list=[ClaimItem(claim_acct_id=100, claim_amount=Decimal("50000"))],
            total_claim_amount=Decimal("50000"),
        )
        # Missing account info for acct_id 100
        with pytest.raises(TempClaimError):
            execute_temp_claim(db_session, request, {})


class TestTempFundQuery:
    def _setup_temp_funds(self, db_session):
        for i in range(5):
            db_session.add(LedgerTempFundRecord(
                finance_id=1000 + i,
                claim_id=2000 + i,
                cust_p_code=f"P{i:03d}",
                cust_name=f"客户{i}",
                acct_name=f"账户{i}",
                acct_cd=f"ACC{i:03d}",
                deposit_ym="202608",
                deposit_amount=Decimal("10000"),
            ))
        db_session.flush()

    def test_query_all(self, db_session):
        self._setup_temp_funds(db_session)
        page = query_temp_funds(db_session)
        assert page.total == 5

    def test_query_by_p_code(self, db_session):
        self._setup_temp_funds(db_session)
        page = query_temp_funds(db_session, cust_p_code="P000")
        assert page.total == 1

    def test_query_by_acct_name_like(self, db_session):
        self._setup_temp_funds(db_session)
        page = query_temp_funds(db_session, acct_name="账户0")
        assert page.total == 1

    def test_query_by_deposit_period(self, db_session):
        self._setup_temp_funds(db_session)
        page = query_temp_funds(db_session, deposit_period="202608")
        assert page.total == 5
