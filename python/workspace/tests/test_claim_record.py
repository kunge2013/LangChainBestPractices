"""
Tests for claim record service (sections 4.1, 4.2).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest

from app.exceptions import ClaimError
from app.models.finance import Finance, Payment
from app.models.ledger_claim import LedgerClaimRecord, LedgerTempFundRecord
from app.schemas.ledger_claim import (
    CreateClaimRequest,
    LedgerClaimQuery,
)
from app.services.ledger_claim_service import (
    create_formal_claim,
    query_ledger_claims,
)


class TestQueryLedgerClaims:
    def _setup_claims(self, db_session):
        for i in range(5):
            db_session.add(LedgerClaimRecord(
                payment_id=1000 + i,
                finance_id=str(2000 + i),
                cust_p_code=f"P{i:03d}",
                cust_name=f"客户{i}",
                acct_name=f"账户{i}",
                acct_cd=f"ACC{i:03d}",
                deposit_ym="202607",
                deposit_amount=Decimal("50000"),
                used_amount=Decimal("10000"),
                available_balance=Decimal("40000"),
                is_t0_init="0",
                status_cd="1000",
            ))
        db_session.flush()

    def test_query_all(self, db_session):
        self._setup_claims(db_session)
        page = query_ledger_claims(db_session)
        assert page.total == 5

    def test_query_by_p_code(self, db_session):
        self._setup_claims(db_session)
        page = query_ledger_claims(db_session, cust_p_code="P000")
        assert page.total == 1

    def test_query_by_status(self, db_session):
        self._setup_claims(db_session)
        page = query_ledger_claims(db_session, status_cd="1000")
        assert page.total == 5

    def test_query_by_balance_range(self, db_session):
        self._setup_claims(db_session)
        page = query_ledger_claims(
            db_session,
            available_balance_min=Decimal("35000"),
            available_balance_max=Decimal("45000"),
        )
        assert page.total == 5


class TestCreateFormalClaim:
    def test_scenario_a_with_temp_funds(self, db_session):
        """Scenario A: temp claim records exist, split by temp claim amounts."""
        db_session.add(Finance(
            finance_id=3001,
            payment_cust_name="客户A",
            payment_money=Decimal("100000"),
            status_cd="1200",
        ))
        db_session.add(LedgerTempFundRecord(
            temp_ledger_claim_id=1,
            finance_id=3001,
            claim_id=5001,
            cust_p_code="P001",
            cust_name="客户A",
            acct_name="账户A",
            acct_cd="ACC001",
            deposit_ym="202607",
            deposit_amount=Decimal("70000"),
        ))
        db_session.add(LedgerTempFundRecord(
            temp_ledger_claim_id=2,
            finance_id=3001,
            claim_id=5002,
            cust_p_code="P002",
            cust_name="客户B",
            acct_name="账户B",
            acct_cd="ACC002",
            deposit_ym="202607",
            deposit_amount=Decimal("30000"),
        ))
        db_session.flush()

        request = CreateClaimRequest(
            payment_id=1001,
            finance_id="3001",
            cust_p_code="P001",
            deposit_amount=Decimal("100000"),
            deposit_period="202607",
        )
        result = create_formal_claim(db_session, request)

        claims = db_session.query(LedgerClaimRecord).all()
        assert len(claims) == 2
        assert claims[0].deposit_amount == Decimal("70000")
        assert claims[1].deposit_amount == Decimal("30000")
        assert claims[0].claim_id == 5001
        assert claims[1].claim_id == 5002

        # Temp funds reduced
        tf1 = db_session.query(LedgerTempFundRecord).get(1)
        assert tf1.deposit_amount == Decimal("0")

    def test_scenario_b_no_temp_funds(self, db_session):
        """Scenario B: no temp claim, use request deposit_amount."""
        db_session.add(Finance(
            finance_id=3001,
            payment_cust_name="客户A",
            payment_money=Decimal("100000"),
            status_cd="1200",
        ))
        db_session.flush()

        request = CreateClaimRequest(
            payment_id=1001,
            finance_id="3001",
            cust_p_code="P001",
            deposit_amount=Decimal("50000"),
            deposit_period="202607",
        )
        result = create_formal_claim(db_session, request)

        claims = db_session.query(LedgerClaimRecord).all()
        assert len(claims) == 1
        assert claims[0].deposit_amount == Decimal("50000")
        assert claims[0].available_balance == Decimal("50000")
        assert claims[0].claim_id is None
        assert claims[0].status_cd == "1000"

    def test_duplicate_claim_raises(self, db_session):
        db_session.add(Finance(
            finance_id=3001,
            payment_cust_name="客户A",
            payment_money=Decimal("100000"),
            status_cd="1200",
        ))
        db_session.add(LedgerClaimRecord(
            payment_id=1001,
            finance_id="3001",
            cust_p_code="P001",
            deposit_amount=Decimal("50000"),
            available_balance=Decimal("50000"),
            status_cd="1000",
        ))
        db_session.flush()

        request = CreateClaimRequest(
            payment_id=1001,
            finance_id="3001",
            cust_p_code="P001",
            deposit_amount=Decimal("50000"),
            deposit_period="202607",
        )
        with pytest.raises(ClaimError):
            create_formal_claim(db_session, request)
